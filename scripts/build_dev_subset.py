"""Fixed reduced-corpus MuSiQue development set, never a paper leaderboard."""
import hashlib, json, random
from common import ROOT, UPSTREAM

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    source = UPSTREAM / 'reproduce/dataset'
    samples = json.loads((source/'musique.json').read_text())
    corpus = json.loads((source/'musique_corpus.json').read_text())
    rng = random.Random(20261015)
    selected = [samples[i] for i in sorted(rng.sample(range(len(samples)), 50))]
    available = {(d['title'], d['text']): d for d in corpus}
    docs = {}; support_keys = set(); distractor_keys = set()
    for s in selected:
        support = [p for p in s['paragraphs'] if p['is_supporting']]
        distractors = [p for p in s['paragraphs'] if not p['is_supporting']]
        assert support
        for p in support:
            key=(p['title'], p['paragraph_text']); assert key in available
            support_keys.add(key); docs[key] = available[key]
        for p in rng.sample(distractors, min(2,len(distractors))):
            key=(p['title'], p['paragraph_text']); assert key in available
            distractor_keys.add(key); docs[key] = available[key]
    # Deterministic order independent of support labels.
    keys=sorted(docs, key=lambda k: hashlib.sha256(('\n'.join(k)).encode()).hexdigest())
    out=ROOT/'data/musique_dev50'; out.mkdir(exist_ok=True)
    for name,obj in [('musique.json',selected),('musique_corpus.json',[docs[k] for k in keys])]:
        (out/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
    manifest={'seed':20261015,'questions':len(selected),'documents':len(keys),
        'unique_support_documents':len(support_keys),'distractors_not_supporting_any_selected_question':len(distractor_keys-support_keys),
        'selection':'50 randomly sampled questions; all supports plus 2 native distractors/question, union deduplicated',
        'scope':'reduced-corpus development diagnostic, not official full-corpus scores',
        'question_ids':[s['id'] for s in selected],
        'source_sha256':{n:sha(source/n) for n in ['musique.json','musique_corpus.json']},
        'output_sha256':{n:sha(out/n) for n in ['musique.json','musique_corpus.json']}}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({k:v for k,v in manifest.items() if k not in ['question_ids','source_sha256','output_sha256']},indent=2))
if __name__=='__main__': main()
