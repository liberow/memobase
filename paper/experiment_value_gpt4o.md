# Value-Based Memory Scoring - GPT-4o 实验方案

## 实验目标

专注于**Value维度**的有效性验证，使用GPT-4o模型在LoCoMo数据集上进行最小化实验，证明Value评分机制对记忆检索的改进作用。

---

## 实验设计原则

1. **极简高效**：只运行必要的实验组（仅2组）
2. **核心对比**：Baseline vs Value-enabled
3. **聚焦价值**：只验证Value维度的独立贡献，不引入Relevance/Recency的干扰
4. **单一模型**：统一使用GPT-4o，避免模型差异

---

## 实验配置

### 环境变量配置

```bash
# OpenAI API配置
export OPENAI_API_KEY="your_openai_api_key"
export OPENAI_BASE_URL="https://api.openai.com"

# Memobase配置
export DATABASE_URL="postgresql://memobase_user:memobase_pass@localhost:5432/memobase_db"
export REDIS_URL="redis://localhost:6379/0"
```

### 统一配置文件（所有实验使用）

**LLM配置（统一使用GPT-4o）**：
```yaml
# Language
language: en  # LoCoMo 是英文数据集，使用英文 prompt

# LLM - 统一使用GPT-4o
llm_api_key: "${OPENAI_API_KEY}"
llm_base_url: "${OPENAI_BASE_URL}"
best_llm_model: "gpt-4o"
thinking_llm_model: "gpt-4o"
value_scorer_model: "gpt-4o"  # Value评分也用GPT-4o

# Embedding - 统一使用text-embedding-3-small
embedding_provider: openai
embedding_api_key: "${OPENAI_API_KEY}"
embedding_model: "text-embedding-3-small"
embedding_base_url: "${OPENAI_BASE_URL}"
embedding_dim: 1536
```

---

## 实验组设计（仅2组）

### 实验组1：Baseline (纯语义检索)

**目的**：建立纯语义检索的性能基准

**配置**：
```yaml
# Value Scoring - 禁用
value_scoring_mode: "off"
```

**检索逻辑**：
- 仅使用余弦相似度进行排序
- 综合得分 = similarity (value_score不参与)

**实验步骤**：
```bash
cd docs/experiments/locomo-benchmark

# 1. 清空数据库
PGPASSWORD=memobase_pass psql -h localhost -U memobase_user -d memobase_db -c "TRUNCATE user_events, users, user_profiles CASCADE;"
redis-cli FLUSHDB

# 2. 配置文件 (config_baseline.yaml)
# 复制上面的LLM配置，添加:
value_scoring_mode: "off"

# 3. 重启 Memobase Server
cd ../../src/server/api
fastapi dev api.py --port 8019

# 4. 加载数据
cd ../../docs/experiments/locomo-benchmark
python run_experiments.py --technique_type memobase --method add

# 5. 运行检索测试
python run_experiments.py --technique_type memobase --method search

# 6. 评估结果
python evals.py --input_file results.json --output_file results/gpt4o_baseline_eval.json

# 7. 生成分数报告
python generate_scores.py --input_path="results/value/value_0.7/gpt4o_value_eval.json"
```

**实验结果**：
```bash
Mean Scores Per Category:
          bleu_score  f1_score  llm_score  count         type
category                                                     
1             0.3509    0.4713     0.7518    282   single_hop
2             0.4675    0.6469     0.8349    321     temporal
3             0.1967    0.2609     0.4375     96    multi_hop
4             0.4012    0.5113     0.7182    841  open_domain

Overall Mean Scores:
bleu_score    0.3931
f1_score      0.5166
llm_score     0.7312
dtype: float64
```

---

### 实验组2：Value-Enabled (价值感知检索)

**目的**：验证Value评分机制的有效性，寻找最优权重

**配置**：
```yaml
# Value Scoring - 启用soft模式
value_scoring_mode: "soft"
soft_rerank_alpha: 0.5  # 平衡Relevance和Value
value_score_threshold_event: 0.15  # 仅用于hard模式
```

**检索逻辑**：
- 综合得分 = α × similarity + (1-α) × value_score
- α = 0.5 时，Relevance和Value权重相同

**实验步骤**：
```bash
cd docs/experiments/locomo-benchmark

# 1. 清空数据库
PGPASSWORD=memobase_pass psql -h localhost -U memobase_user -d memobase_db -c "TRUNCATE user_events, users, user_profiles CASCADE;"
redis-cli FLUSHDB

# 2. 配置文件 (config_value.yaml)
# 复制上面的LLM配置，添加:
value_scoring_mode: "soft"
soft_rerank_alpha: 0.5
value_score_threshold_event: 0.15

# 3. 重启 Memobase Server
cd ./src/server/api
fastapi dev api.py --port 8019

# 4. 加载数据

# 建议从仓库根目录执行
cd ~/caofuping/agent/memobase

# 关键：把本地 client 放到 PYTHONPATH
export PYTHONPATH="$(pwd)/src/client:$PYTHONPATH"


cd ./docs/experiments/locomo-benchmark

python run_experiments.py --technique_type memobase --method add

# 5. 运行检索测试
python run_experiments.py --technique_type memobase --method search

# 6. 评估结果
python evals.py --input_file results.json --output_file results/gpt4o_baseline_eval.json

# 7. 生成分数报告
python generate_scores.py --input_path="results/gpt4o_baseline_eval.json"
```

**实验结果**：
```bash
Mean Scores Per Category:
          bleu_score  f1_score  llm_score  count         type
category                                                     
1             0.3439    0.4856     0.7199    282   single_hop
2             0.4499    0.6149     0.8069    321     temporal
3             0.1902    0.2466     0.4167     96    multi_hop
4             0.3907    0.4978     0.7063    841  open_domain

Overall Mean Scores:
bleu_score    0.3820
f1_score      0.5043
llm_score     0.7117
dtype: float64
```

---

## 实验对比表

| 实验组 | value_scoring_mode | soft_rerank_alpha | 检索逻辑 | 目的 |
|--------|------------------|------------------|-----------|------|
| Baseline | "off" | - | similarity only | 建立基准 |
| Value-Enabled | "soft" | 0.5 | 0.5×similarity + 0.5×value | 证明Value有效 |

---

## 预期结果与分析

### 1. 主要指标（LLM Score）

| 类别 | Baseline | Value-Enabled | 预期提升 |
|------|----------|--------------|----------|
| Single-hop | TBD | TBD | 平衡或微升 |
| Temporal | TBD | TBD | **预期提升** |
| **Multi-hop** | **TBD** | **TBD** | **预期显著提升** ⭐ |
| Open-domain | TBD | TBD | 平衡或微升 |
| **Overall** | **TBD** | **TBD** | **预期提升** |

### 2. 预期结果分析

| 指标 | 预期变化 | 原因 |
|------|----------|------|
| **Multi-hop LLM Score** | ↑ 5%~10% | Value评分过滤噪声，提升推理质量 |
| **Temporal BLEU/F1** | ↑ 3%~8% | Value评分帮助识别时序关键事件 |
| **Single-hop** | ~持平或微降 | 简单问题对Value不敏感 |
| **Overall LLM Score** | ↑ 2%~5% | 综合效果 |
| **Overall BLEU/F1** | ↑ 1%~3% | 检索精度提升 |

### 3. 如果结果不如预期

| 情况 | 可能原因 | 应对措施 |
|------|----------|----------|
| Overall无提升 | α=0.5不合适 | 尝试α=0.7或0.3 |
| Multi-hop下降 | Value评分质量差 | 调整value_scorer_prompt |
| 所有类别下降 | GPT-4o对Value评分不敏感 | 考虑改用DouBao |

---

## 实验检查清单

- [ ] 环境变量配置正确（OPENAI_API_KEY、DATABASE_URL、REDIS_URL）
- [ ] 配置文件中的value_scoring_mode正确设置
- [ ] PostgreSQL数据库可连接且为空
- [ ] Redis缓存已清空
- [ ] Memobase Server正常启动
- [ ] 数据集文件存在（locomo10.json）
- [ ] 每次实验后结果JSON文件已保存
- [ ] 成本监控（记录API调用量）

---

## 成本估算（GPT-4o）

| 阶段 | 2组总计 | 调用次数 | 模型 | 成本 |
|-------|---------|---------|------|------|
| add阶段 | ~3080次 | ~1540次/组 | gpt-4o | ~$30 |
| search阶段 | ~1540次 | ~770次/组 | gpt-4o | ~$15 |
| eval阶段 | ~1540次 | ~770次/组 | gpt-4o-mini | ~$6 |
| value评分 | ~1540次 | ~770次/组 | gpt-4o | ~$15 |
| Embedding | ~3080次 | ~1540次/组 | text-3-small | ~$4 |
| **总计** | - | - | - | **~$70** |

**说明**：value评分是额外开销，只在add阶段计算一次。

---

## 实验优先级

| 优先级 | 实验组 | 必要性 |
|---------|---------|--------|
| P0 | Baseline | 必须 |
| P0 | Value-Enabled (α=0.5) | 必须 |
| P1 | 如需优化，尝试α=0.7或0.3 | 可选 |

---

## 配置文件模板

### config_baseline.yaml

```yaml
# Language
language: en

# LLM
llm_api_key: "${OPENAI_API_KEY}"
llm_base_url: "${OPENAI_BASE_URL}"
best_llm_model: "gpt-4o"
thinking_llm_model: "gpt-4o"
value_scorer_model: "gpt-4o"

# Embedding
embedding_provider: openai
embedding_api_key: "${OPENAI_API_KEY}"
embedding_model: "text-embedding-3-small"
embedding_base_url: "${OPENAI_BASE_URL}"
embedding_dim: 1536

# Value Scoring
value_scoring_mode: "off"
```

### config_value.yaml

```yaml
# Language
language: en

# LLM
llm_api_key: "${OPENAI_API_KEY}"
llm_base_url: "${OPENAI_BASE_URL}"
best_llm_model: "gpt-4o"
thinking_llm_model: "gpt-4o"
value_scorer_model: "gpt-4o"

# Embedding
embedding_provider: openai
embedding_api_key: "${OPENAI_API_KEY}"
embedding_model: "text-embedding-3-small"
embedding_base_url: "${OPENAI_BASE_URL}"
embedding_dim: 1536

# Value Scoring
value_scoring_mode: "soft"
soft_rerank_alpha: 0.5
value_score_threshold_event: 0.15
```

---

## 实验结果汇总模板

### 完整对比表

| 方法 | Single-hop | Temporal | Multi-hop | Open-domain | Overall |
|------|------------|----------|-----------|-------------|---------|
| Baseline | TBD | TBD | TBD | TBD | TBD |
| Value-Enabled | TBD | TBD | TBD | TBD | TBD |
| **提升** | TBD | TBD | TBD | TBD | TBD |

### 指标对比

| 指标 | Baseline | Value-Enabled | 变化 | 变化率 |
|------|----------|--------------|------|--------|
| **llm_score** (Overall) | TBD | TBD | TBD | TBD |
| - Multi-hop | TBD | TBD | TBD | TBD |
| - Temporal | TBD | TBD | TBD | TBD |
| - Single-hop | TBD | TBD | TBD | TBD |
| - Open-domain | TBD | TBD | TBD | TBD |
| **bleu_score** (Overall) | TBD | TBD | TBD | TBD |
| **f1_score** (Overall) | TBD | TBD | TBD | TBD |

---

## 论文更新要点

### 4.1.3 实验环境
```
- LLM模型：GPT-4o（所有实验统一使用）
- Embedding模型：text-embedding-3-small（1536维）
- 实验组：2组（Baseline、Value-Enabled）
- 数据集：LoCoMo Benchmark
```

### 4.2.1 整体性能对比

```
我们在LoCoMo数据集上进行了对比实验。结果显示：
- Value-Enabled在Multi-hop类别上提升X%，证明Value评分有效过滤了噪声信息
- Overall LLM Score提升Y%，表明Value维度对整体检索质量有正向作用
```

### 4.2.2 Value评分机制分析

```
Value评分机制通过以下方式改进检索：
1. 过滤低价值噪声：降低无关事件对答案生成的干扰
2. 提升关键事件权重：确保重要信息被优先检索
3. 改善多跳推理：为复杂推理提供更高质量的证据
```

---

## 附录：Value评分原理

### Value Scoring机制

```python
# value_scorer.py 中的评分逻辑

# 1. 静态过滤（硬规则）
trivial_markers = ["哈哈", "嗯嗯", "好啊", "收到", r"\bok\b"]
if content contains trivial_markers:
    value_score = 0.0

# 2. LLM动态评分
value_score = llm_evaluate(content)
# 输出：0.000~1.000的浮点数
# 高分：包含具体事实、时间、地点、偏好
# 低分：纯闲聊、无新信息

# 3. 检索时重排序
combined_score = α × similarity + (1-α) × value_score
```

### 重排序公式

| α | Relevance权重 | Value权重 | 适用场景 |
|----|--------------|-----------|----------|
| 1.0 | 100% | 0% | 纯语义检索（Baseline） |
| 0.7 | 70% | 30% | 优先语义相似 |
| 0.5 | 50% | 50% | 平衡（本实验采用） |
| 0.3 | 30% | 70% | 优先高价值事件 |
| 0.0 | 0% | 100% | 纯价值检索 |

---

## 快速执行脚本

```bash
#!/bin/bash
# run_value_experiments.sh

echo "========================================="
echo "Experiment: Value-Based Scoring with GPT-4o"
echo "========================================="

# 实验组列表
EXPERIMENTS=("baseline" "value")

for exp in "${EXPERIMENTS[@]}"; do
    echo ""
    echo "========================================="
    echo "Running experiment: $exp"
    echo "========================================="

    # 清空数据库
    PGPASSWORD=memobase_pass psql -h localhost -U memobase_user -d memobase_db -c "TRUNCATE user_events, users, user_profiles CASCADE;"
    redis-cli FLUSHDB

    # 选择配置文件
    if [ "$exp" = "baseline" ]; then
        export CONFIG_FILE="config_baseline.yaml"
    else
        export CONFIG_FILE="config_value.yaml"
    fi

    echo "Using config: $CONFIG_FILE"

    # 重启Server (需要手动)
    echo "Please restart Memobase Server with config: $CONFIG_FILE"
    read -p "Press Enter when ready..."

    # 运行实验
    cd docs/experiments/locomo-benchmark
    python run_experiments.py --technique_type memobase --method add
    python run_experiments.py --technique_type memobase --method search
    python evals.py --input_file results.json --output_file "results/gpt4o_${exp}_eval.json"
    python generate_scores.py --input_path="results/gpt4o_${exp}_eval.json"

    echo ""
    echo "Experiment $exp completed!"
    echo ""
done

echo "========================================="
echo "All experiments completed!"
echo "========================================="
```

---

## 注意事项

1. **数据隔离**：每次实验前必须清空数据库和Redis
2. **配置加载**：确保Server使用正确的配置文件
3. **成本控制**：GPT-4o成本较高，建议先小规模测试
4. **结果保存**：每次实验后立即保存评估结果
5. **失败重试**：网络不稳定时，实验脚本会自动重试

---

## 预期论文贡献

### 主要结论

1. **Value评分机制在GPT-4o上有效**
2. **Multi-hop问题提升最显著**（预期5%-10%）
3. **Overall性能稳步提升**（预期2%-5%）

### 发表建议

- **适合**：中文会议（CCL/CCIR）、Workshop
- **需要补充**：统计显著性检验、消融实验（不同α值）
- **核心卖点**：Value维度独立贡献、Multi-hop显著提升

---

## 总结

本实验方案通过**仅2组实验**验证了Value维度的有效性：

- ✅ Baseline：建立纯语义检索基准
- ✅ Value-Enabled：证明Value评分的价值
- ✅ 极简设计：总成本~$70
- ✅ 清晰对比：聚焦Value的独立贡献

如果实验结果符合预期（Overall提升≥2%，Multi-hop提升≥5%），可以作为一个完整的论文工作发表。
