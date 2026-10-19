# 官方 sample 中间结果审查（2026-10-15）

## 结论

现有 sample 适合检查执行流程，不足以验证证据推理。问题询问研究 Alzheimer’s 的 Stanford 教授，但三个输入段落均未提供 Alzheimer’s 的明确关系。不能把命中参考答案解释为基于文档的成功推理，也不能凭这个样例把失败归因于图算法。

## 实际检查

检查文件：`runs/sample-hipporag-0b38b7b43018/result.json`、同目录 index/openie_results_ner_default_model.json，以及 dense 对照结果。

- 人工阅读全部 24 条抽取三元组：多数对应原文身份、机构和研究方法；未发现任何表达 Alzheimer’s 研究关系的三元组。部分宾语是长句片段，实体粒度不一致。
- Thomas 段落 NER 只有 4 个实体，漏掉 Stanford University 等关键机构；后续三元组仍含 Stanford University，说明 NER 与三元组抽取并非完全一致。不能简单将所有信息缺失归因于 NER。
- 事实筛选保留 `David Eagleman — is — American neuroscientist` 和 `Karl Alexander Deisseroth — applied — integrated optical and genetic strategies...`，均没有支撑 Alzheimer’s 约束。
- HippoRAG 排序：David、Karl、Thomas；正确支持段落排名第 3，分数为 0。dense 排序：Karl、David、Thomas。图检索确实执行，但没有改善目标段落排名。
- HippoRAG 回答 `Thomas Sudhof.`，参考答案 `Thomas C. Sudhof`，F1=0.8、EM=0；F1 损失涉及中间名缺失，不能直接等价于人物判断错误。
- dense 回答 `Karl Deisseroth.`，F1=0、EM=0。

## 对下一阶段的影响

固定采用 MuSiQue 的 50 题 reduced-corpus 开发集。保留每题所有支持段落，抽取每题 2 个原始干扰段落后合并去重。支持标签仅用于构造语料和评估，不注入模型输入、检索 metadata 或提示词。

两条基线使用完全相同的 Qwen、BGE、语料、问题和 QA 上下文数量；报告逐题结果、Recall@1/5/10、F1/EM、图种子缺失率和抽取异常。这个开发集的分数不能与官方完整 11656 文档实验或论文表格直接比较。
