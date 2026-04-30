"""
QAMR: Quality-Aware Memory Retrieval

This module implements the QAMR scoring system that combines three factors:
- Relevance (R): Semantic similarity between query and event
- Value (V): Importance/quality score of the event content
- Recency (T): Time decay factor based on event age

Final score = w_r * Relevance + w_v * Value + w_t * Recency
"""

from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone
from typing import TypeVar, Generic, Callable, Any
from dataclasses import dataclass

from .env import CONFIG, TRACE_LOG


# WEIGHT_PREDICTION_PROMPT_ZH = """你是一个用于 AI 智能体的“记忆检索控制器”。

# 给定一个用户查询，请判断以下三个因素在检索相关记忆时的重要性：

# 1. Relevance（相关性）：查询与记忆之间的语义相似度
# 2. Value（价值）：记忆中信息的重要性/信息密度
# 3. Recency（时效性）：记忆的时间新近程度

# 你的任务是为这三个因素分配权重，要求：

# - 每个权重必须在 0 到 1 之间
# - 三个权重之和必须严格等于 1

# 判断规则参考如下：

# - 时间相关问题（如“上周”、“最近”、“昨天”等）→ 提高 Recency 权重
# - 事实查询问题（如“在哪里”、“是什么”、“谁”）→ 提高 Relevance 权重
# - 多跳推理或原因分析（如“为什么”、“怎么做”、“原因是”）→ 提高 Value 权重
# - 开放性问题 → 三者相对均衡分配

# 重要约束：

# - 请对权重进行归一化，使其总和严格为 1
# - 除非非常必要，不要将全部权重分配给单一因素
# - 输出必须稳定、合理，不要随机波动

# 仅返回 JSON，不要输出任何额外内容，格式如下：

# {
#   "relevance": 浮点数,
#   "value": 浮点数,
#   "recency": 浮点数
# }

# 示例：

# 查询: "我上周做了什么？"
# 输出: {"relevance": 0.5, "value": 0.2, "recency": 0.3}

# 查询: "我住在哪里？"
# 输出: {"relevance": 0.8, "value": 0.15, "recency": 0.05}

# 查询: "我为什么做那个决定？"
# 输出: {"relevance": 0.3, "value": 0.6, "recency": 0.1}

# 查询: "介绍一下我的兴趣爱好"
# 输出: {"relevance": 0.6, "value": 0.25, "recency": 0.15}

# 查询: "{query}"
# """


QUERY_TYPE_CLASSIFICATION_SYSTEM_PROMPT = """You are a query classifier for conversational memory retrieval.

Your job is to classify the query into exactly one of these four types:
- temporal
- single_hop
- multi_hop
- open_domain

Definitions:
- temporal: asks about when, duration, chronology, recency, before/after, or time ranges.
- single_hop: asks for a specific fact such as who, what, where, which, name, title, place, date, object, or attribute.
- multi_hop: asks for explanation, reason, cause, implication, comparison, motivation, relationship, synthesis, or light inference across facts.
- open_domain: broad or mixed queries that do not fit the above clearly.

Important rules:
- You are classifying the query form, not answering the query.
- Do not say context is missing.
- Always choose exactly one type.
- Return exactly one line containing only one label from this set:
temporal
single_hop
multi_hop
open_domain

Examples:
- "When did Dave buy a vintage camera?" -> temporal
- "Who headlined the music festival?" -> single_hop
- "Why did Dave start working on cars?" -> multi_hop
- "Tell me about Calvin recently." -> open_domain
"""


QUERY_TYPE_CLASSIFICATION_PROMPT = """Query:
{query}

Return only one label:
temporal
single_hop
multi_hop
open_domain
"""


# Backward-compatible aliases for the old demo/test helpers.
WEIGHT_PREDICTION_SYSTEM_PROMPT = QUERY_TYPE_CLASSIFICATION_SYSTEM_PROMPT
WEIGHT_PREDICTION_PROMPT = QUERY_TYPE_CLASSIFICATION_PROMPT


@dataclass
class QAMRWeights:
    """Weights for QAMR scoring (relevance, value, recency)"""
    relevance: float
    value: float
    recency: float
    source: str = "config"
    
    def __post_init__(self):
        # Normalize weights to sum to 1.0
        total = self.relevance + self.value + self.recency
        if total > 0:
            self.relevance /= total
            self.value /= total
            self.recency /= total


def normalize_weights_dict(weights: dict) -> tuple[float, float, float]:
    """
    Normalize weights from LLM response to ensure sum = 1.

    Args:
        weights: Dict with keys "relevance", "value", "recency"

    Returns:
        Tuple of normalized weights (relevance, value, recency)
    """
    def _parse_weight_value(value: Any, default: float) -> float:
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return float(value)

        text = str(value).strip()

        fraction_match = re.search(r"([-+]?\d*\.?\d+)\s*/\s*([-+]?\d*\.?\d+)", text)
        if fraction_match:
            numerator = float(fraction_match.group(1))
            denominator = float(fraction_match.group(2))
            if denominator != 0:
                return numerator / denominator

        match = re.search(r"[-+]?\d*\.?\d+", text)
        if not match:
            return default
        return float(match.group(0))

    r = _parse_weight_value(weights.get("relevance", 0.33), 0.33)
    v = _parse_weight_value(weights.get("value", 0.33), 0.33)
    t = _parse_weight_value(weights.get("recency", 0.33), 0.33)

    # Ensure all weights are non-negative
    r = max(0, r)
    v = max(0, v)
    t = max(0, t)

    total = r + v + t
    if total == 0:
        # Fallback to balanced weights if all zeros
        return (0.5, 0.3, 0.2)

    return (r / total, v / total, t / total)


def infer_query_type_from_query(query: str) -> str:
    """
    Infer a coarse query type from the query text itself.
    This is used as a heuristic fallback when LLM-based weighting fails.
    """
    text = query.strip().lower()

    temporal_patterns = [
        r"\bwhen\b",
        r"\bwhat time\b",
        r"\bwhat year\b",
        r"\bwhat month\b",
        r"\bwhat day\b",
        r"\bdate\b",
        r"\brecently\b",
        r"\blast\b",
        r"\byesterday\b",
        r"\btoday\b",
        r"\btomorrow\b",
        r"\bago\b",
        r"\bbefore\b",
        r"\bafter\b",
        r"\bduring\b",
        r"\bthis year\b",
        r"\bthis month\b",
        r"\bthis week\b",
        r"\bnext\b",
        r"\bplanned?\b",
    ]
    if any(re.search(pattern, text) for pattern in temporal_patterns):
        return "temporal"

    multi_hop_patterns = [
        r"\bwhy\b",
        r"\bhow\b",
        r"\blikely\b",
        r"\bwould\b",
        r"\bcould\b",
        r"\bshould\b",
        r"\bimpact\b",
        r"\brepresent\b",
        r"\bmotivat",
        r"\breason\b",
        r"\bfeel\b",
        r"\bmean\b",
        r"\bdescribe\b",
        r"\bcompare\b",
        r"\brelationship\b",
        r"\bstatus\b",
        r"\bidentity\b",
    ]
    if any(re.search(pattern, text) for pattern in multi_hop_patterns):
        return "multi_hop"

    single_hop_patterns = [
        r"^\s*who\b",
        r"^\s*what\b",
        r"^\s*where\b",
        r"^\s*which\b",
        r"^\s*whom\b",
        r"\bname of\b",
    ]
    if any(re.search(pattern, text) for pattern in single_hop_patterns):
        return "single_hop"

    return "open_domain"


def get_heuristic_qamr_weights(query: str, reason: str) -> QAMRWeights:
    inferred_type = infer_query_type_from_query(query)
    weights = get_qamr_weights(inferred_type)
    weights.source = f"fallback_heuristic:{inferred_type}:{reason}"
    return weights


def normalize_query_type(query_type: str | None) -> str | None:
    if query_type is None:
        return None

    normalized = str(query_type).strip().lower().replace("-", "_")
    if normalized in {"temporal", "single_hop", "multi_hop", "open_domain"}:
        return normalized
    return None


def parse_query_type_classification_output(raw_output: Any) -> str | None:
    """
    Parse query-type classification output from the LLM.

    Supported formats:
    - temporal
    - {"query_type": "temporal"}
    - type=temporal
    - QueryType: single_hop
    """
    if raw_output is None:
        return None

    if isinstance(raw_output, dict):
        for key in ("query_type", "type", "label"):
            normalized = normalize_query_type(raw_output.get(key))
            if normalized is not None:
                return normalized

    text = str(raw_output).strip()
    if not text:
        return None

    direct_type = normalize_query_type(text.splitlines()[0].strip())
    if direct_type is not None:
        return direct_type

    for candidate in re.findall(r"\{[\s\S]*?\}", text):
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            for key in ("query_type", "type", "label"):
                normalized = normalize_query_type(parsed.get(key))
                if normalized is not None:
                    return normalized

    labeled_match = re.search(
        r"\b(?:query_type|type|label)\b\s*[:=]\s*(temporal|single_hop|multi_hop|open_domain)\b",
        text,
        flags=re.IGNORECASE,
    )
    if labeled_match:
        return normalize_query_type(labeled_match.group(1))

    any_type_match = re.search(
        r"\b(temporal|single_hop|multi_hop|open_domain)\b",
        text,
        flags=re.IGNORECASE,
    )
    if any_type_match:
        return normalize_query_type(any_type_match.group(1))

    return None


async def classify_query_type_with_llm(
    query: str,
    llm_client: Callable,
    project_id: str,
    user_id: str = "unknown",
) -> str | None:
    """
    Use the LLM to classify the query into one of the fixed QAMR query types.
    """
    user_prompt = QUERY_TYPE_CLASSIFICATION_PROMPT.format(query=query)

    try:
        response = await llm_client(
            project_id,
            prompt=user_prompt,
            system_prompt=QUERY_TYPE_CLASSIFICATION_SYSTEM_PROMPT,
            model=CONFIG.llm_weight_prediction_model,
            max_tokens=16,
            temperature=0.0,
            prompt_id="query_type_classification",
            no_cache=True,
        )

        if not response.ok():
            TRACE_LOG.warning(
                project_id,
                user_id,
                f"Query-type classification LLM call failed: {response.msg()}"
            )
            return None

        text = str(response.data()).strip()
        classified_type = parse_query_type_classification_output(text)
        if classified_type is None:
            TRACE_LOG.warning(
                project_id,
                user_id,
                f"Unable to parse query type from LLM output: {text[:200]}"
            )
            return None

        TRACE_LOG.info(
            project_id,
            user_id,
            f"Query: '{query[:50]}...' → Type={classified_type}"
        )
        return classified_type

    except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
        TRACE_LOG.warning(
            project_id,
            user_id,
            f"Failed to classify query type for query '{query[:50]}...': {e}"
        )
        return None
    except Exception as e:
        TRACE_LOG.error(
            project_id,
            user_id,
            f"LLM query-type classification failed for query '{query[:50]}...': {e}",
            exc_info=True,
        )
        return None


async def get_qamr_weights_for_query(
    query: str,
    query_type: str | None,
    llm_client: Callable | None,
    project_id: str,
    user_id: str = "unknown",
) -> QAMRWeights:
    """
    Resolve the fixed QAMR weights for a query.

    Priority:
    1. Use the provided query_type when available.
    2. Otherwise, if enabled, use the LLM to classify the query type.
    3. Otherwise, fall back to heuristic query-type inference.
    """
    normalized_query_type = normalize_query_type(query_type)
    if normalized_query_type is not None:
        weights = get_qamr_weights(normalized_query_type)
        weights.source = f"provided:{normalized_query_type}"
        return weights

    if CONFIG.enable_llm_weight_prediction and llm_client is not None:
        classified_type = await classify_query_type_with_llm(
            query, llm_client, project_id, user_id
        )
        if classified_type is not None:
            weights = get_qamr_weights(classified_type)
            weights.source = f"llm_type:{classified_type}"
            return weights

    return get_heuristic_qamr_weights(query, "no_query_type")


def get_qamr_weights(query_type: str = "open_domain") -> QAMRWeights:
    """
    Get QAMR weights based on query type.
    
    Args:
        query_type: One of "temporal", "single_hop", "multi_hop", "open_domain"
    
    Returns:
        QAMRWeights with (relevance, value, recency) weights
    """
    weights_map = {
        "temporal": CONFIG.qamr_weights_temporal,
        "single_hop": CONFIG.qamr_weights_single_hop,
        "multi_hop": CONFIG.qamr_weights_multi_hop,
        "open_domain": CONFIG.qamr_weights_open_domain,
    }
    
    weights = weights_map.get(query_type, CONFIG.qamr_weights_open_domain)
    return QAMRWeights(
        relevance=weights[0],
        value=weights[1],
        recency=weights[2],
        source=f"type:{query_type}",
    )


def compute_recency_score(
    created_at: datetime,
    decay_factor: float = None,
) -> float:
    """
    Compute recency score using exponential decay.
    
    Args:
        created_at: Event creation timestamp
        decay_factor: Decay factor per hour (default from config)
    
    Returns:
        Recency score in [0.0, 1.0], where 1.0 is most recent
    """
    if decay_factor is None:
        decay_factor = CONFIG.recency_decay_factor
    
    now = datetime.now(timezone.utc)
    
    # Ensure created_at is timezone-aware
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    else:
        created_at = created_at.astimezone(timezone.utc)
    
    # Calculate hours since event
    hours_ago = (now - created_at).total_seconds() / 3600.0
    
    # Exponential decay: score = decay_factor ^ hours_ago
    # decay_factor = 0.999 means ~0.1% decay per hour
    score = math.pow(decay_factor, max(0, hours_ago))
    
    return min(1.0, max(0.0, score))


def compute_qamr_score(
    relevance: float,
    value: float,
    recency: float,
    weights: QAMRWeights,
) -> float:
    """
    Compute final QAMR score.
    
    Args:
        relevance: Semantic similarity score [0, 1]
        value: Event value/importance score [0, 1]
        recency: Time decay score [0, 1]
        weights: QAMR weights for each factor
    
    Returns:
        Combined QAMR score [0, 1]
    """
    score = (
        weights.relevance * relevance +
        weights.value * value +
        weights.recency * recency
    )
    return min(1.0, max(0.0, score))


T = TypeVar('T')


def rerank_by_qamr(
    items: list[T],
    get_similarity: Callable[[T], float],
    get_created_at: Callable[[T], datetime],
    get_value_score: Callable[[T], float] = None,
    query_type: str | None = None,
    topk: int = None,
    weights: QAMRWeights = None,
) -> list[tuple[T, float]]:
    """
    Rerank items using QAMR scoring.
    
    Args:
        items: List of items to rerank
        get_similarity: Function to get similarity score from item
        get_created_at: Function to get created_at timestamp from item
        get_value_score: Function to get value score from item (default: 1.0)
        query_type: Query type for weight selection
        topk: Number of top items to return (None = all)
    
    Returns:
        List of (item, qamr_score) tuples sorted by QAMR score descending
    """
    if not CONFIG.enable_qamr:
        # If QAMR is disabled, return items sorted by similarity only
        scored = [(item, get_similarity(item)) for item in items]
        scored.sort(key=lambda x: x[1], reverse=True)
        if topk:
            scored = scored[:topk]
        return scored

    # Use provided weights or get weights based on query_type
    if weights is None:
        weights = get_qamr_weights(query_type)
    
    # Default value score function returns 1.0 (no filtering)
    if get_value_score is None:
        get_value_score = lambda x: 1.0
    
    scored_items = []
    for item in items:
        similarity = get_similarity(item)
        value = get_value_score(item)
        recency = compute_recency_score(get_created_at(item))
        
        qamr_score = compute_qamr_score(similarity, value, recency, weights)
        scored_items.append((item, qamr_score))
    
    # Sort by QAMR score descending
    scored_items.sort(key=lambda x: x[1], reverse=True)
    
    if topk:
        scored_items = scored_items[:topk]
    
    return scored_items

