# 固定开发集：本地 Qwen 与 DeepSeek 模型对照

固定的 MuSiQue 50 题、227 文档缩减语料开发集；不是原论文分数。

| 模型与检索 | Recall@1 | Recall@5 | Recall@10 | EM | F1 | 平均每题秒 | 缓存响应总 tokens |
|---|---:|---:|---:|---:|---:|---:|---:|
| deepseek/hipporag | 0.3717 | 0.8617 | 0.9683 | 0.5200 | 0.6105 | 2.15 | 499193 |
| deepseek/standard | 0.3750 | 0.8000 | 0.8650 | 0.5000 | 0.6352 | 1.42 | 72785 |
| local/hipporag | 0.3117 | 0.8117 | 0.9000 | 0.0600 | 0.1408 | 2.50 | 501648 |
| local/standard | 0.3750 | 0.8000 | 0.8650 | 0.0600 | 0.1736 | 1.01 | 76604 |

## 解释边界

本地 Qwen 使用 strict-json-v3 实体/事实抽取适配和重复惩罚；DeepSeek 使用原始抽取提示词并关闭思考模式。因此跨模型差异也包含推理配置差异，不能只归因于模型能力。
缓存响应总 tokens 是每个运行目录的去重响应库存，不是整个调试过程的账单。本地 HippoRAG 曾导入上次的 NER 响应缓存；其建索引时间不是冷启动值。DeepSeek 的收费还受缓存命中和调用时间影响，实际账单以服务商为准。

- local: HippoRAG−Dense 的配对 F1 差 -0.0329，5000 次 bootstrap 95% 区间 [-0.1105, 0.0432]。
- deepseek: HippoRAG−Dense 的配对 F1 差 -0.0246，5000 次 bootstrap 95% 区间 [-0.1315, 0.0900]。

两组 DeepSeek 开发集运行于 2026-10-17，缓存返回模型标识均为 `deepseek-flash`。图检索比 dense 在 Recall@5 高 6.17 个百分点，但回答 F1 低 2.46 个百分点；两个配对置信区间都跨过 0，当前样本不能证明 HippoRAG2 的回答质量优于 dense。

## DeepSeek sample 流程检查

3 篇文档、1 题的 sample 中，HippoRAG2 抽取 41 个三元组，图含 41 节点、82 边，问题有图种子；Recall@1=1、回答 F1=0。dense Recall@1=0、回答 F1=0。两种回答均指出给定段落没有明确说明所问教授与阿尔茨海默病的关系。样例存在证据缺口，不能用这一题比较问答能力；详情见 `sample_audit.md`。

## 失败信号

- deepseek/hipporag: 前五篇找齐支持文档 32/50；其中回答 F1=0 为 6 题；回答超过 20 英文词 0 题；响应到达长度上限 0 条。
- deepseek/standard: 前五篇找齐支持文档 24/50；其中回答 F1=0 为 2 题；回答超过 20 英文词 1 题；响应到达长度上限 1 条。
- local/hipporag: 前五篇找齐支持文档 28/50；其中回答 F1=0 为 15 题；回答超过 20 英文词 19 题；响应到达长度上限 4 条。
- local/standard: 前五篇找齐支持文档 24/50；其中回答 F1=0 为 10 题；回答超过 20 英文词 20 题；响应到达长度上限 0 条。

## 源结果

- deepseek/hipporag: `runs/musique-hipporag-4484a5d6cdac/result.json`
- deepseek/standard: `runs/musique-standard-983e4dddd3dd/result.json`
- local/hipporag: `runs/musique-hipporag-919e8c07ccb6/result.json`
- local/standard: `runs/musique-standard-2fa2fe6c41f1/result.json`

DeepSeek 是可更新的模型别名，记录调用日期及返回模型名；本实验不等于论文原模型、原 embedding 或完整语料实验。
