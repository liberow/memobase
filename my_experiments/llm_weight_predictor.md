# LLM Weight Predictor

## Overview

The current LLM path no longer predicts continuous `(relevance, value, recency)` weights directly. Instead, it classifies the query into one of four fixed QAMR types and then maps that type to a fixed weight table:

- `temporal`
- `single_hop`
- `multi_hop`
- `open_domain`

The runtime priority is:

1. Use the provided `query_type` if the caller supplies one
2. Otherwise use the LLM to classify the query type (if enabled)
3. Otherwise fall back to heuristic query-type inference

## How It Works

### Before (Rule-based)

```
Query Type → Lookup Table → Fixed Weights
e.g., "temporal" → (0.3, 0.1, 0.6)
```

### After (LLM-based)

```
Query → LLM → Predicted Weights
e.g., "What did I do last week?" → (0.5, 0.2, 0.3)
```

## Features

### Dynamic Weight Prediction

The LLM analyzes the query and predicts optimal weights for three factors:
- **Relevance (R)**: Semantic similarity between query and memory
- **Value (V)**: Information importance/quality of the memory
- **Recency (T)**: Time freshness of the memory

### Robust Normalization

- Ensures weights always sum to 1.0
- Handles edge cases (negative values, zeros, large values)
- Provides sensible fallback when LLM prediction fails

### Backward Compatible

- Can be toggled on/off via configuration
- Falls back to rule-based weights when disabled
- No breaking changes to existing API

## Configuration

Add these to your `config.yaml` or environment variables:

```yaml
# Enable/disable LLM weight prediction
enable_llm_weight_prediction: false

# Model to use for weight prediction
llm_weight_prediction_model: "gpt-4o-mini"
```

Or via environment variables:

```bash
export MEMOBASE_ENABLE_LLM_WEIGHT_PREDICTION=true
export MEMOBASE_LLM_WEIGHT_PREDICTION_MODEL="gpt-4o-mini"
```

## Usage

### Example Query Predictions

| Query Type | Example Query | Predicted Weights (R, V, T) |
|------------|---------------|------------------------------|
| Temporal   | "What did I do last week?" | (0.50, 0.20, 0.30) |
| Factoid    | "Where do I live?" | (0.80, 0.15, 0.05) |
| Multi-hop  | "Why did I make that decision?" | (0.30, 0.60, 0.10) |
| Open-ended | "Tell me about my hobbies" | (0.60, 0.25, 0.15) |

### Enabling LLM Weight Prediction

1. Set `enable_llm_weight_prediction: true` in your config
2. Ensure `enable_qamr: true` (required)
3. Ensure valid LLM credentials are configured

### API Usage

The API remains unchanged. The important detail is that `query_type` is now a high-priority override:

```python
from memobase import MemoBaseClient

client = MemoBaseClient(...)

user = client.get_user(user_id)

# If query_type is omitted, the system may use LLM classification
context = user.context(
    max_token_size=3000,
    chats=[{"role": "user", "content": "What did I do last week?"}],
)

# If query_type is provided, the system uses the fixed weights for that type directly
context = user.context(
    max_token_size=3000,
    chats=[{"role": "user", "content": "What did I do last week?"}],
    query_type="temporal",
)
```

## Implementation Details

### Files Modified

- `src/server/api/memobase_server/env.py`: Added configuration options
- `src/server/api/memobase_server/qamr.py`: Added query-type classification and fixed-weight resolution
- `src/server/api/memobase_server/controllers/event_gist.py`: Integrated fixed-weight resolution
- `src/server/api/memobase_server/controllers/event.py`: Integrated fixed-weight resolution

### Key Functions

#### `get_qamr_weights_for_query(query, query_type, llm_client, project_id)`

Resolves the final fixed QAMR weights for a query.

**Parameters:**
- `query`: The user's query string
- `query_type`: Optional externally provided query type
- `llm_client`: Async LLM client function
- `project_id`: Project identifier for billing/logging

**Returns:**
- `QAMRWeights` mapped from one of the fixed query-type tables

#### `classify_query_type_with_llm(query, llm_client, project_id)`

Classifies the query into one of `temporal`, `single_hop`, `multi_hop`, or `open_domain`.

**Parameters:**
- `query`: The user's query string
- `llm_client`: Async LLM client function
- `project_id`: Project identifier for billing/logging

**Returns:**
- Classified query type label, or `None` on failure

## Testing

### Unit Tests

Run the local validation script:

```bash
python src/server/api/memobase_server/test_llm_weights.py
```

### Integration Testing

To test the full LLM integration:

1. Set up proper configuration with valid LLM credentials
2. Enable `enable_llm_weight_prediction`
3. Run the memobase server
4. Make queries and check logs for query-type classification / fixed-weight selection

## Performance Considerations

### Latency

- Additional LLM call per query (100-500ms typical)
- Use faster models (e.g., gpt-4o-mini) to minimize impact
- Consider caching for frequently repeated queries

### Cost

- Each prediction uses ~100-200 tokens
- Monitor token usage and costs via telemetry

### Recommendations

- For production: Consider implementing a caching layer
- For experiments: Log predictions to analyze patterns
- For optimization: Distill to a smaller model after collecting data

## Future Improvements

1. **Query Caching**: Cache weight predictions for repeated queries
2. **Model Distillation**: Train a smaller model based on LLM predictions
3. **Hybrid Approach**: Use LLM only for ambiguous queries
4. **Feedback Learning**: Collect feedback to improve predictions

## Troubleshooting

### LLM Predictions Not Working

1. Check `enable_llm_weight_prediction` is `true`
2. Check `enable_qamr` is `true`
3. Verify LLM credentials are configured
4. Check logs for LLM-related errors

### Weights Not Normalized

The normalization function handles all edge cases. Check logs for warnings.

### API Latency Increased

Expected behavior when LLM prediction is enabled. Consider:
- Using a faster model
- Implementing query caching
- Reverting to rule-based weights for production

## License

Same as the main MemoBase project.
