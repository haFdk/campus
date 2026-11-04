"""Offline synthetic evaluation. Baseline is a frozen test artifact, never a runtime strategy."""
import argparse
import importlib.util
import json
import os
import platform
import socket
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'


def metrics(rows, key):
    exact = [r for r in rows if len(r['acceptable']) == 1]
    supplied = [r for r in rows if r[key]]
    targets = [r for r in rows if r['acceptable']]
    rejected = [r for r in rows if not r['acceptable']]
    counts = {}
    from app.services.category_policy import CATEGORIES
    for cat in CATEGORIES:
        tp = sum(r['acceptable'] == [cat] and r[key][:1] == [cat] for r in exact)
        fp = sum(r['acceptable'] != [cat] and r[key][:1] == [cat] for r in exact)
        fn = sum(r['acceptable'] == [cat] and r[key][:1] != [cat] for r in exact)
        counts[cat] = {'n': sum(r['acceptable'] == [cat] for r in exact),
                       'f1': 2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0,
                       'precision': tp/(tp+fp) if tp+fp else 0, 'recall': tp/(tp+fn) if tp+fn else 0}
    return {
        'top1_accuracy_single_label_including_abstention': sum(r[key][:1] == r['acceptable'] for r in exact)/len(exact),
        'macro_f1_single_label': statistics.mean(c['f1'] for c in counts.values()),
        'candidate_hit_rate_classifiable': sum(bool(set(r[key]) & set(r['acceptable'])) for r in targets)/len(targets),
        'coverage_all': len(supplied)/len(rows),
        'top1_accuracy_among_recommended': sum(r[key][0] in r['acceptable'] for r in supplied)/len(supplied) if supplied else None,
        'mean_candidates_when_recommended': statistics.mean(len(r[key]) for r in supplied) if supplied else 0,
        'irrelevant_candidates': sum(len(set(r[key])-set(r['acceptable'])) for r in rows),
        'invalid_recommended': sum(bool(r[key]) for r in rejected), 'invalid_total': len(rejected),
        'per_class': counts,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--split', choices=['dev', 'test'], required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    out = Path(args.output)
    if out.exists():
        raise SystemExit('Output already exists; choose another filename to preserve prior reports')
    def deny(*a, **k):
        raise RuntimeError('Evaluation network disabled')
    socket.socket.connect = deny
    import psutil
    from app.config import Config
    from app.services.classification import Classifier, MODEL_ID, MODEL_REVISION
    from app.services.category_lexicon import Lexicon
    spec = importlib.util.spec_from_file_location('frozen_baseline', ROOT/'tests/baselines/classification_title_v2.py')
    baseline_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(baseline_module)
    config = {k:getattr(Config,k) for k in dir(Config) if k.isupper()}
    baseline = baseline_module.Classifier(config)
    service = Classifier(config)
    started = time.perf_counter()
    baseline._load()
    cold = time.perf_counter()-started
    # Share exactly the same weights, tokenizer and thread setting for paired comparison.
    for name in ('model', 'tokenizer', 'entailment', 'contradiction'):
        setattr(service, name, getattr(baseline, name))
    service._get_lexicon()
    baseline.rank('独立预热文本')
    service.recommend('独立预热文本')
    rows = json.loads((ROOT/f'tests/data/hybrid_{args.split}.json').read_text(encoding='utf-8'))
    results = []
    max_rss = 0
    for i, row in enumerate(rows):
        started = time.perf_counter()
        ranked = baseline.rank(row['title'])
        base_seconds = time.perf_counter()-started
        top, second = ranked[:2]
        accepted = (top['category'] is not None and top['score'] >= config['CLASSIFICATION_MIN_SCORE']
                    and top['support'] >= config['CLASSIFICATION_MIN_SUPPORT']
                    and top['score']-second['score'] >= config['CLASSIFICATION_MIN_MARGIN'])
        started = time.perf_counter()
        lexical = service.lexicon.match(row['title'])
        lexical_seconds = time.perf_counter()-started
        started = time.perf_counter()
        response = service.recommend(row['title'])
        seconds = time.perf_counter()-started
        strong = Lexicon.strong(lexical)
        candidates = [r['category'] for r in response['candidates']]
        max_rss = max(max_rss, psutil.Process().memory_info().rss/2**20)
        results.append({**row, 'baseline_raw_top':top, 'baseline':[top['category']] if accepted else [],
                        'hybrid':candidates, 'retrieval':[r['category'] for r in lexical],
                        'lexicon_fallback':[r['category'] for r in strong] if 0<len(strong)<=3 else [],
                        'response':response, 'baseline_seconds':base_seconds,
                        'hybrid_seconds':seconds, 'retrieval_seconds':lexical_seconds})
        print(f'{i+1}/{len(rows)} {row["title"]}: {candidates}', flush=True)
    report = {'warning':'Agent synthetic; not real users or independent human labels. Fixed titles split before evaluation; familiar concepts may overlap.',
              'split':args.split, 'model':MODEL_ID, 'revision':MODEL_REVISION,
              'environment':{'python':platform.python_version(), 'cpu':platform.processor(),
                             'ram_gib':psutil.virtual_memory().total/2**30, 'threads':config['CLASSIFICATION_THREADS']},
              'config':{k:v for k,v in config.items() if k.startswith('CLASSIFICATION_')},
              'load_seconds':cold, 'max_sampled_rss_mb':max_rss,
              'timing_scope':'service call, no HTTP; excludes model load, includes tokenization; paired sequential CPU calls',
              'results':results}
    for key in ['baseline','hybrid','retrieval','lexicon_fallback']:
        report[key] = metrics(results,key)
    report['baseline_raw_top1_single_label'] = sum(r['baseline_raw_top']['category']==r['acceptable'][0] for r in results if len(r['acceptable'])==1)/sum(len(r['acceptable'])==1 for r in results)
    report['regressions'] = [r['id'] for r in results if r['baseline'] and r['baseline'][0] in r['acceptable'] and (not r['hybrid'] or r['hybrid'][0] not in r['acceptable'])]
    retrieved = [r for r in results if r['acceptable'] and set(r['retrieval']) & set(r['acceptable'])]
    report['ranking_stage'] = {
        'retrieval_contains_acceptable': len(retrieved),
        'correct_first_after_model': sum(bool(r['hybrid']) and r['hybrid'][0] in r['acceptable'] for r in retrieved),
        'acceptable_still_displayed': sum(bool(set(r['hybrid']) & set(r['acceptable'])) for r in retrieved),
        'model_rejected_all_retrieved_candidates': sum(not r['hybrid'] for r in retrieved),
    }
    report['hybrid_inference_latency_excluding_lexical_only_rejection'] = {
        'n': sum(r['response']['source'] in ('hybrid', 'model') for r in results),
        'median': statistics.median(r['hybrid_seconds'] for r in results if r['response']['source'] in ('hybrid', 'model')),
    }
    for key in ['baseline','hybrid','retrieval']:
        values = sorted(r[key+'_seconds'] for r in results)
        report[key+'_latency'] = {'n':len(values), 'median':statistics.median(values), 'p95':values[max(0,int(len(values)*.95)-1)]}
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('results','config')},ensure_ascii=False,indent=2))

if __name__ == '__main__':
    main()

