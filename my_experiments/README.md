# Agent Memory

## 1. 环境配置

### 1.1 获取代码与数据

**Memobase 源码**

- 公开仓库：<https://github.com/memodb-io/memobase>
- 推荐用 HTTPS 克隆（无需事先配置 GitHub SSH）：

```bash
git clone https://github.com/memodb-io/memobase.git
cd memobase
```

- 若已配置 SSH，也可使用：

```bash
git clone git@github.com:memodb-io/memobase.git
cd memobase
```

- 没有 `git` 时：在浏览器打开上述仓库页面，使用 **Code → Download ZIP** 下载源码压缩包，解压后进入解压目录即可。

**LOCOMO 评测数据（复现第 3 节 LOCOMO / QAMR 实验时需要）**

- 数据说明与文件入口：<https://github.com/snap-research/locomo/tree/main/data>
- 下载其中的 `locomo10.json`，放到本仓库的 `docs/experiments/locomo-benchmark/dataset/` 下（若目录不存在请先 `mkdir -p docs/experiments/locomo-benchmark/dataset`）。
- 更完整的评测说明见 `docs/experiments/locomo-benchmark/README.md`。

```bash
wget -O docs/experiments/locomo-benchmark/dataset/locomo10.json \
https://raw.githubusercontent.com/snap-research/locomo/main/data/locomo10.json
```

### 1.2 项目环境

```bash
# 若尚未进入仓库根目录，请先 cd 到你的 memobase 克隆路径

conda create -n memobase python=3.11 -y
conda activate memobase

# 安装 **API 服务端** 依赖（与 pyproject.toml 一致，含 FastAPI、tiktoken、typeguard 等）
cd src/server/api
python -m pip install -e .
cd ../..

# 若只需要调用云端/HTTP 客户端（不写服务端），可用仓库根目录的轻量依赖：
# pip install -r requirements.txt
```

### 1.3 数据存储

1. Postgres（**必须**带 [pgvector](https://github.com/pgvector/pgvector) 扩展，否则启动时会报 `vector.control` / `type "vector" does not exist`）

```bash
apt update
apt install -y postgresql postgresql-contrib

# 安装与当前 PostgreSQL 主版本一致的 pgvector（下面以 14 为例，请用 ls /usr/share/postgresql/ 查看本机版本号）
apt install -y postgresql-14-pgvector
# Ubuntu 22.04 等默认源里通常 **没有** postgresql-14-pgvector，会报 Unable to locate package。任选其一：

# --- 方式 A：添加 PostgreSQL 官方源（PGDG）后再装（推荐）---
apt install -y curl ca-certificates lsb-release
install -d /usr/share/postgresql-common/pgdg
curl -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc --fail https://www.postgresql.org/media/keys/ACCC4CF8.asc
sh -c 'echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
apt update
apt install -y postgresql-14-pgvector

# --- 方式 B：从源码编译到当前 PG（不增加 PGDG 源时）---
# apt install -y postgresql-server-dev-14 build-essential git
# cd /tmp && git clone --branch v0.8.0 https://github.com/pgvector/pgvector.git && cd pgvector && make && make install
# service postgresql restart

# --- 方式 C：Docker 见上文「pgvector/pgvector:pg14」---

# 常见 Debian/Ubuntu 容器（主版本号用 ls /usr/share/postgresql/ 查看，例如 14 / 16）：
service postgresql start  ||  pg_ctlcluster 14 main start

# 进入 postgres 用户执行 SQL
su - postgres -c "psql -c \"CREATE USER memobase_user WITH PASSWORD 'memobase_pass';\""
su - postgres -c "psql -c \"CREATE DATABASE memobase_db OWNER memobase_user;\""
# 在业务库中启用扩展（服务启动时也会执行 CREATE EXTENSION，但必须先装好系统级 pgvector 包）
su - postgres -c "psql -d memobase_db -c \"CREATE EXTENSION IF NOT EXISTS vector;\""

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

# 建议先确认环境变量（本地实验常用）
export DATABASE_URL="postgresql+psycopg2://memobase_user:memobase_pass@localhost:5432/memobase_db"
export REDIS_URL="redis://localhost:6379/0"
export ACCESS_TOKEN="secret"  # 需与实验端 MEMOBASE_API_KEY 保持一致

# fastapi
fastapi dev api.py --port 8019

#  uvicorn
uvicorn api:app --reload --host 0.0.0.0 --port 8019
```

## 3. LOCOMO + QAMR 完整实验命令

---

### 0. 第二次跑（或任意新一轮）前的标准流程

> 目的：避免上一轮残留数据污染结果，保证可复现。

```bash
# 进入项目根目录
cd ~/caofuping/agent/memobase

# 1) 确保 PostgreSQL / Redis 在运行
service postgresql start || pg_ctlcluster 14 main start
service redis-server start || redis-server --bind 0.0.0.0 --port 6379 &

# 2) 清空状态（必做）
PGPASSWORD=memobase_pass psql -h localhost -U memobase_user -d memobase_db \
  -c "TRUNCATE user_events, users, user_profiles CASCADE;"
redis-cli FLUSHDB

# 3) 清理上轮产物（建议）
cd docs/experiments/locomo-benchmark
mkdir -p results
rm -f results.json
rm -f results/memobase_locomo_baseline_00_eval.json
cd ~/caofuping/agent/memobase
```

服务端（建议在单独终端）：

```bash
cd ~/caofuping/agent/memobase/src/server/api
fastapi dev api.py --port 8019
```

实验端（另一个终端）：

```bash
cd ~/caofuping/agent/memobase
export PYTHONPATH="$(pwd)/src/client:$PYTHONPATH"
export MEMOBASE_PROJECT_URL="http://localhost:8019"
export MEMOBASE_API_KEY="secret"   # 必须与服务端 ACCESS_TOKEN 一致

cd docs/experiments/locomo-benchmark
```

---

### 阶段 1：LOCOMO Baseline

1. command

```bash
# 在仓库根目录执行，避免相对路径错误
cd ~/caofuping/agent/memobase

# 实验端环境变量（必须）
export PYTHONPATH="$(pwd)/src/client:$PYTHONPATH"
export MEMOBASE_PROJECT_URL="http://localhost:8019"
export MEMOBASE_API_KEY="secret"   # 必须与服务端 ACCESS_TOKEN 一致

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
  --input_file results/memobase_locomo_baseline_gpt_result.json \
  --output_file results/memobase_locomo_baseline_gpt_eval.json

# 4. 生成分数报告
python generate_scores.py \
  --input_path results/memobase_locomo_baseline_00_eval.json
```

常见报错快速排查：

- `ModuleNotFoundError: No module named 'memobase'`：未设置 `PYTHONPATH` 到 `src/client`。
- `401 Unauthorized`：`MEMOBASE_API_KEY` 与服务端 `ACCESS_TOKEN` 不一致，或服务未重启导致旧变量未生效。
- `api_key of memobase client is required`：未设置 `MEMOBASE_API_KEY`。

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
# 在仓库根目录 memobase/ 下执行
export PYTHONPATH="$(pwd)/src/client:$PYTHONPATH"

# 进入实验目录
cd ./docs/experiments/locomo-benchmark

# 1. 在开启 QAMR 的 Memobase 上加载对话数据
python run_experiments.py \
  --technique_type memobase \
  --method add

# 2. 运行检索测试，生成预测答案（QAMR）
python run_experiments.py \
  --technique_type memobase \
  --method search \
  2>&1 | tee search.log

# 3. 评估结果
python evals.py \
  --input_file results/qaver/memobase_locomo_llm_weight_predictor_doubao_results.json \
  --output_file results/qaver/memobase_locomo_llm_weight_predicto_doubao_eval.json

# 4. 生成分数报告
python generate_scores.py \
  --input_path results/qaver/memobase_locomo_llm_weight_predicto_doubao_eval.json
```

