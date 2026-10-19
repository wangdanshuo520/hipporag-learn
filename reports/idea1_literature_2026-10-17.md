# Idea 1 相关工作核查（2026-10-17）

研究问题：工业手册的适用条件未被完整观察时，如何检索相关证据、避免给出错误设备处置建议，并只在答案可能改变时询问缺失字段。

| 工作 | 已覆盖的能力 | 与 Idea 1 的关系 | 可复现资源 |
|---|---|---|---|
| [HippoRAG 2, ICML 2025](https://proceedings.mlr.press/v267/gutierrez25a.html) | OpenIE 图、段落连接、LLM 事实筛选、PPR 检索 | 本项目的图检索基线；未显式求解设备条件满足/未知和澄清决策 | [官方代码和样本](https://github.com/OSU-NLP-Group/HippoRAG)；已在本地复现替换模型基线 |
| [RuleRAG, arXiv 2025 v3](https://arxiv.org/abs/2410.22353) | 用规则共同引导检索和生成，提供 RuleQA | “把规则加入 RAG”已不是空白；需比较规则提示和规则检索 | 论文报告 RuleQA；本轮未核实官方公开代码，暂不标记为可运行基线 |
| [TelcoAI, Findings IJCNLP 2025](https://aclanthology.org/2025.findings-ijcnlp.80/) | 技术规范的元数据引导检索和专家问题评测 | 工业文档使用 metadata 已有先例；硬过滤必须作为强基线 | 论文公开；本轮未核实代码/评测集公开性 |
| [Clarify When Necessary, Findings NAACL 2025](https://aclanthology.org/2025.findings-naacl.306/) | 估计澄清问题的效用 | 不能把“会追问”单独作为创新 | 论文公开；本轮未核实代码 |
| [AskBench, Findings ACL 2026](https://aclanthology.org/2026.findings-acl.845/) | 何时/问什么的交互评测与训练 | 可借鉴评测设计；不是工业设备适用性证据检索 | [官方代码与数据](https://github.com/jialeuuz/askbench) |
| [SAGE-Agent / ClarifyBench, Findings ACL 2026](https://aclanthology.org/2026.findings-acl.2028/) | 结构化不确定性和信息价值引导的追问 | 与原设想的“动作会否改变才追问”高度接近，是主要新颖性风险 | [作者提供的代码/基准入口](https://github.com/MananSuri27/ClarifyBench)，本轮未在本机复现 |

目前合理的差异化假设是：把**检索证据的适用性不确定性**和**错误处置动作的代价**共同纳入决策，区分“设备状态缺失”“手册证据缺失”“证据互相冲突”。是否构成独立方法贡献，取决于相对 metadata 过滤、规则提示、现有澄清方法的实证增益与严格数据集，而不是模块名称。

本轮只对 HippoRAG 2 和本地强基线做小规模可复现诊断。RuleRAG、AskBench、SAGE-Agent 的原方法尚未在相同工业集上公平迁移；因此不能将本轮结果宣称为击败这些工作，也不能据此判断顶会发表概率。
