# Forgetting Memory

## 1. 环境配置

### 1.1 项目环境

```
# clone 
git clone git@github.com:liberow/memobase.git

# create env 
conda create -n selective_forgetting python=3.11 -y

# activate env 
conda activate selective_forgetting

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

## 3. LOCOMO + Selective Forgetting 完整实验命令

---

### 阶段 1：LOCOMO Baseline（未使用遗忘机制）

1. command

```bash
# 进入实验目录
cd ./docs/experiments/locomo-benchmark

# 1. 在开启 Selective Forgetting 的 Memobase 上加载对话数据
python run_experiments.py \
  --technique_type memobase \
  --method add

# 2. 运行检索测试，生成预测答案（Selective Forgetting）
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

2. result

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

### 阶段 2：Forget 机制


---

### 阶段 3：LOCOMO After Forgetting（使用遗忘机制）

#### 3.1. 设置配置

```yaml
enable_value_based_forgetting: true
value_based_forgetting_mode: "soft"  # soft = 检索时重排序，hard = 写入时删除
soft_forgetting_alpha: 0.7           # 综合得分权重：α * similarity + (1-α) * value_score
value_score_threshold_event: 0.15    # hard 模式的阈值（soft 模式不使用）
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

# 1. 在开启 Selective Forgetting 的 Memobase 上加载对话数据
python run_experiments.py \
  --technique_type memobase \
  --method add

# 2. 运行检索测试，生成预测答案（Selective Forgetting）
python run_experiments.py \
  --technique_type memobase \
  --method search

# 3. 评估结果
python evals.py \
  --input_file results/memobase_locomo_forget_05_result.json \
  --output_file results/memobase_locomo_forget_05_eval.json

# 4. 生成分数报告
python generate_scores.py \
  --input_path results/memobase_locomo_forget_05_eval.json
```



### 结果对比

#### 00 vs 01

1. forget config

```yaml
```yaml
enable_value_based_forgetting: true
value_based_forgetting_mode: "soft"  # soft = 检索时重排序，hard = 写入时删除
soft_forgetting_alpha: 0.7           # 综合得分权重：α * similarity + (1-α) * value_score
value_score_threshold_event: 0.15    # hard 模式的阈值（soft 模式不使用）
```
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

| 指标 | Category | 00 (Baseline) | 01 (Forget) | 变化 | 变化率 |
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

| 指标 | 00 (Baseline) | 01 (Forget) | 变化 | 变化率 |
|------|---------------|-------------|------|--------|
| bleu_score | 0.3159 | 0.3222 | +0.0063 | +2.0% |
| f1_score | 0.3969 | 0.4063 | +0.0094 | +2.4% |
| llm_score | 0.6864 | 0.6779 | -0.0085 | -1.2% |

**分析总结：**

1. **temporal（时序问题）提升显著**：bleu +17.1%, f1 +14.5%，说明遗忘机制帮助过滤了过时信息，提升了时序相关问答的准确性
2. **multi_hop（多跳推理）全面提升**：bleu +16.9%, f1 +19.3%, llm_score +20.6%，遗忘机制减少了噪声信息干扰
3. **single_hop 和 open_domain 略有下降**：可能是因为 soft_forgetting_alpha=0.7 对简单检索任务有轻微负面影响
4. **整体 f1_score 提升 2.4%**：表明遗忘机制对检索精度有正向作用
5. **llm_score 略降 1.2%**：可能需要调整 alpha 参数以平衡

---

#### 02 vs 00 vs 01

1. config

```yaml
# 三因素检索: Relevance + Value + Recency 
enable_qamr: true
recency_decay_factor: 0.995  # 每小时衰减约0.5%

# 不同问题类型的权重配置 (relevance, value, recency)
qamr_weights_temporal: [0.3, 0.1, 0.6]      # 时间问题重视 recency
qamr_weights_single_hop: [0.7, 0.2, 0.1]    # 事实查询重视 relevance  
qamr_weights_multi_hop: [0.4, 0.5, 0.1]     # 推理问题重视 value
qamr_weights_open_domain: [0.5, 0.3, 0.2]   # 开放问题均衡
```

2. scores

```bash
(selective_forgetting) root@c81ab3b21da2:/workspace/liber/memory/memobase/docs/experiments/locomo-benchmark# python generate_scores.py \
  --input_path results/memobase_locomo_forget_02_eval.json
Mean Scores Per Category:
          bleu_score  f1_score  llm_score  count         type
category                                                     
1             0.2141    0.3400     0.7411    282   single_hop
2             0.2520    0.3152     0.6854    321     temporal
3             0.1041    0.1419     0.3438     96    multi_hop
4             0.3442    0.4117     0.6825    841  open_domain

Overall Mean Scores:
bleu_score    0.2862
f1_score      0.3616
llm_score     0.6727
dtype: float64
```

3. 对比

**按类别对比表：**

| 指标 | Category | 00 (Baseline) | 01 (Soft Forget) | 02 (QAMR) | 01 vs 00 | 02 vs 00 | 02 vs 01 |
|------|----------|---------------|------------------|-----------|----------|----------|----------|
| **bleu_score** | 1 (single_hop) | 0.2354 | 0.2254 | 0.2141 | -4.2% | -9.0% | -5.0% |
| | 2 (temporal) | 0.3237 | 0.3790 | 0.2520 | **+17.1%** | -22.1% | -33.5% |
| | 3 (multi_hop) | 0.1235 | 0.1444 | 0.1041 | **+16.9%** | -15.7% | -27.9% |
| | 4 (open_domain) | 0.3619 | 0.3532 | 0.3442 | -2.4% | -4.9% | -2.5% |
| **f1_score** | 1 (single_hop) | 0.3557 | 0.3485 | 0.3400 | -2.0% | -4.4% | -2.4% |
| | 2 (temporal) | 0.4241 | 0.4857 | 0.3152 | **+14.5%** | -25.7% | -35.1% |
| | 3 (multi_hop) | 0.1557 | 0.1858 | 0.1419 | **+19.3%** | -8.9% | -23.6% |
| | 4 (open_domain) | 0.4279 | 0.4205 | 0.4117 | -1.7% | -3.8% | -2.1% |
| **llm_score** | 1 (single_hop) | 0.7908 | 0.7872 | 0.7411 | -0.5% | -6.3% | -5.9% |
| | 2 (temporal) | 0.6511 | 0.6449 | 0.6854 | -1.0% | **+5.3%** | **+6.3%** |
| | 3 (multi_hop) | 0.3542 | 0.4271 | 0.3438 | **+20.6%** | -2.9% | -19.5% |
| | 4 (open_domain) | 0.7027 | 0.6825 | 0.6825 | -2.9% | -2.9% | 0.0% |

**Overall 对比：**

| 指标 | 00 (Baseline) | 01 (Soft Forget) | 02 (QAMR) | 01 vs 00 | 02 vs 00 | 02 vs 01 |
|------|---------------|------------------|-----------|----------|----------|----------|
| bleu_score | 0.3159 | 0.3222 | 0.2862 | +2.0% | -9.4% | -11.2% |
| f1_score | 0.3969 | 0.4063 | 0.3616 | +2.4% | -8.9% | -11.0% |
| llm_score | 0.6864 | 0.6779 | 0.6727 | -1.2% | -2.0% | -0.8% |

**分析总结：**

1. **02 (QAMR) 整体表现不如预期**：
   - 相比 00 Baseline，所有指标全面下降（bleu -9.4%, f1 -8.9%, llm -2.0%）
   - 相比 01 Soft Forget，下降更明显（bleu -11.2%, f1 -11.0%）

2. **02 的唯一亮点 - temporal 的 llm_score**：
   - temporal 类别的 llm_score 提升 +5.3%（vs 00）和 +6.3%（vs 01）
   - 说明 QAMR 的 recency 权重配置 `[0.3, 0.1, 0.6]` 对时序问题的语义理解有帮助

3. **02 在 temporal 类别的精确匹配指标大幅下降**：
   - bleu_score: -22.1%（vs 00），-33.5%（vs 01）
   - f1_score: -25.7%（vs 00），-35.1%（vs 01）
   - 这与 llm_score 提升形成矛盾，可能是检索到的内容语义相关但文本匹配度低

4. **01 仍是最佳配置**：
   - 在 temporal 和 multi_hop 类别表现最好
   - 整体 bleu 和 f1 均优于 baseline



#### 03 vs 02

1. config

```yaml
# 三因素检索: Relevance + Value + Recency 
enable_qamr: true
recency_decay_factor: 0.995  # 每小时衰减约0.5%

# 不同问题类型的权重配置 (relevance, value, recency)
qamr_weights_temporal: [1.0, 0.0, 0.0]      # 时间问题重视 recency
qamr_weights_single_hop: [1.0, 0.0, 0.0]    # 事实查询重视 relevance  
qamr_weights_multi_hop: [1.0, 0.0, 0.0]     # 推理问题重视 value
qamr_weights_open_domain: [1.0, 0.0, 0.0]   # 开放问题均衡
```

2. score

```bash
Mean Scores Per Category:
          bleu_score  f1_score  llm_score  count         type
category                                                     
1             0.2073    0.3312     0.7411    282   single_hop
2             0.2529    0.3187     0.6667    321     temporal
3             0.1041    0.1399     0.3750     96    multi_hop
4             0.3411    0.4098     0.6849    841  open_domain

Overall Mean Scores:
bleu_score    0.2834
f1_score      0.3596
llm_score     0.6721
dtype: float64
```

#### 04 vs 03

1. config 

```yaml

# 三因素检索: Relevance + Value + Recency 
enable_qamr: true
recency_decay_factor: 0.999  # 每小时衰减约0.1%

# 不同问题类型的权重配置 (relevance, value, recency)
qamr_weights_temporal: [0.7, 0.0, 0.3]      # 时间问题重视 recency
qamr_weights_single_hop: [1.0, 0.0, 0.0]    # 事实查询重视 relevance  
qamr_weights_multi_hop: [0.7, 0.3, 0.0]     # 推理问题重视 value
qamr_weights_open_domain: [0.7, 0.2, 0.1]   # 开放问题均衡
```

2. scores

```bash
Mean Scores Per Category:
          bleu_score  f1_score  llm_score  count         type
category                                                     
1             0.2158    0.3404     0.7482    282   single_hop
2             0.2533    0.3177     0.6511    321     temporal
3             0.1111    0.1438     0.3438     96    multi_hop
4             0.3447    0.4121     0.6730    841  open_domain

Overall Mean Scores:
bleu_score    0.2875
f1_score      0.3625
llm_score     0.6617
dtype: float64
```


#### 05 vs 04

1. config

```yaml
# 三因素检索: Relevance + Value + Recency 
enable_qamr: true
recency_decay_factor: 0.999  # 每小时衰减约0.1%

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
1             0.2057    0.3291     0.7447    282   single_hop
2             0.2601    0.3273     0.6885    321     temporal
3             0.1030    0.1332     0.3333     96    multi_hop
4             0.3460    0.4137     0.6849    841  open_domain

Overall Mean Scores:
bleu_score    0.2872
f1_score      0.3627
llm_score     0.6747
dtype: float64
```