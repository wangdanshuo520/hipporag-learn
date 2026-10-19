"""Summarize matched local dev runs; no changes to upstream retrieval or evaluation."""
import json, sqlite3, random, statistics
from common import ROOT

def main():
    runs={}
    for path in (ROOT/'runs').glob('musique-*/result.json'):
        r=json.loads(path.read_text())
        if r.get('status')=='completed' and r.get('questions')==50 and r.get('documents')==227 and r['config'].get('backend')=='local' and r['config'].get('local_adapter'):
            method=r['config']['method']
            if method in runs: raise ValueError('Multiple matching runs; choose explicitly before reporting')
            runs[method]=(path,r)
    assert set(runs)=={'hipporag','standard'}, 'Both completed runs required'
    a,b=[runs[m][1] for m in ('hipporag','standard')]
    for key in ('corpus_sha256','questions_sha256','embedding_snapshot','local_model_snapshot','llm','base_url','local_adapter'):
        assert a['config'][key]==b['config'][key], key
    assert [p['id'] for p in a['per_question']]==[p['id'] for p in b['per_question']]
    report={'scope':'Fixed reduced-corpus development diagnostic; not paper-score reproduction','questions':50,'documents':227,'adapter':a['config']['local_adapter'],'methods':{}}
    for method,(path,r) in runs.items():
        times=[p['seconds'] for p in r['per_question']]
        rows=[]
        for db in (path.parent/'index/llm_cache').glob('*.sqlite'):
            with sqlite3.connect(db) as con: rows.extend(json.loads(x[0]) for x in con.execute('select metadata from cache'))
        imported_ids=set()
        if r.get('raw_cache_reuse'):
            with sqlite3.connect(r['raw_cache_reuse']['source']) as con:
                imported_ids={json.loads(x[0]).get('response_id') for x in con.execute('select metadata from cache')}
        new_rows=[x for x in rows if x.get('response_id') not in imported_ids]
        d={'raw_cache_reuse':r.get('raw_cache_reuse'),'new_responses_since_import':{'requests':len(new_rows),**{k:sum(int(x.get(k) or 0) for x in new_rows) for k in ('prompt_tokens','completion_tokens','total_tokens')}},'run':str(path.relative_to(ROOT)), 'retrieval':r['retrieval_metrics'],'qa':r['qa_metrics'],
           'indexing_seconds':r['indexing_seconds'],'query_seconds_mean':statistics.mean(times),
           'query_seconds_median':statistics.median(times),'query_seconds_max':max(times),
           'unique_response_tokens':r['cached_unique_response_usage'],
           'length_terminated_responses':sum(x.get('finish_reason')=='length' for x in rows)}
        if method=='hipporag':
            docs=json.loads(next((path.parent/'index').glob('openie_results_ner_*.json')).read_text())['docs']
            attempt_path=path.parent/'extraction_attempts.jsonl'
            attempts=[json.loads(line) for line in attempt_path.read_text().splitlines()]
            d['extraction_attempts']=len(attempts)
            d['format_retries']=sum(x['attempt']==2 for x in attempts)
            d['shape_normalizations']=sum(x['normalized_json_shape'] for x in attempts)
            d.update(graph=r['graph_info'],queries_with_graph_seeds=r['queries_with_graph_seeds'],
                queries_without_graph_seeds=50-r['queries_with_graph_seeds'],
                documents_without_entities=sum(not x['extracted_entities'] for x in docs),
                documents_without_triples=sum(not x['extracted_triples'] for x in docs),
                extraction_document_count=len(docs))
        report['methods'][method]=d
    rng=random.Random(20261015)
    delta=[x['qa']['F1']-y['qa']['F1'] for x,y in zip(a['per_question'],b['per_question'])]
    boot=sorted(sum(rng.choices(delta,k=50))/50 for _ in range(5000))
    report['paired_F1_difference']={'hipporag_minus_dense':statistics.mean(delta),'bootstrap_95_percentile':[boot[125],boot[4874]],'bootstrap_seed':20261015,'resamples':5000}
    report['per_question']=[{'id':x['id'],'question':s['question'],'hipporag_answer':s['answer'],'dense_answer':t['answer'],'gold_answers':s['gold_answers'],'hipporag':x,'dense':y,'graph_seeds':s['graph_seeds']} for x,y,s,t in zip(a['per_question'],b['per_question'],a['solutions'],b['solutions'])]
    (ROOT/'reports/dev50_results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    lines=['# 本地 Qwen 的 50 题开发集对照','', '固定 50 题 / 227 文档；缩减检索语料，不能与论文完整语料指标比较。原始本地配置因 2/227 NER 解析失败而中止，以下为明确标注的格式适配配置。两条方法均使用 repetition_penalty=1.1、context_size=256；HippoRAG 抽取另加严格 JSON 提示、最多一次格式重试和不增删字符串的列表结构规范化。官方源码未修改，但提示词与生成配置不同于原始运行。', '', '| 方法 | Recall@1 | Recall@5 | Recall@10 | EM | F1 | 建索引秒 | 平均每题秒 |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for m,d in report['methods'].items():
        vals=[d['retrieval'][f'Recall@{k}'] for k in (1,5,10)]+[d['qa'][k] for k in ('ExactMatch','F1')]
        lines.append('| '+m+' | '+' | '.join(f'{v:.4f}' for v in vals)+f" | {d['indexing_seconds']:.1f} | {d['query_seconds_mean']:.2f} |")
    lines+=['', '## 运行质量与成本','']
    for m,d in report['methods'].items():
        u=d['unique_response_tokens'];lines.append(f"- {m}: {u['requests']} 条缓存响应，输入 {u['prompt_tokens']} / 输出 {u['completion_tokens']} tokens；{d['length_terminated_responses']} 条响应达到长度上限。")
    h=report['methods']['hipporag']; lines += [f"- HippoRAG: {h['documents_without_entities']}/{h['extraction_document_count']} 文档无实体，{h['documents_without_triples']}/{h['extraction_document_count']} 文档无三元组；{h['queries_without_graph_seeds']}/50 问题无图种子。",'- 空抽取是异常代理指标，不等同于已确认的解析错误；截断统计包含所有 LLM 阶段。', '- 全部使用本地模型，无外部模型 API 费用。HippoRAG 本轮复用适配探索阶段的 NER 原始响应缓存，建索引秒数不是冷启动值，不能直接比较完整建索引成本。缓存库存 token 含继承的响应，也不等于本轮新生成量；JSON 另记录相对导入缓存新增的响应用量。耗时还受模型服务 KV 缓存、系统负载和调用顺序影响。','', '## 配对比较','',str(report['paired_F1_difference']),'','原始逐题结果、引用运行路径和统计见 dev50_results.json。小开发集不足以证明泛化优势；先分析失败再改算法。']
    (ROOT/'reports/dev50_results.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='per_question'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
