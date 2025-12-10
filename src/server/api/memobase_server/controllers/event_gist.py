from pydantic import ValidationError
from ..models.database import UserEventGist, UserEvent
from ..models.response import UserEventGistsData, UserEventGistData
from ..models.utils import Promise, CODE
from ..connectors import Session
from ..utils import get_encoded_tokens, event_str_repr, event_embedding_str

from ..llms.embeddings import get_embedding
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


async def rerank_event_gists_by_value_score(
    user_id: str,
    project_id: str,
    events: UserEventGistsData,
) -> Promise[UserEventGistsData]:
    """
    在检索时基于价值分数进行重排序。
    
    - 当 value_scoring_mode == "off" 或 "hard" 时, 这是一个空操作。
    - 当 value_scoring_mode == "soft" 时, 我们根据 value_score 和 similarity 
      计算综合得分，并重新排序事件。低价值事件会排在后面，但不会被直接删除。
      后续的 truncate_event_gists 会根据 token 预算自然截断。
    - "hard" 模式在写入时在 handle_session_event 中处理。
    
    综合得分公式: combined_score = α * similarity + (1-α) * value_score
    其中 α (soft_rerank_alpha) 控制语义相似度的权重，默认为 0.7
    """
    if CONFIG.value_scoring_mode != "soft":
        return Promise.resolve(events)

    if not events.gists:
        return Promise.resolve(events)

    gist_ids = [g.id for g in events.gists]

    with Session() as session:
        rows = (
            session.query(UserEventGist.id, UserEvent.event_data)
            .join(
                UserEvent,
                (UserEventGist.event_id == UserEvent.id)
                & (UserEventGist.project_id == UserEvent.project_id),
            )
            .filter(
                UserEventGist.user_id == user_id,
                UserEventGist.project_id == project_id,
                UserEventGist.id.in_(gist_ids),
            )
            .all()
        )

        value_by_id = {}
        for gist_id, event_data in rows:
            try:
                value = float(event_data.get("value_score", 1.0))
            except (TypeError, ValueError):
                value = 1.0
            value_by_id[gist_id] = value

    # 软筛选：根据综合得分重排序，而不是过滤
    # α 控制语义相似度的权重，1-α 是价值分数的权重
    alpha = CONFIG.soft_rerank_alpha
    
    # 计算每个 gist 的综合得分
    for idx, g in enumerate(events.gists):
        value_score = value_by_id.get(g.id, 1.0)
        # 如果有相似度分数（来自向量搜索），使用综合得分
        if hasattr(g, 'similarity') and g.similarity is not None:
            g.combined_score = alpha * g.similarity + (1 - alpha) * value_score
        else:
            # 没有相似度（来自时间排序）时：
            # 保持原有时间顺序的同时，让低价值事件稍微靠后
            # 使用 position_score 保持相对顺序，value_score 作为微调
            position_score = 1.0 - (idx / max(len(events.gists), 1)) * 0.1  # 越靠前分越高
            g.combined_score = 0.8 * position_score + 0.2 * value_score
    
    # 按综合得分降序排序（高分在前）
    events.gists = sorted(events.gists, key=lambda g: g.combined_score, reverse=True)
    
    TRACE_LOG.info(
        project_id,
        user_id,
        f"Value-based reranking: reranked {len(events.gists)} gists by combined score (alpha={alpha})",
    )
    
    return Promise.resolve(events)


async def search_user_event_gists(
    user_id: str,
    project_id: str,
    query: str,
    topk: int = 10,
    similarity_threshold: float = 0.2,
    time_range_in_days: int = 21,
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
        .limit(topk)
    )

    with Session() as session:
        # Use .all() instead of .scalars().all() to get both columns
        result = session.execute(stmt).all()
        user_event_gists: list[UserEventGistData] = []
        for row in result:
            user_event: UserEventGist = row[0]  # UserEventGist object
            similarity: float = row[1]  # similarity value
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
            f"Event Query: {query}",
        )

    return Promise.resolve(user_event_gists_data)
