from pydantic import ValidationError
from ..models.database import UserEventGist, UserEvent
from ..models.response import UserEventGistsData, UserEventGistData
from ..models.utils import Promise, CODE
from ..connectors import Session
from ..utils import get_encoded_tokens, event_str_repr, event_embedding_str

from ..llms.embeddings import get_embedding
from ..qamr import rerank_by_qamr
from datetime import timedelta
from sqlalchemy import desc, select
from sqlalchemy.sql import func
from ..env import TRACE_LOG, CONFIG


async def get_user_event_gists(
    user_id: str,
    project_id: str,
    topk: int = 10,
    time_range_in_days: int = 21,
) -> Promise[UserEventGistsData]:
    with Session() as session:
        query = (
            session.query(UserEventGist)
            .filter_by(user_id=user_id, project_id=project_id)
            .filter(
                UserEventGist.created_at
                > (func.now() - timedelta(days=time_range_in_days))
            )
        )
        user_event_gists = (
            query.order_by(UserEventGist.created_at.desc()).limit(topk).all()
        )
        if user_event_gists is None:
            return Promise.resolve(UserEventGistsData(gists=[]))
        results = [
            {
                "id": ue.id,
                "gist_data": ue.gist_data,
                "created_at": ue.created_at,
                "updated_at": ue.updated_at,
            }
            for ue in user_event_gists
        ]
    gists = UserEventGistsData(gists=results)
    return Promise.resolve(gists)


async def truncate_event_gists(
    events: UserEventGistsData,
    max_token_size: int | None,
) -> Promise[UserEventGistsData]:
    if max_token_size is None:
        return Promise.resolve(events)
    c_tokens = 0
    truncated_results = []
    for r in events.gists:
        c_tokens += len(get_encoded_tokens(r.gist_data.content))
        if c_tokens > max_token_size:
            break
        truncated_results.append(r)
    events.gists = truncated_results
    return Promise.resolve(events)


async def search_user_event_gists(
    user_id: str,
    project_id: str,
    query: str,
    topk: int = 10,
    similarity_threshold: float = 0.2,
    time_range_in_days: int = 21,
    query_type: str = "open_domain",
) -> Promise[UserEventGistsData]:
    if not CONFIG.enable_event_embedding:
        TRACE_LOG.warning(
            project_id,
            user_id,
            "Event embedding is not enabled, skip search",
        )
        return Promise.reject(
            CODE.NOT_IMPLEMENTED,
            "Event embedding is not enabled",
        )
    query_embeddings = await get_embedding(
        project_id, [query], phase="query", model=CONFIG.embedding_model
    )
    if not query_embeddings.ok():
        TRACE_LOG.error(
            project_id,
            user_id,
            f"Failed to get embeddings: {query_embeddings.msg()}",
        )
        return query_embeddings
    query_embedding = query_embeddings.data()[0]

    # Calculate the time cutoff once
    time_cutoff = func.now() - timedelta(days=time_range_in_days)

    # Store the similarity expression to avoid recomputation
    similarity_expr = 1 - UserEventGist.embedding.cosine_distance(query_embedding)

    # Fetch topk candidates (same as Soft mode for fair comparison)
    fetch_limit = topk

    stmt = (
        select(
            UserEventGist,
            similarity_expr.label("similarity"),
        )
        .where(
            UserEventGist.user_id == user_id,
            UserEventGist.project_id == project_id,
            UserEventGist.created_at > time_cutoff,
            similarity_expr > similarity_threshold,
            UserEventGist.embedding.is_not(None),  # Skip null embeddings
        )
        .order_by(desc("similarity"))
        .limit(fetch_limit)
    )

    with Session() as session:
        # Use .all() instead of .scalars().all() to get both columns
        result = session.execute(stmt).all()
        
        # Build candidate list with similarity scores
        candidates = []
        event_ids = set()
        for row in result:
            user_event: UserEventGist = row[0]
            similarity: float = row[1]
            candidates.append({
                "event": user_event,
                "similarity": similarity,
            })
            event_ids.add(user_event.event_id)
        
        # Fetch value_scores from parent UserEvent records
        value_score_map = {}
        if CONFIG.enable_qamr and event_ids:
            event_rows = (
                session.query(UserEvent.id, UserEvent.event_data)
                .filter(UserEvent.id.in_(event_ids))
                .all()
            )
            for eid, event_data in event_rows:
                try:
                    value_score_map[eid] = float(event_data.get("value_score", 1.0))
                except (TypeError, ValueError, AttributeError):
                    value_score_map[eid] = 1.0
        
        # Apply QAMR reranking if enabled
        if CONFIG.enable_qamr and candidates:
            # Helper function to get value_score from parent event
            def get_value_score(item):
                event_id = item["event"].event_id
                return value_score_map.get(event_id, 1.0)
            
            reranked = rerank_by_qamr(
                items=candidates,
                get_similarity=lambda x: x["similarity"],
                get_created_at=lambda x: x["event"].created_at,
                get_value_score=get_value_score,
                query_type=query_type,
                topk=topk,
            )
            candidates = [item for item, score in reranked]
        else:
            candidates = candidates[:topk]
        
        # Convert to response format
        user_event_gists: list[UserEventGistData] = []
        for candidate in candidates:
            user_event = candidate["event"]
            similarity = candidate["similarity"]
            user_event_gists.append(
                UserEventGistData(
                    id=user_event.id,
                    gist_data=user_event.gist_data,
                    created_at=user_event.created_at,
                    updated_at=user_event.updated_at,
                    similarity=similarity,
                )
            )

        # Create UserEventsData with the events
        user_event_gists_data = UserEventGistsData(gists=user_event_gists)
        TRACE_LOG.info(
            project_id,
            user_id,
            f"Event Query: {query} (QAMR: {CONFIG.enable_qamr}, type: {query_type})",
        )

    return Promise.resolve(user_event_gists_data)
