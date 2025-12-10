"""
QAMR: Quality-Aware Memory Retrieval

This module implements the QAMR scoring system that combines three factors:
- Relevance (R): Semantic similarity between query and event
- Value (V): Importance/quality score of the event content  
- Recency (T): Time decay factor based on event age

Final score = w_r * Relevance + w_v * Value + w_t * Recency
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import TypeVar, Generic, Callable, Any
from dataclasses import dataclass

from .env import CONFIG, TRACE_LOG


@dataclass
class QAMRWeights:
    """Weights for QAMR scoring (relevance, value, recency)"""
    relevance: float
    value: float
    recency: float
    
    def __post_init__(self):
        # Normalize weights to sum to 1.0
        total = self.relevance + self.value + self.recency
        if total > 0:
            self.relevance /= total
            self.value /= total
            self.recency /= total


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
    query_type: str = "open_domain",
    topk: int = None,
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

