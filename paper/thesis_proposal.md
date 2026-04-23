# 开题报告

## 一、开题报告基本信息

### 1. 论文题目

#### 中文

超越语义检索：多维度智能体记忆方法

#### 英文

Beyond Semantic Retrieval: Multi-dimensional Memory Management for LLM Agents

## 二、选题

### 1.研究意义及创新点

#### 研究意义

大语言模型（Large Language Model, LLM）智能体正在成为人工智能应用的核心范式。然而，当前LLM智能体面临的一个关键挑战是**长期记忆管理**——如何在长周期交互中有效存储、组织和检索历史信息。传统的检索增强生成（RAG）方法主要依赖语义相似度进行记忆检索，难以应对以下关键挑战：

1. **时间敏感性**：用户的偏好、状态和环境会随时间变化，最新信息往往更具参考价值
2. **信息质量差异**：不同记忆片段的信息密度和实用价值差异显著
3. **查询类型多样性**：不同类型的问题（事实查询、时间推理、多跳推理等）需要不同的检索策略

本研究旨在提出一种超越传统语义检索的多维度记忆管理方法，通过融合语义相关性、信息价值和时间新近性三个维度，提升智能体在长周期对话场景下的记忆能力和回答质量，为构建更智能、更个性化的AI助手奠定基础。

#### 创新点

1. **超越语义检索的多维度记忆框架（QAMR）**：提出Query-Aware Memory Retrieval方法，突破传统单一语义相似度的局限，将语义相关性（Relevance）、信息价值（Value）和时间新近性（Recency）三个维度融合为统一的记忆评分与检索机制

2. **动态权重自适应策略**：根据查询类型（temporal、single_hop、multi_hop、open_domain）自动调整三个维度的权重配比，实现针对不同查询场景的精准记忆管理

3. **LLM驱动的记忆价值评估**：利用大语言模型对记忆片段进行价值评分，识别高信息密度的关键记忆，过滤低价值的闲聊内容，提升记忆质量

4. **端到端的智能体记忆系统实现**：在开源项目Memobase基础上实现完整的QAMR系统，并在LoCoMo长对话基准测试上验证有效性，多跳推理问题准确率提升11.7%

### 2.国内外研究综述

#### 大语言模型智能体研究现状

自GPT-4、Claude等大型语言模型问世以来，LLM-based Agent成为AI领域的研究热点。代表性工作包括：

- **AutoGPT/BabyAGI**（2023）：早期的自主智能体框架，展示了LLM进行自主规划和执行的能力
- **ReAct**（Yao et al., 2023）：提出推理-行动交替范式，增强智能体的决策能力
- **ToolLLM**（Qin et al., 2024）：研究智能体的工具使用能力
- **AgentBench**（Liu et al., 2023）：建立智能体能力评估基准

#### 记忆机制研究现状

记忆是智能体实现长期交互的核心能力：

- **MemGPT**（Packer et al., 2023）：提出分层记忆架构，模拟人类的工作记忆和长期记忆
- **Mem0**（2024）：开源记忆层框架，支持用户画像和事件记忆
- **Memobase**（2024）：结合Profile和Event的混合记忆架构
- **Generative Agents**（Park et al., 2023）：在模拟环境中实现基于记忆的智能体行为

#### 检索增强生成（RAG）研究现状

- **Dense Passage Retrieval**（Karpukhin et al., 2020）：开创性的稠密向量检索方法
- **Self-RAG**（Asai et al., 2023）：自适应检索增强生成
- **RAPTOR**（Sarthi et al., 2024）：递归抽象的树状检索方法
- **HyDE**（Gao et al., 2023）：假设文档嵌入方法

#### 现有研究的不足

1. 现有RAG方法主要依赖单一语义相似度，未充分考虑时间因素和信息质量差异
2. 检索策略缺乏对查询类型的感知和适应，无法针对不同问题采用最优策略
3. 记忆质量评估多依赖启发式规则，缺乏智能化、自适应的评估手段

### 3.主要参考文献

[1] Park J S, O'Brien J C, Cai C J, et al. Generative agents: Interactive simulacra of human behavior[C]//Proceedings of the 36th Annual ACM Symposium on User Interface Software and Technology. 2023.

[2] Packer C, Gori V, Hernandes M, et al. MemGPT: Towards LLMs as operating systems[J]. arXiv preprint arXiv:2310.08560, 2023.

[3] Yao S, Zhao J, Yu D, et al. ReAct: Synergizing reasoning and acting in language models[J]. arXiv preprint arXiv:2210.03629, 2022.

[4] Karpukhin V, Oğuz B, Min S, et al. Dense passage retrieval for open-domain question answering[C]//EMNLP. 2020.

[5] Lewis P, Perez E, Piktus A, et al. Retrieval-augmented generation for knowledge-intensive NLP tasks[J]. NeurIPS, 2020.

[6] Asai A, Wu Z, Wang Y, et al. Self-RAG: Learning to retrieve, generate, and critique through self-reflection[J]. arXiv preprint arXiv:2310.11511, 2023.

[7] Liu X, Yu H, Zhang H, et al. AgentBench: Evaluating LLMs as agents[J]. arXiv preprint arXiv:2308.03688, 2023.

[8] Gao L, Ma X, Lin J, et al. Precise zero-shot dense retrieval without relevance labels[C]//ACL. 2023.

[9] Sarthi P, Abdullah S, Tuli A, et al. RAPTOR: Recursive abstractive processing for tree-organized retrieval[J]. arXiv preprint arXiv:2401.18059, 2024.

[10] Maharana A, Lee D H, Tulyakov S, et al. Evaluating very long-term conversational memory of LLM agents[C]//ACL. 2024.

## 三、研究方案

### 1.研究目标、研究内容及拟解决的关键问题

#### 研究目标

本研究旨在设计并实现一种超越传统语义检索的多维度智能体记忆方法（QAMR），提升LLM智能体在长周期对话场景中的记忆管理能力和问答质量。具体目标包括：

1. 在LoCoMo长对话基准测试上，整体问答准确率（LLM Score）提升5%以上
2. 在多跳推理问题（multi_hop）类别上获得显著改进
3. 构建可复用的开源多维度记忆管理框架

#### 研究内容

**（1）多维度记忆评分机制设计**

提出QAMR（Query-Aware Memory Retrieval）评分公式，突破传统单一语义相似度的局限：

$$Score_{QAMR} = w_r \cdot Relevance + w_v \cdot Value + w_t \cdot Recency$$

其中：
- $Relevance$：基于embedding向量计算的语义相似度
- $Value$：LLM评估的记忆信息价值分数
- $Recency$：基于指数衰减的时间新近性分数

**（2）查询类型感知的动态权重策略**

针对不同查询类型设计差异化权重配置：

| 查询类型 | Relevance权重 | Value权重 | Recency权重 | 设计理由 |
|---------|--------------|----------|------------|---------|
| temporal | 0.5 | 0.0 | 0.5 | 时间问题需要近期信息 |
| single_hop | 1.0 | 0.0 | 0.0 | 事实查询依赖语义匹配 |
| multi_hop | 0.7 | 0.3 | 0.0 | 多跳推理需要高质量证据 |
| open_domain | 0.6 | 0.2 | 0.2 | 开放问题需要均衡考量 |

**（3）LLM驱动的记忆价值评估器**

设计Value Scorer模块，利用LLM判断记忆片段的长期价值：
- 高价值：具体事实、时间信息、个人偏好、关系变化
- 低价值：闲聊问候、简单确认、情感表达

**（4）记忆检索与重排序流程**

实现完整的QAMR检索流程：
1. 语义向量检索召回候选记忆
2. 并行计算三维度分数
3. 加权融合并重排序
4. 返回Top-K结果

#### 拟解决的关键问题

1. **时间敏感性建模**：如何设计合理的时间衰减函数，平衡新旧信息的重要性
2. **价值评估准确性**：如何设计有效的Prompt使LLM准确评估记忆价值
3. **权重配置优化**：如何确定不同查询类型的最优权重组合
4. **效率与效果平衡**：如何在保证检索质量的同时控制计算开销

### 2.研究方法、技术路线及可行性分析

#### 研究方法

1. **文献研究法**：系统梳理LLM Agent、记忆机制、RAG等领域的研究进展
2. **实验研究法**：在LoCoMo基准上进行对比实验，验证方法有效性
3. **消融研究法**：分析各组件（Relevance/Value/Recency）的独立贡献
4. **案例分析法**：深入分析典型成功/失败案例，指导方法改进

#### 技术路线

```
┌─────────────────────────────────────────────────────────────────┐
│                         研究技术路线                              │
├─────────────────────────────────────────────────────────────────┤
│  阶段1: 基础框架搭建                                              │
│  ├── 部署Memobase记忆系统                                        │
│  ├── 集成LoCoMo评测数据集                                        │
│  └── 建立Baseline性能基准                                        │
├─────────────────────────────────────────────────────────────────┤
│  阶段2: QAMR核心算法实现                                          │
│  ├── 设计QAMR评分公式                                            │
│  ├── 实现Recency时间衰减模块                                     │
│  ├── 实现Value Scorer价值评估模块                                │
│  └── 实现查询类型分类与权重映射                                   │
├─────────────────────────────────────────────────────────────────┤
│  阶段3: 实验验证与优化                                            │
│  ├── 在LoCoMo上进行端到端评测                                    │
│  ├── 权重参数调优                                                │
│  ├── 消融实验分析各组件贡献                                      │
│  └── 错误案例分析与方法改进                                      │
├─────────────────────────────────────────────────────────────────┤
│  阶段4: 论文撰写与整理                                            │
│  ├── 撰写实验报告和论文                                          │
│  ├── 整理开源代码                                                │
│  └── 答辩准备                                                    │
└─────────────────────────────────────────────────────────────────┘
```

#### 可行性分析

1. **技术可行性**
   - Memobase开源项目提供了完整的记忆存储和检索基础设施
   - LoCoMo数据集提供了标准化的评测框架和指标
   - LLM API（如GPT-4、Doubao）可支持Value评估任务

2. **实验可行性**
   - 已完成Baseline实验，建立性能基准（LLM Score: 0.6864）
   - 初步实验验证QAMR方法有效性（LLM Score: 0.6994，提升1.9%）
   - 具备GPU计算资源和API调用额度

3. **时间可行性**
   - 核心框架已实现，后续主要是优化和论文撰写工作
   - 研究周期合理，各阶段任务明确

### 3.研究计划、进度安排

| 阶段 | 时间 | 主要任务 | 预期成果 |
|-----|------|---------|---------|
| 第一阶段 | 第1-2周 | 文献调研、方案设计 | 完成开题报告 |
| 第二阶段 | 第3-5周 | QAMR核心算法实现 | 完成系统原型 |
| 第三阶段 | 第6-8周 | 实验验证与参数调优 | 获得实验结果 |
| 第四阶段 | 第9-10周 | 消融实验与案例分析 | 完成分析报告 |
| 第五阶段 | 第11-13周 | 论文撰写与修改 | 完成论文初稿 |
| 第六阶段 | 第14-16周 | 论文完善与答辩准备 | 完成最终论文 |

## 四、研究工作基础

### 1.相关的研究工作积累、已取得的主要成果

#### 已完成的工作

1. **系统部署与集成**
   - 完成Memobase记忆系统的本地部署（PostgreSQL + Redis + FastAPI）
   - 集成LoCoMo长对话评测数据集
   - 建立完整的实验流程（数据加载→检索测试→结果评估→分数报告）

2. **QAMR核心模块实现**
   - 实现`qamr.py`：QAMR评分框架，包含权重管理、时间衰减、综合评分
   - 实现`value_scorer.py`：LLM驱动的记忆价值评估器
   - 实现查询类型到权重的映射机制

3. **实验结果**

   **Baseline性能（纯语义检索）**：
   ```
   Overall: BLEU=0.3159, F1=0.3969, LLM_Score=0.6864
   - single_hop:  LLM_Score=0.7908
   - temporal:    LLM_Score=0.6511
   - multi_hop:   LLM_Score=0.3542
   - open_domain: LLM_Score=0.7027
   ```

   **QAMR优化后性能**：
   ```
   Overall: BLEU=0.3325, F1=0.4173, LLM_Score=0.6994
   - single_hop:  LLM_Score=0.7482
   - temporal:    LLM_Score=0.6760 (+3.8%)
   - multi_hop:   LLM_Score=0.3958 (+11.7%)
   - open_domain: LLM_Score=0.7265 (+3.4%)
   ```

   **主要发现**：
   - QAMR在temporal类别提升显著，验证了时间感知的有效性
   - multi_hop类别提升最大，说明Value维度有助于筛选高质量证据
   - 整体BLEU提升5.3%，F1提升5.1%，LLM Score提升1.9%

4. **代码开源**
   - 基于Memobase开发的QAMR扩展已整理为可复现的代码库
   - 包含完整的实验脚本和配置文件

### 2.尚缺少的研究条件和拟解决问题的途径

#### 尚缺少的条件

1. **更大规模的评测**：当前仅在LoCoMo数据集上验证，缺乏更多数据集的泛化性验证
2. **查询类型自动分类**：当前依赖数据集提供的category标签，实际应用需要自动分类
3. **权重的自动学习**：当前权重基于人工调优，缺乏自动化优化机制
4. **更多Baseline对比**：需要与MemGPT、Mem0等其他记忆系统进行对比

#### 拟解决途径

1. **数据集扩展**：收集或构建更多长对话场景的评测数据
2. **查询分类器**：训练轻量级分类模型或设计LLM-based分类器
3. **参数优化**：使用网格搜索或贝叶斯优化自动调参
4. **系统对比**：部署其他开源记忆系统进行公平对比实验
