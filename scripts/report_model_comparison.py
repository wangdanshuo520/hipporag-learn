"""Compare completed 50-question DeepSeek and local runs on identical data."""
import json, sqlite3, random, statistics
from pathlib import Path
from common import ROOT

def choose():
    found={}
    for path in (ROOT/'runs').glob('musique-*/result.json'):
        r=json.loads(path.read_text())
        if r.get('status')!='completed' or r.get('questions')!=50 or r.get('documents')!=227: continue
        c=r['config']; backend=c['backend']; method=c['method']
        if backend=='local' and not c.get('local_adapter'): continue
        key=(backend,method)
        if key in found: raise ValueError(f'Multiple completed runs for {key}; choose explicitly')
        found[key]=(path,r)
    return found

def main():
    found=choose(); expected={(b,m) for b in ('local','deepseek') for m in ('hipporag','standard')}
    assert set(found)==expected, f'Missing completed runs: {expected-set(found)}'
    ref=found['local','hipporag'][1]['config']
    for _,r in found.values():
        for key in ('dataset','corpus_sha256','questions_sha256','embedding_snapshot'):
            assert r['config'][key]==ref[key],key
        assert len(r['per_question'])==50
    order=[p['id'] for p in found['local','hipporag'][1]['per_question']]
    assert all([p['id'] for p in r['per_question']]==order for _,r in found.values())
    result={'scope':'固定的 MuSiQue 50 题、227 文档缩减语料开发集；不是原论文分数。',
            'comparison_limit':'本地 Qwen 使用 strict-json-v3 实体/事实抽取适配和重复惩罚；DeepSeek 使用原始抽取提示词并关闭思考模式。因此跨模型差异也包含推理配置差异，不能只归因于模型能力。',
            'question_ids':order,'runs':{}}
    for (backend,method),(path,r) in sorted(found.items()):
        rows=[]
        for db in (path.parent/'index/llm_cache').glob('*.sqlite'):
            with sqlite3.connect(db) as con: rows.extend(json.loads(x[0]) for x in con.execute('select metadata from cache'))
        key=f'{backend}/{method}'
        result['runs'][key]={'result_path':str(path.relative_to(ROOT)),'config':r['config'],
                             'retrieval':r['retrieval_metrics'],'qa':r['qa_metrics'],
                             'indexing_seconds':r['indexing_seconds'],
                             'query_seconds_mean':statistics.mean(p['seconds'] for p in r['per_question']),
                             'queries_with_graph_seeds':r.get('queries_with_graph_seeds'),
                             'response_models':sorted({x.get('model') for x in rows if x.get('model')}),
                             'cached_response_usage':r['cached_unique_response_usage'],
                             'length_terminated_responses':sum(x.get('finish_reason')=='length' for x in rows),
                             'complete_support_at_5':sum(p['retrieval']['Recall@5']>=.9999 for p in r['per_question']),
                             'complete_support_at_5_but_f1_zero':sum(p['retrieval']['Recall@5']>=.9999 and p['qa']['F1']==0 for p in r['per_question']),
                             'answers_over_20_words':sum(len(s['answer'].split())>20 for s in r['solutions']),
                             'raw_cache_reuse':r.get('raw_cache_reuse')}
    rng=random.Random(20261017)
    result['paired_differences']={}
    for backend in ('local','deepseek'):
        h=found[backend,'hipporag'][1]['per_question'];d=found[backend,'standard'][1]['per_question']
        delta=[x['qa']['F1']-y['qa']['F1'] for x,y in zip(h,d)]
        boot=sorted(sum(rng.choices(delta,k=50))/50 for _ in range(5000))
        result['paired_differences'][backend]={'hipporag_minus_dense_f1':statistics.mean(delta),
            'bootstrap_95_percentile':[boot[125],boot[4874]],'resamples':5000,'seed':20261017}
    (ROOT/'reports/model_comparison.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    lines=['# 固定开发集：本地 Qwen 与 DeepSeek 模型对照','',result['scope'],'',
        '| 模型与检索 | Recall@1 | Recall@5 | Recall@10 | EM | F1 | 平均每题秒 | 缓存响应总 tokens |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for key,x in result['runs'].items():
        vals=[x['retrieval'][f'Recall@{n}'] for n in (1,5,10)]+[x['qa'][n] for n in ('ExactMatch','F1')]
        lines.append('| '+key+' | '+' | '.join(f'{v:.4f}' for v in vals)+f" | {x['query_seconds_mean']:.2f} | {x['cached_response_usage']['total_tokens']} |")
    lines+=['','## 解释边界','',result['comparison_limit'],
         '缓存响应总 tokens 是每个运行目录的去重响应库存，不是整个调试过程的账单。本地 HippoRAG 曾导入上次的 NER 响应缓存；其建索引时间不是冷启动值。DeepSeek 的收费还受缓存命中和调用时间影响，实际账单以服务商为准。','']
    for backend,x in result['paired_differences'].items():
        lines.append(f"- {backend}: HippoRAG−Dense 的配对 F1 差 {x['hipporag_minus_dense_f1']:.4f}，5000 次 bootstrap 95% 区间 [{x['bootstrap_95_percentile'][0]:.4f}, {x['bootstrap_95_percentile'][1]:.4f}]。")
    lines+=['','两组 DeepSeek 开发集运行于 2026-10-17，缓存返回模型标识均为 `deepseek-flash`。图检索比 dense 在 Recall@5 高 6.17 个百分点，但回答 F1 低 2.46 个百分点；两个配对置信区间都跨过 0，当前样本不能证明 HippoRAG2 的回答质量优于 dense。','',
            '## DeepSeek sample 流程检查','',
            '3 篇文档、1 题的 sample 中，HippoRAG2 抽取 41 个三元组，图含 41 节点、82 边，问题有图种子；Recall@1=1、回答 F1=0。dense Recall@1=0、回答 F1=0。两种回答均指出给定段落没有明确说明所问教授与阿尔茨海默病的关系。样例存在证据缺口，不能用这一题比较问答能力；详情见 `sample_audit.md`。','',
            '## 失败信号','']
    for key,x in result['runs'].items():
        lines.append(f"- {key}: 前五篇找齐支持文档 {x['complete_support_at_5']}/50；其中回答 F1=0 为 {x['complete_support_at_5_but_f1_zero']} 题；回答超过 20 英文词 {x['answers_over_20_words']} 题；响应到达长度上限 {x['length_terminated_responses']} 条。")
    lines+=['','## 源结果','']
    for key,x in result['runs'].items():
        lines.append(f"- {key}: `{x['result_path']}`")
    lines+=['','DeepSeek 是可更新的模型别名，记录调用日期及返回模型名；本实验不等于论文原模型、原 embedding 或完整语料实验。']
    (ROOT/'reports/model_comparison.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({k:{'Recall@5':v['retrieval']['Recall@5'],'F1':v['qa']['F1'],'tokens':v['cached_response_usage']['total_tokens']} for k,v in result['runs'].items()},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
