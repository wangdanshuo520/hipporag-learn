"""Opt-in small-model output-contract adaptation; upstream algorithms stay intact."""
import copy,json,threading

class LocalExtractionAdapter:
    version='strict-json-v3'
    def __init__(self,llm,log_path):
        self.llm=llm; self.global_config=llm.global_config; self.log_path=log_path; self.lock=threading.Lock()
    def infer(self,messages,**kwargs):
        from hipporag.information_extraction.openie_openai import _extract_ner_from_response,_extract_json_list_field
        from hipporag.utils.llm_utils import fix_broken_generated_json
        ner='extract named entities' in messages[0]['content']
        schema='{"named_entities": ["entity string"]}' if ner else '{"triples": [["subject", "relation", "object"]]}'
        instruction='\nReturn ONLY one JSON object with this structure: '+schema+'. Use a flat list of strings for named_entities; triples must be lists of exactly three strings. Do not repeat entries. Do not include explanations or Markdown.'
        adapted=copy.deepcopy(messages); adapted[-1]['content']+=instruction
        for attempt in range(2):
            text,meta,hit=self.llm.infer(messages=adapted,**kwargs)
            normalized=False
            try:
                payload=json.loads(fix_broken_generated_json(text) if meta.get("finish_reason")=="length" else text)
                values=payload.get('named_entities') if isinstance(payload,dict) else payload
                if ner and isinstance(values,list) and any(isinstance(x,list) for x in values):
                    flat=[]
                    def flatten(items,depth=0):
                        if depth>3: raise ValueError('Too deeply nested')
                        for item in items:
                            if isinstance(item,str): flat.append(item)
                            elif isinstance(item,list): flatten(item,depth+1)
                            else: raise ValueError('Non-string entity')
                    flatten(values)
                    text=json.dumps({'named_entities':flat}); normalized=True
                elif not ner and isinstance(payload,list) and all(isinstance(t,list) and len(t)==3 and all(isinstance(x,str) for x in t) for t in payload):
                    text=json.dumps({'triples':payload}); normalized=True
            except (ValueError,TypeError): pass
            try:
                parsed=fix_broken_generated_json(text) if meta.get('finish_reason')=='length' else text
                if ner: _extract_ner_from_response(parsed)
                else: _extract_json_list_field(parsed,'triples')
                error=None
            except Exception as exc: error=str(exc)
            with self.lock:
                with self.log_path.open('a') as f:
                    f.write(json.dumps({'stage':'ner' if ner else 'triples','attempt':attempt+1,'cache_hit':hit,'normalized_json_shape':normalized,'metadata':meta,'parse_error':error})+'\n')
            if error is None or attempt==1: return text,meta,hit
            adapted=copy.deepcopy(messages)
            adapted[-1]['content']+=instruction+'\nPrevious attempt violated the JSON schema. Output the JSON object directly; nested entity lists are not allowed.'
