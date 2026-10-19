"""Replay the two failed NER documents with an explicit local generation setting."""
import json
from common import ROOT, load_environment, local_config

def main():
    load_environment()
    from hipporag.utils.config_utils import BaseConfig
    from hipporag.llm.openai_gpt import CacheOpenAI
    from hipporag.information_extraction.openie_openai import OpenIE
    from hipporag.utils.misc_utils import compute_mdhash_id
    cfg=local_config()
    config=BaseConfig(save_dir=str(ROOT/'runs/repetition_probe'),llm_name=cfg['llm'],llm_base_url=cfg['base_url'])
    llm=CacheOpenAI.from_experiment_config(config)
    llm.llm_config.generate_params['extra_body']={'repetition_penalty':1.1,'repetition_context_size':256}
    from local_extraction_adapter import LocalExtractionAdapter
    wrapped=LocalExtractionAdapter(llm,ROOT/'reports/structured_probe_attempts.jsonl')
    target={'chunk-8be1a30fc405598da002a69f2f45634e','chunk-0a2997bcc62cde2a452d07a1a0d99d8f'}
    outputs=[]
    try:
        openie=OpenIE(wrapped,max_workers=1)
        for d in json.loads((ROOT/'data/musique_dev50/musique_corpus.json').read_text()):
            text=d['title']+'\n'+d['text']; key=compute_mdhash_id(text,prefix='chunk-')
            if key in target:
                r=openie.ner(key,text)
                outputs.append({'chunk':key,'title':d['title'],'entities':r.unique_entities,'metadata':r.metadata,'response':r.response})
        assert len(outputs)==2
    finally: llm.close()
    (ROOT/'reports/structured_probe.json').write_text(json.dumps(outputs,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps([{'chunk':r['chunk'],'entities':len(r['entities']),'metadata':r['metadata']} for r in outputs],indent=2))
if __name__=='__main__':main()
