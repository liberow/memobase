# GPT-4o实验方案

## 实验目标

使用GPT-4o模型运行QAMR实验，与原始基准（Mem0、Zep等）使用相同的LLM，实现公平对比。

---

## 实验设计原则

1. **精简高效**：只运行必要的实验组，控制成本
2. **核心对比**：Baseline vs QAMR最优配置
3. **消融分析**：验证各维度（Relevance/Value/Recency）的独立贡献
4. **公平对比**：与原始基准使用相同LLM，可直接对比

---

## 实验配置

### 环境变量配置

```bash
# OpenAI API配置
export OPENAI_API_KEY="sk-gr-6775edabd806c9b3b15c0248e1ebd4c34ced7a9e"
export OPENAI_BASE_URL="https://endpoint.wendalog.com"

# LLM模型配置（所有实验统一使用）
export MODEL="gpt-4o"
export EMBEDDING_MODEL="text-embedding-3-small"

# Memobase配置
export DATABASE_URL="postgresql://memobase_user:memobase_pass@localhost:5432/memobase_db"
export REDIS_URL="redis://localhost:6379/0"
```

### 统一配置文件

**所有实验使用相同的LLM和Embedding配置**：

```yaml
# QAMR + GPT-4o 统一配置

# Language
language: en

# LLM (统一使用GPT-4o)
llm_api_key: "${OPENAI_API_KEY}"
llm_base_url: "${OPENAI_BASE_URL}"
best_llm_model: "gpt-4o"
thinking_llm_model: "gpt-4o"
value_scorer_model: "gpt-4o"

# Embedding (统一使用text-embedding-3-small)
embedding_provider: openai
embedding_api_key: "${OPENAI_API_KEY}"
embedding_model: "text-embedding-3-small"
embedding_base_url: "${OPENAI_BASE_URL}"
embedding_dim: 1536

# QAMR基础配置
enable_qamr: true
recency_decay_factor: 0.999
```

---

## 实验组

### 实验组1：Baseline (GPT-4o)

**目的**：建立用GPT-4o的Baseline性能基准，验证与原始基准的可比性

**配置**：
```yaml
enable_qamr: false  # 禁用QAMR，纯语义检索
```

**权重**：
- Relevance: 1.0
- Value: 0.0
- Recency: 0.0

**实验步骤**：
```bash
cd docs/experiments/locomo-benchmark

# 1. 清空数据库
PGPASSWORD=memobase_pass psql -h localhost -U memobase_user -d memobase_db -c "TRUNCATE user_events, users, user_profiles CASCADE;"
redis-cli FLUSHDB

# 2. 重启 Memobase Server
cd ../../src/server/api
fastapi dev api.py --port 8019

# 3. 加载数据
python run_experiments.py --technique_type memobase --method add

# 4. 运行检索测试
python run_experiments.py --technique_type memobase --method search

# 5. 评估结果
python evals.py --input_file results.json --output_file results/gpt4o_baseline_eval.json

# 6. 生成分数报告
python generate_scores.py --input_path="results/gpt4o_baseline_eval.json"
```

**预期结果**：与原始基准（Memobase v0.0.37）的LLM Score（75.78%）接近，验证实验设置正确

**实际结果**

```bash
Mean Scores Per Category:
          bleu_score  f1_score  llm_score  count         type
category                                                     
1             0.3433    0.4681     0.7447    282   single_hop
2             0.4338    0.5915     0.8037    321     temporal
3             0.1694    0.2331     0.4583     96    multi_hop
4             0.3907    0.5010     0.7122    841  open_domain

Overall Mean Scores:
bleu_score    0.3772
f1_score      0.4971
llm_score     0.7214
dtype: float64
```

---

### 实验组2：QAMR最优配置

**目的**：验证QAMR方法在GPT-4o上的效果，证明方法有效性

**配置权重**（基于豆包实验最优配置QAMR-02）：
```yaml
enable_qamr: true

# 不同查询类型的权重配置
qamr_weights_temporal: [0.7, 0.1, 0.2]      # Temporal: 重视Recency
qamr_weights_single_hop: [0.9, 0.1, 0.0]    # Single-hop: 重视Relevance
qamr_weights_multi_hop: [0.7, 0.3, 0.0]     # Multi-hop: 重视Value
qamr_weights_open_domain: [0.7, 0.2, 0.1]   # Open-domain: 均衡配置
```

**实验步骤**：
```bash
cd docs/experiments/locomo-benchmark

# 1. 清空数据库
PGPASSWORD=memobase_pass psql -h localhost -U memobase_user -d memobase_db -c "TRUNCATE user_events, users, user_profiles CASCADE;"
redis-cli FLUSHDB

# 2. 重启 Memobase Server (使用QAMR配置)
cd ../../src/server/api
fastapi dev api.py --port 8019

# 3. 加载数据
python run_experiments.py --technique_type memobase --method add

# 4. 运行检索测试
python run_experiments.py --technique_type memobase --method search

# 5. 评估结果
python evals.py --input_file results.json --output_file results/gpt4o_qamr_eval.json

# 6. 生成分数报告
python generate_scores.py --input_path="results/gpt4o_qamr_eval.json"
```

**预期结果**：相比Baseline有提升，Multi-hop类别提升显著（8%~12%）


**实际结果**

```bash
Mean Scores Per Category:
          bleu_score  f1_score  llm_score  count         type
category                                                     
1             0.3286    0.4574     0.7376    282   single_hop
2             0.4422    0.6019     0.8224    321     temporal
3             0.1559    0.2251     0.4271     96    multi_hop
4             0.3903    0.4981     0.7087    841  open_domain

Overall Mean Scores:
bleu_score    0.3752
f1_score      0.4952
llm_score     0.7201
dtype: float64
```

---

### 实验组3：消融实验 - 去掉Value维度

**目的**：验证Value维度的独立贡献

**配置**：
```yaml
enable_qamr: true

# 去掉Value，只使用Relevance和Recency
qamr_weights_temporal: [0.5, 0.0, 0.5]      # Temporal: R+T
qamr_weights_single_hop: [1.0, 0.0, 0.0]    # Single-hop: 纯R
qamr_weights_multi_hop: [1.0, 0.0, 0.0]     # Multi-hop: 纯R (无Value)
qamr_weights_open_domain: [0.8, 0.0, 0.2]   # Open-domain: R+T
```

**实验步骤**：
```bash
# 清空数据库 → 重启Server → add → search → eval → 生成报告
# (步骤同实验组2，配置文件不同)
```

**预期结果**：相比QAMR最优配置性能下降，Multi-hop下降最明显

**实际结果**

```bash
Mean Scores Per Category:
          bleu_score  f1_score  llm_score  count         type
category                                                     
1             0.3405    0.4668     0.7376    282   single_hop
2             0.4457    0.6025     0.8006    321     temporal
3             0.1967    0.2588     0.4583     96    multi_hop
4             0.3936    0.5017     0.7099    841  open_domain

Overall Mean Scores:
bleu_score    0.3825
f1_score      0.5012
llm_score     0.7182
dtype: float64
```

---

### 实验组4：消融实验 - 去掉Recency维度

**目的**：验证Recency维度的独立贡献

**配置**：
```yaml
enable_qamr: true

# 去掉Recency，只使用Relevance和Value
qamr_weights_temporal: [1.0, 0.0, 0.0]      # Temporal: 纯R (无Recency)
qamr_weights_single_hop: [1.0, 0.0, 0.0]    # Single-hop: 纯R
qamr_weights_multi_hop: [0.7, 0.3, 0.0]     # Multi-hop: R+V
qamr_weights_open_domain: [0.8, 0.2, 0.0]   # Open-domain: R+V
```

**实验步骤**：
```bash
# 清空数据库 → 重启Server → add → search → eval → 生成报告
# (步骤同实验组2，配置文件不同)
```

**预期结果**：相比QAMR最优配置性能下降，Temporal下降最明显

**实际结果**

```bash
Mean Scores Per Category:
          bleu_score  f1_score  llm_score  count         type
category                                                     
1             0.3439    0.4711     0.7482    282   single_hop
2             0.4380    0.5968     0.8131    321     temporal
3             0.1563    0.2258     0.4583     96    multi_hop
4             0.3922    0.4989     0.7099    841  open_domain

Overall Mean Scores:
bleu_score    0.3782
f1_score      0.4972
llm_score     0.7227
dtype: float64
```

---

## 实验对比表

| 实验组 | Relevance | Value | Recency | 目的 |
|--------|-----------|-------|---------|------|
| Baseline | 1.0 | 0.0 | 0.0 | 建立基准 |
| QAMR最优 | 动态 | 动态 | 动态 | 证明方法有效 |
| 消融-无Value | 动态 | 0.0 | 动态 | 验证Value贡献 |
| 消融-无Recency | 动态 | 动态 | 0.0 | 验证Recency贡献 |

---

## 实验结果汇总模板

### 完整对比表

| 方法 | Temporal | Single-hop | Multi-hop | Open-domain | Overall |
|------|----------|------------|-----------|-------------|---------|
| Baseline (GPT-4o) | TBD | TBD | TBD | TBD | TBD |
| QAMR最优配置 | TBD | TBD | TBD | TBD | TBD |
| 消融-无Value | TBD | TBD | TBD | TBD | TBD |
| 消融-无Recency | TBD | TBD | TBD | TBD | TBD |
| **原始基准** | 85.05% | 70.92% | 52.08% | 77.17% | 75.78% |

### 消融分析

| 配置 | LLM Score | vs Baseline | vs QAMR最优 |
|------|-----------|--------------|----------------|
| Baseline (R only) | TBD | - | ↓ |
| QAMR最优 (R+V+T) | TBD | ↑ | - |
| R+T (无Value) | TBD | ↑ | ↓ |
| R+V (无Recency) | TBD | ↑ | ↓ |

**分析**：
- 如果R+T和R+V都优于Baseline，说明各维度独立有效
- 如果QAMR最优优于R+T和R+V，说明三个维度有协同效应

---

## 成本估算

### GPT-4o成本（4组实验）

| 阶段 | 每组调用次数 | 4组总计 | 模型 | 成本 |
|-------|-------------|---------|------|------|
| add阶段 | ~1540次 | ~6160次 | gpt-4o | ~$60 |
| search阶段 | ~1540次 | ~6160次 | gpt-4o | ~$60 |
| eval阶段 | ~1540次 | ~6160次 | gpt-4o-mini | ~$12 |
| Embedding | ~3080次 | ~12320次 | text-3-small | ~$4 |
| **总计** | - | - | - | **~$136** |

### GPT-4o-mini成本（可选，节省成本）

| 阶段 | 每组调用次数 | 4组总计 | 模型 | 成本 |
|-------|-------------|---------|------|------|
| add阶段 | ~1540次 | ~6160次 | gpt-4o-mini | ~$8 |
| search阶段 | ~1540次 | ~6160次 | gpt-4o-mini | ~$8 |
| eval阶段 | ~1540次 | ~6160次 | gpt-4o-mini | ~$2 |
| Embedding | ~3080次 | ~12320次 | text-3-small | ~$4 |
| **总计** | - | - | - | **~$22** |

**建议**：
- 如果预算紧张，先用gpt-4o-mini跑4组实验（~$22）
- 结果满意后，再用gpt-4o跑Baseline和QAMR最优两组（~$50）用于论文

---

## 实验优先级

| 优先级 | 实验组 | 说明 |
|---------|---------|------|
| P0 | Baseline (GPT-4o) | 建立基准，必须 |
| P1 | QAMR最优配置 | 证明方法有效，核心 |
| P2 | 消融-无Value | 验证Value维度贡献 |
| P3 | 消融-无Recency | 验证Recency维度贡献 |

---

## 实验流程脚本（可选）

为了提高效率，可以编写自动化脚本：

```bash
#!/bin/bash
# run_all_experiments.sh

EXPERIMENTS=("baseline" "qamr" "ablation_no_value" "ablation_no_recency")

for exp in "${EXPERIMENTS[@]}"; do
    echo "========================================="
    echo "Running experiment: $exp"
    echo "========================================="

    # 清空数据库
    PGPASSWORD=memobase_pass psql -h localhost -U memobase_user -d memobase_db -c "TRUNCATE user_events, users, user_profiles CASCADE;"
    redis-cli FLUSHDB

    # 根据实验类型加载配置
    case $exp in
        baseline)
            export QAMR_CONFIG="config_baseline.yaml"
            ;;
        qamr)
            export QAMR_CONFIG="config_qamr.yaml"
            ;;
        ablation_no_value)
            export QAMR_CONFIG="config_ablation_no_value.yaml"
            ;;
        ablation_no_recency)
            export QAMR_CONFIG="config_ablation_no_recency.yaml"
            ;;
    esac

    # 重启Server
    cd ../../src/server/api
    fastapi dev api.py --port 8019 &
    SERVER_PID=$!
    sleep 10

    # 运行实验
    cd docs/experiments/locomo-benchmark
    python run_experiments.py --technique_type memobase --method add
    python run_experiments.py --technique_type memobase --method search
    python evals.py --input_file results.json --output_file "results/gpt4o_${exp}_eval.json"
    python generate_scores.py --input_path="results/gpt4o_${exp}_eval.json"

    # 停止Server
    kill $SERVER_PID

    echo "Experiment $exp completed!"
    echo ""
done

echo "All experiments completed!"
```

---

## 实验检查清单

- [ ] 环境变量配置正确（OPENAI_API_KEY、DATABASE_URL、REDIS_URL）
- [ ] PostgreSQL数据库可连接且为空
- [ ] Redis缓存已清空
- [ ] Memobase Server正常启动
- [ ] 数据集文件存在（locomo10.json）
- [ ] 每次实验后结果JSON文件已保存
- [ ] 成本监控开启（记录API调用量）

---

## 论文更新要点

实验完成后，论文需要更新：

### 4.1.3 实验环境
```
- LLM模型：GPT-4o（用于所有GPT-4o实验）
- Embedding模型：text-embedding-3-small（1536维）
- 实验组：4组（Baseline、QAMR最优、消融-无Value、消融-无Recency）
```

### 4.2.1 整体性能对比表
添加新的实验结果表格，包含：
- Baseline (GPT-4o)
- QAMR最优配置
- 消融-无Value
- 消融-无Recency
- 与原始基准的对比

### 4.2.2 消融实验小节
```
4.2.2 消融实验

为了验证QAMR各维度的独立贡献，我们进行了消融实验...

[插入消融结果和分析]
```

### 6.1 研究局限
删除"模型差异限制"相关内容，因为实验已使用相同LLM与原始基准对比。

---

## 预期结果

基于豆包实验结果和GPT-4o的能力预期：

| 指标 | Baseline (GPT-4o) | QAMR最优 | 提升 |
|------|-------------------|-----------|------|
| Overall | ~75% | ~77%~79% | 2%~4% |
| Temporal | ~83% | ~86%~88% | 3%~5% |
| Single-hop | ~70% | ~72%~74% | 2%~4% |
| Multi-hop | ~50% | ~58%~62% | 8%~12% ⭐ |
| Open-domain | ~75% | ~78%~82% | 3%~7% |

**与原始基准对比**：
- Baseline (GPT-4o)应接近Memobase v0.0.37 (75.78%)
- QAMR最优应超越或接近Memobase v0.0.37
- Multi-hop类别的提升将是主要贡献
