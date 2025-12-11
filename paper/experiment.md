
## experiment

### baseline

```
Mean Scores Per Category:
          bleu_score  f1_score  llm_score  count         type
category                                                     
1             0.2354    0.3557     0.7908    282   single_hop
2             0.3237    0.4241     0.6511    321     temporal
3             0.1235    0.1557     0.3542     96    multi_hop
4             0.3619    0.4279     0.7027    841  open_domain

Overall Mean Scores:
bleu_score    0.3159
f1_score      0.3969
llm_score     0.6864
dtype: float64
```

### 01

1. config 

```yaml
# Language
language: en  # LoCoMo 是英文数据集，使用英文 prompt

# LLM
llm_api_key: "182b8a28-3392-4490-90a0-fe4cb6ef5bb2"                
llm_base_url: "https://ark.cn-beijing.volces.com/api/v3"
best_llm_model: "doubao-1-5-pro-32k-250115"
thinking_llm_model: "doubao-1-5-pro-32k-250115"
value_scorer_model: "doubao-1-5-pro-32k-250115"    

# Embedding
embedding_provider: openai
embedding_api_key: "182b8a28-3392-4490-90a0-fe4cb6ef5bb2"          
embedding_model: "doubao-embedding-large-text-240915"
embedding_base_url: "https://ark.cn-beijing.volces.com/api/v3"
embedding_dim: 4096

# QAMR (Query-Aware Memory Retrieval)
enable_qamr: true
recency_decay_factor: 0.999  # 每小时衰减约 0.1%

# 不同问题类型的权重配置 (relevance, value, recency)
qamr_weights_temporal: [0.5, 0.0, 0.5]      # 时间问题重视 recency
qamr_weights_single_hop: [1.0, 0.0, 0.0]    # 事实查询重视 relevance  
qamr_weights_multi_hop: [0.7, 0.3, 0.0]     # 推理问题重视 value
qamr_weights_open_domain: [0.6, 0.2, 0.2]   # 开放问题均衡
```

2. scores

```bash
Mean Scores Per Category:
          bleu_score  f1_score  llm_score  count         type
category                                                     
1             0.2395    0.3629     0.7730    282   single_hop
2             0.3738    0.4815     0.6729    321     temporal
3             0.1005    0.1369     0.3646     96    multi_hop
4             0.3712    0.4412     0.7158    841  open_domain

Overall Mean Scores:
bleu_score    0.3308
f1_score      0.4163
llm_score     0.6955
dtype: float64
```

### 02

1. config

```yaml
# Language
language: en  # LoCoMo 是英文数据集，使用英文 prompt

# LLM
llm_api_key: "182b8a28-3392-4490-90a0-fe4cb6ef5bb2"                
llm_base_url: "https://ark.cn-beijing.volces.com/api/v3"
best_llm_model: "doubao-1-5-pro-32k-250115"
thinking_llm_model: "doubao-1-5-pro-32k-250115"
value_scorer_model: "doubao-1-5-pro-32k-250115"    

# Embedding
embedding_provider: openai
embedding_api_key: "182b8a28-3392-4490-90a0-fe4cb6ef5bb2"          
embedding_model: "doubao-embedding-large-text-240915"
embedding_base_url: "https://ark.cn-beijing.volces.com/api/v3"
embedding_dim: 4096

# QAMR (Query-Aware Memory Retrieval)
enable_qamr: true
recency_decay_factor: 0.999  # 每小时衰减约 0.1%

# 不同问题类型的权重配置 (relevance, value, recency)
qamr_weights_temporal: [0.7, 0.1, 0.2]      # 时间问题重视 recency
qamr_weights_single_hop: [0.9, 0.1, 0.0]    # 事实查询重视 relevance  
qamr_weights_multi_hop: [0.7, 0.3, 0.0]     # 推理问题重视 value
qamr_weights_open_domain: [0.7, 0.2, 0.1]   # 开放问题均衡
```

2. scores

```bash
Mean Scores Per Category:
          bleu_score  f1_score  llm_score  count         type
category                                                     
1             0.2473    0.3627     0.7482    282   single_hop
2             0.3693    0.4764     0.6760    321     temporal
3             0.1109    0.1490     0.3958     96    multi_hop
4             0.3723    0.4436     0.7265    841  open_domain

Overall Mean Scores:
bleu_score    0.3325
f1_score      0.4173
llm_score     0.6994
dtype: float64
```