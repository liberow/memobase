# Agent Memory

## 1. 环境配置

### 1.1 项目环境

```bash
# clone 
git clone git@github.com:liberow/memobase.git

# create env 
conda create -n memobase python=3.11 -y

# activate env 
conda activate memobase

# into project
cd memobase/

# install package 
pip install -r requirements.txt
```

### 1.2. 数据存储

1. Postgres

```bash
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

```bash
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

```bash
cd ./src/server/api

fastapi dev api.py --port 8019
```

## 3. LOCOMO + QAMR 完整实验命令

---

### 阶段 1：LOCOMO Baseline

1. command

```bash
# 进入实验目录
cd ./docs/experiments/locomo-benchmark

# 1. 在 Memobase 上加载对话数据
python run_experiments.py \
  --technique_type memobase \
  --method add

# 2. 运行检索测试，生成预测答案
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

### 阶段 2：优化机制


---

### 阶段 3：LOCOMO After QAMR（使用 QAMR 机制）

#### 3.1. 设置配置

```yaml
enable_qamr: true
recency_decay_factor: 0.999  # 每小时衰减约 0.1%

# 不同问题类型的权重配置 (relevance, value, recency)
qamr_weights_temporal: [0.5, 0.0, 0.5]      # 时间问题重视 recency
qamr_weights_single_hop: [1.0, 0.0, 0.0]    # 事实查询重视 relevance  
qamr_weights_multi_hop: [0.7, 0.3, 0.0]     # 推理问题重视 value
qamr_weights_open_domain: [0.6, 0.2, 0.2]   # 开放问题均衡
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
# 设置 PYTHONPATH
export PYTHONPATH="/workspace/liber/memory/memobase/src/client:$PYTHONPATH"

# 进入实验目录
cd ./docs/experiments/locomo-benchmark

# 1. 在开启 QAMR 的 Memobase 上加载对话数据
python run_experiments.py \
  --technique_type memobase \
  --method add

# 2. 运行检索测试，生成预测答案（QAMR）
python run_experiments.py \
  --technique_type memobase \
  --method search

# 3. 评估结果
python evals.py \
  --input_file results.json \
  --output_file results/memobase_locomo_qamr_02_eval.json

# 4. 生成分数报告
python generate_scores.py \
  --input_path results/memobase_locomo_qamr_02_eval.json
```

