"""Synthetic smoke evaluation, not an independent real-world accuracy claim."""
import argparse
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--split', choices=['dev', 'test'], default='test')
    parser.add_argument('--template')
    parser.add_argument('--input-type', choices=['title', 'legacy-text'], default='title')
    args = parser.parse_args()
    # A stronger offline check than an environment flag: deny socket connections.
    def deny(*a, **kw):
        raise RuntimeError('Network forbidden during evaluation')
    socket.socket.connect = deny
    import psutil
    from app.config import Config
    from app.services.classification import Classifier, CATEGORIES, MODEL_ID, MODEL_REVISION
    config = {k: getattr(Config, k) for k in dir(Config) if k.isupper()}
    if args.template:
        config['CLASSIFICATION_TEMPLATE'] = args.template
    service = Classifier(config)
    start = time.perf_counter()
    service._load()
    cold = time.perf_counter() - start
    if args.input_type == 'title':
        rows = json.loads((ROOT / 'tests/data/classification_titles.json').read_text(encoding='utf-8'))
    else:
        rows = json.loads((ROOT / 'tests/data/classification_samples.json').read_text(encoding='utf-8'))
        rows = [r for r in rows if r['split'] == args.split]
    results = []
    for i, row in enumerate(rows):
        start = time.perf_counter()
        ranked = service.rank(row['title'] if args.input_type == 'title' else row['text'])
        top, second = ranked[:2]
        accepted = (top['category'] is not None and top['score'] >= config['CLASSIFICATION_MIN_SCORE']
                    and top['support'] >= config['CLASSIFICATION_MIN_SUPPORT']
                    and top['score'] - second['score'] >= config['CLASSIFICATION_MIN_MARGIN'])
        results.append({**row, 'top': top, 'margin': top['score'] - second['score'],
                        'accepted': accepted, 'seconds': time.perf_counter() - start})
        print(f'{i+1}/{len(rows)} {row["label"]} -> {top["category"]} accepted={accepted}', flush=True)
    classified = [r for r in results if r['label'] is not None]
    accepted = [r for r in results if r['accepted']]
    per_class = {}
    for c in CATEGORIES:
        tp = sum(r['label'] == c and r['top']['category'] == c for r in classified)
        fp = sum(r['label'] != c and r['top']['category'] == c for r in classified)
        fn = sum(r['label'] == c and r['top']['category'] != c for r in classified)
        per_class[c] = {'support': sum(r['label'] == c for r in classified),
                        'precision': tp / (tp + fp) if tp + fp else 0,
                        'recall': tp / (tp + fn) if tp + fn else 0,
                        'f1': 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0}
    report = {'warning': 'Agent-authored synthetic smoke samples; not real-user or independently human-labeled evaluation.',
              'model': MODEL_ID, 'revision': MODEL_REVISION, 'split': args.split,
              'input_type': args.input_type,
              'template': config['CLASSIFICATION_TEMPLATE'],
              'thresholds': {k: config[k] for k in config if k.startswith('CLASSIFICATION_MIN_')},
              'environment': {'python': platform.python_version(), 'cpu': platform.processor(),
                              'threads': config['CLASSIFICATION_THREADS'], 'ram_gb': psutil.virtual_memory().total / 2**30},
              'load_seconds': cold, 'rss_mb': psutil.Process().memory_info().rss / 2**20,
              'median_seconds': statistics.median(r['seconds'] for r in results),
              'p95_seconds': sorted(r['seconds'] for r in results)[max(0, int(len(results) * .95) - 1)],
              'top1_accuracy_classifiable': sum(r['label'] == r['top']['category'] for r in classified) / len(classified),
              'macro_f1_classifiable': statistics.mean(v['f1'] for v in per_class.values()),
              'recommendation_coverage_all': len(accepted) / len(results),
              'accepted_accuracy': sum(r['label'] == r['top']['category'] for r in accepted) / len(accepted) if accepted else None,
              'per_class': per_class, 'results': results}
    out = ROOT / 'docs' / (f'classification-evaluation-title-{args.split}.json' if args.input_type == 'title' else f'classification-evaluation-{args.split}.json')
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ['results', 'per_class']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
