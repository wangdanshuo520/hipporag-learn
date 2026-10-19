"""Validate that format adaptation preserves strings and fails closed after one retry."""
import json,tempfile
from pathlib import Path
from common import load_environment
from local_extraction_adapter import LocalExtractionAdapter

class Fake:
    global_config=None
    def __init__(self,values,finish="stop"): self.values=iter(values);self.calls=0;self.finish=finish
    def infer(self,**kwargs):
        self.calls+=1
        return next(self.values),{'finish_reason':self.finish},False

def main():
    load_environment()
    with tempfile.TemporaryDirectory() as d:
        for text,system,expected in [
            ('[["Speaker"],["House"]]','extract named entities',{'named_entities':['Speaker','House']}),
            ('[["A","works at","B"]]','construct an RDF graph',{'triples':[['A','works at','B']]}),
            ('{"named_entities":["A"]}','extract named entities',{'named_entities':['A']})]:
            llm=Fake([text]);adapter=LocalExtractionAdapter(llm,Path(d)/'log')
            result,_,_=adapter.infer([{'role':'system','content':system},{'role':'user','content':'document'}])
            assert json.loads(result)==expected and llm.calls==1
        llm=Fake(['[["A"], ["B"], ["unfinished'],finish='length')
        adapter=LocalExtractionAdapter(llm,Path(d)/'log')
        result,_,_=adapter.infer([{'role':'system','content':'extract named entities'},{'role':'user','content':'document'}])
        assert json.loads(result)=={'named_entities':['A','B']} and llm.calls==1
        llm=Fake(['[[123]]' ,'[[123]]']);adapter=LocalExtractionAdapter(llm,Path(d)/'log')
        result,_,_=adapter.infer([{'role':'system','content':'extract named entities'},{'role':'user','content':'document'}])
        assert result=='[[123]]' and llm.calls==2
    print('PASS: nested entity strings preserved; bare triples preserved; valid JSON unchanged; non-string entities not coerced; retry bounded at one')
if __name__=='__main__':main()
