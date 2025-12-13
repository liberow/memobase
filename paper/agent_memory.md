# Value-Based Memory Scoring

## 1. 环境配置

### 1.1 项目环境

```
# clone 
git clone git@github.com:liberow/memobase.git
# create env 
conda create -n memobase_value python=3.11 -y
# activate env 
conda activate memobase_value
# into project
cd memobase/
# install package 
pip install -r requirements.txt
```

### 1.2. 数据存储

1. Postgres
```
apt update
apt install -y postgresql postgresql-contrib
# 常见 Debian/Ubuntu 容器：
service postgresql start  ||  pg_ctlcluster 16 main start
# 进入 postgres 用户执行 SQL
su - postgres -c "psql -c \"CREATE USER memobase_user WITH PASSWORD 'memobase_pass';\""
su - postgres -c "psql -c \"CREATE DATABASE memobase_db OWNER memobase_user;\""
export DATABASE_URL="postgresql+psycopg2://memobase_user:memobase_pass@localhost:5432/memobase_db"
```

2. Redis

```
apt install -y redis-server
# 简单方式：前台启动一个 redis（如果你是交互式终端，可以用 & 放后台）
redis-server --bind 0.0.0.0 --port 6379 &
# 如果没有密码：
export REDIS_URL="redis://localhost:6379/0"
# 如果你给 redis 配了密码，比如 "redis_pass"，就：
# export REDIS_URL="redis://:redis_pass@localhost:6379/0"
```

## 2. 运行

1. Memobase Server 启动

```
cd ./src/server/api
fastapi dev api.py --port 8019
```

2. 

## 3. LOCOMO + Value-Based Scoring 完整实验命令

---

### 阶段 1：LOCOMO Baseline（未使用价值评分机制）

1. command

```bash
# 进入实验目录
cd ./docs/experiments/locomo-benchmark

# 1. 在开启 Value-Based Scoring 的 Memobase 上加载对话数据
python run_experiments.py \
  --technique_type memobase \
  --method add

# 2. 运行检索测试，生成预测答案（Value-Based Scoring）
python run_experiments.py \
  --technique_type memobase \
  --method search

# 3. 评估结果
python evals.py \
  --input_file results/memobase_locomo_baseline_00_result.json \
  --output_file results/memobase_locomo_baseline_00_eval.json

# 4. 生成分数报告
python generate_scores.py \
  --input_path results/memobase_locomo_baseline_00_eval.json
```

2. config

```yaml
# Language
language: zh  

# LLM
llm_api_key: "182b8a28-3392-4490-90a0-fe4cb6ef5bb2"                
llm_base_url: "https://ark.cn-beijing.volces.com/api/v3"
best_llm_model: "doubao-1-5-pro-32k-250115"
thinking_llm_model: "doubao-1-5-pro-32k-250115"

# Embedding
embedding_provider: openai
embedding_api_key: "182b8a28-3392-4490-90a0-fe4cb6ef5bb2"          
embedding_model: "doubao-embedding-large-text-240915"
embedding_base_url: "https://ark.cn-beijing.volces.com/api/v3"
embedding_dim: 4096
```

3. result

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

---

### 阶段 2：Value 机制


---

### 阶段 3：LOCOMO After Value Scoring（使用价值评分机制）

#### 3.1. 设置配置

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

# Value Scoring
# value_scoring_mode: off = 禁用, soft = 检索时重排序, hard = 写入时删除
value_scoring_mode: "soft"
soft_rerank_alpha: 0.7      # 综合得分权重：α * similarity + (1-α) * value_score
value_score_threshold_event: 0.15    # hard 模式的阈值

```
#### 3.2. 重启 server
```bash

# 清空数据库
PGPASSWORD=memobase_pass psql -h localhost -U memobase_user -d memobase_db -c "TRUNCATE user_events, users, user_profiles CASCADE;"

# 清空 Redis
redis-cli FLUSHDB

cd ./src/server/api

fastapi dev api.py --port 8019
```

#### 3.3. commands
```bash
# 进入实验目录
cd ./docs/experiments/locomo-benchmark

# 1. 在开启 Value-Based Scoring 的 Memobase 上加载对话数据
python run_experiments.py \
  --technique_type memobase \
  --method add

# 2. 运行检索测试，生成预测答案（Value-Based Scoring）
python run_experiments.py \
  --technique_type memobase \
  --method search

# 3. 评估结果
python evals.py \
  --input_file results.json \
  --output_file results/memobase_locomo_value_01_eval.json

# 4. 生成分数报告
python generate_scores.py \
  --input_path results/memobase_locomo_value_01_eval.json
```



### 结果对比

#### 00 vs 01

1. config

```yaml
# value_scoring_mode: off = 禁用, soft = 检索时重排序, hard = 写入时删除
value_scoring_mode: "soft"
soft_rerank_alpha: 0.7      # 综合得分权重：α * similarity + (1-α) * value_score
value_score_threshold_event: 0.15    # hard 模式的阈值
```

2. scores

```bash
Mean Scores Per Category:
          bleu_score  f1_score  llm_score  count         type
category                                                     
1             0.2254    0.3485     0.7872    282   single_hop
2             0.3790    0.4857     0.6449    321     temporal
3             0.1444    0.1858     0.4271     96    multi_hop
4             0.3532    0.4205     0.6825    841  open_domain

Overall Mean Scores:
bleu_score    0.3222
f1_score      0.4063
llm_score     0.6779
dtype: float64
```

3. 和 00 的对比

| 指标 | Category | 00 (Baseline) | 01 (Value) | 变化 | 变化率 |
|------|----------|---------------|-------------|------|--------|
| **bleu_score** | 1 (single_hop) | 0.2354 | 0.2254 | -0.0100 | -4.2% |
| | 2 (temporal) | 0.3237 | 0.3790 | **+0.0553** | **+17.1%** |
| | 3 (multi_hop) | 0.1235 | 0.1444 | **+0.0209** | **+16.9%** |
| | 4 (open_domain) | 0.3619 | 0.3532 | -0.0087 | -2.4% |
| **f1_score** | 1 (single_hop) | 0.3557 | 0.3485 | -0.0072 | -2.0% |
| | 2 (temporal) | 0.4241 | 0.4857 | **+0.0616** | **+14.5%** |
| | 3 (multi_hop) | 0.1557 | 0.1858 | **+0.0301** | **+19.3%** |
| | 4 (open_domain) | 0.4279 | 0.4205 | -0.0074 | -1.7% |
| **llm_score** | 1 (single_hop) | 0.7908 | 0.7872 | -0.0036 | -0.5% |
| | 2 (temporal) | 0.6511 | 0.6449 | -0.0062 | -1.0% |
| | 3 (multi_hop) | 0.3542 | 0.4271 | **+0.0729** | **+20.6%** |
| | 4 (open_domain) | 0.7027 | 0.6825 | -0.0202 | -2.9% |

**Overall 对比：**

| 指标 | 00 (Baseline) | 01 (Value) | 变化 | 变化率 |
|------|---------------|-------------|------|--------|
| bleu_score | 0.3159 | 0.3222 | +0.0063 | +2.0% |
| f1_score | 0.3969 | 0.4063 | +0.0094 | +2.4% |
| llm_score | 0.6864 | 0.6779 | -0.0085 | -1.2% |

**分析总结：**

1. **temporal（时序问题）提升显著**：bleu +17.1%, f1 +14.5%，说明价值评分机制帮助过滤了低价值信息，提升了时序相关问答的准确性
2. **multi_hop（多跳推理）全面提升**：bleu +16.9%, f1 +19.3%, llm_score +20.6%，价值评分机制减少了噪声信息干扰
3. **single_hop 和 open_domain 略有下降**：可能是因为 soft_rerank_alpha=0.7 对简单检索任务有轻微负面影响
4. **整体 f1_score 提升 2.4%**：表明价值评分机制对检索精度有正向作用
5. **llm_score 略降 1.2%**：可能需要调整 alpha 参数以平衡

---

#### 02 vs 00

1. config 

```yaml
# Language
language: en  # LoCoMo 是英文数据集，使用英文 prompt

# LLM
llm_api_key: "182b8a28-3392-4490-90a0-fe4cb6ef5bb2"                
llm_base_url: "https://ark.cn-beijing.volces.com/api/v3"
best_llm_model: "doubao-1-5-lite-32k-250115"
thinking_llm_model: "doubao-1-5-lite-32k-250115"
value_scorer_model: "doubao-1-5-lite-32k-250115"    

# Embedding
embedding_provider: openai
embedding_api_key: "182b8a28-3392-4490-90a0-fe4cb6ef5bb2"          
embedding_model: "doubao-embedding-large-text-240915"
embedding_base_url: "https://ark.cn-beijing.volces.com/api/v3"
embedding_dim: 4096

# Value Scoring
# value_scoring_mode: off = 禁用, soft = 检索时重排序, hard = 写入时删除
value_scoring_mode: "off"
soft_rerank_alpha: 0.7      # 综合得分权重：α * similarity + (1-α) * value_score
value_score_threshold_event: 0.15    # hard 模式的阈值

```

2. scores

```bash
Mean Scores Per Category:
          bleu_score  f1_score  llm_score  count         type
category                                                     
1             0.2144    0.3432     0.7305    282   single_hop
2             0.2710    0.3423     0.6604    321     temporal
3             0.1229    0.1588     0.3542     96    multi_hop
4             0.3436    0.4064     0.6635    841  open_domain

Overall Mean Scores:
bleu_score    0.2911
f1_score      0.3660
llm_score     0.6558
dtype: float64
```

#### 03 vs 02 vs 01 vs 00

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

# Value Scoring
# value_scoring_mode: off = 禁用, soft = 检索时重排序, hard = 写入时删除
value_scoring_mode: "soft"
soft_rerank_alpha: 0.7      # 综合得分权重：α * similarity + (1-α) * value_score
value_score_threshold_event: 0.15    # hard 模式的阈值
```

2. scores

```bash
Mean Scores Per Category:
          bleu_score  f1_score  llm_score  count         type
category                                                     
1             0.2427    0.3692     0.7766    282   single_hop
2             0.3827    0.4957     0.6760    321     temporal
3             0.1408    0.1785     0.4167     96    multi_hop
4             0.3684    0.4376     0.7218    841  open_domain

Overall Mean Scores:
bleu_score    0.3342
f1_score      0.4210
llm_score     0.7032
dtype: float64
```

#### 04 

1. config

```yaml
# Language
language: en  # LoCoMo 是英文数据集，使用英文 prompt

# LLM
llm_api_key: "182b8a28-3392-4490-90a0-fe4cb6ef5bb2"                
llm_base_url: "https://ark.cn-beijing.volces.com/api/v3"
best_llm_model: "doubao-1-5-lite-32k-250115"
thinking_llm_model: "doubao-1-5-lite-32k-250115"
value_scorer_model: "doubao-1-5-lite-32k-250115"    

# Embedding
embedding_provider: openai
embedding_api_key: "182b8a28-3392-4490-90a0-fe4cb6ef5bb2"          
embedding_model: "doubao-embedding-large-text-240915"
embedding_base_url: "https://ark.cn-beijing.volces.com/api/v3"
embedding_dim: 4096

# Value Scoring
# value_scoring_mode: off = 禁用, soft = 检索时重排序, hard = 写入时删除
value_scoring_mode: "soft"
soft_rerank_alpha: 0.7      # 综合得分权重：α * similarity + (1-α) * value_score
value_score_threshold_event: 0.15    # hard 模式的阈值

```

2. score

```bash
Mean Scores Per Category:
          bleu_score  f1_score  llm_score  count         type
category                                                     
1             0.2093    0.3439     0.7872    282   single_hop
2             0.2571    0.3278     0.6729    321     temporal
3             0.1011    0.1279     0.3333     96    multi_hop
4             0.3438    0.4075     0.6671    841  open_domain

Overall Mean Scores:
bleu_score    0.2860
f1_score      0.3618
llm_score     0.6695
dtype: float64
```


#### 05 

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

# Value Scoring
# value_scoring_mode: off = 禁用, soft = 检索时重排序, hard = 写入时删除
value_scoring_mode: "soft"
soft_rerank_alpha: 0.7      # 综合得分权重：α * similarity + (1-α) * value_score
value_score_threshold_event: 0.15    # hard 模式的阈值
```


2. scores

```bash
Mean Scores Per Category:
          bleu_score  f1_score  llm_score  count         type
category                                                     
1             0.2332    0.3557     0.7801    282   single_hop
2             0.3469    0.4616     0.6636    321     temporal
3             0.1396    0.1782     0.4479     96    multi_hop
4             0.3697    0.4396     0.7039    841  open_domain

Overall Mean Scores:
bleu_score    0.3256
f1_score      0.4125
llm_score     0.6935
dtype: float64
```