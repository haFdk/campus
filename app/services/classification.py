"""Offline NLI inference. No database access; model is loaded only on first use."""
import logging
import threading
import time
from pathlib import Path

MODEL_ID = 'MoritzLaurer/mDeBERTa-v3-base-mnli-xnli'
MODEL_REVISION = '8adb042d524ecd5c26d3e3ba0e3fbcf7e2d0864c'
from .category_policy import CATEGORIES, VERSION, BROAD_FRAGMENTS
from .category_lexicon import Lexicon, invalid_intent, normalize
NLI_LABELS = ['电子数码设备', '书籍和纸质学习资料', '衣服或穿戴配饰', '家居生活日用品',
              '体育运动器材', '用于演奏音乐的乐器', '用于维修的工具', '用于玩耍的玩具',
              '供人欣赏的艺术作品', '植物或其他杂物']
REJECT_LABELS = ['天气情况', '寻求他人帮助或服务', '招聘兼职工作', '日常闲聊', '信息不明确的东西']


class ClassificationUnavailable(Exception):
    pass


class ClassificationBusy(Exception):
    pass


class Classifier:
    def __init__(self, config):
        self.config = config
        self.lock = threading.Lock()
        self.model = self.tokenizer = None
        self.retry_after = 0
        self.load_seconds = None
        self.lexicon = None
        self.lexicon_lock = threading.Lock()
        self.hypothesis_cache = {}

    def _load(self):
        if self.model is not None:
            return
        if time.monotonic() < self.retry_after:
            raise ClassificationUnavailable()
        started = time.perf_counter()
        try:
            path = Path(self.config['CLASSIFICATION_MODEL_PATH'])
            if not (path / 'model.safetensors').is_file():
                raise FileNotFoundError('Prepare local model first')
            import torch
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            torch.set_num_threads(self.config['CLASSIFICATION_THREADS'])
            tokenizer = AutoTokenizer.from_pretrained(str(path), local_files_only=True, trust_remote_code=False)
            model = AutoModelForSequenceClassification.from_pretrained(
                str(path), local_files_only=True, trust_remote_code=False, use_safetensors=True,
            ).eval()
            labels = {str(v).lower(): int(k) for k, v in model.config.id2label.items()}
            if 'entailment' not in labels or 'contradiction' not in labels:
                raise ValueError('Unexpected NLI label mapping')
            self.entailment = labels['entailment']
            self.contradiction = labels['contradiction']
            self.tokenizer, self.model = tokenizer, model
            self.load_seconds = time.perf_counter() - started
        except Exception as exc:
            self.retry_after = time.monotonic() + 30
            logging.getLogger(__name__).warning('Classification load failed (%s)', type(exc).__name__)
            raise ClassificationUnavailable() from exc

    def _get_lexicon(self):
        if self.lexicon is None:
            try:
                self.lexicon = Lexicon()
            except Exception as exc:
                logging.getLogger(__name__).warning('Lexicon load failed (%s)', type(exc).__name__)
                raise ClassificationUnavailable() from exc
        return self.lexicon

    @staticmethod
    def _response(candidates, source='none', degraded=False):
        # Legacy category is populated only for an unambiguous single suggestion.
        return {'status': 'suggested' if candidates else 'uncertain',
                'category': candidates[0]['category'] if len(candidates) == 1 else None,
                'candidates': candidates, 'source': source, 'degraded': degraded,
                'version': VERSION,
                'message': ('当前为词库匹配建议，请核对后选择分类' if degraded else '请选择符合实际商品的分类')
                           if candidates else '信息不足或分类不明确，请补充商品名称或手动选择'}

    def _lexical_fallback(self, matches, error):
        strong = Lexicon.strong(matches)
        if 0 < len(strong) <= 3:
            return self._response([self._candidate(h, 'lexicon') for h in strong], 'lexicon', True)
        raise error

    @staticmethod
    def _candidate(hit, source):
        return {'category': hit['category'], 'source': source,
                'evidence': hit.get('evidence', []),
                'reason': '匹配词：' + '、'.join(hit['evidence']) if hit.get('evidence') else '根据标题语义推荐'}

    def _score(self, text, descriptions):
        """Independent entailment/contradiction support plus legacy relative score."""
        self._load()
        import torch
        hypotheses = tuple(self.config['CLASSIFICATION_TEMPLATE'].format(label=x) for x in descriptions)
        # Cache fixed/recurring hypotheses, never user titles.
        if hypotheses not in self.hypothesis_cache:
            if len(self.hypothesis_cache) >= 128:
                self.hypothesis_cache.pop(next(iter(self.hypothesis_cache)))
            self.hypothesis_cache[hypotheses] = self.tokenizer(list(hypotheses), add_special_tokens=False)['input_ids']
        second = self.hypothesis_cache[hypotheses]
        first = self.tokenizer(text, add_special_tokens=False)['input_ids']
        batch_size = int(self.config.get('CLASSIFICATION_BATCH_SIZE', 8))
        if not 1 <= batch_size <= 32:
            raise ValueError('Invalid classification batch size')
        logits = []
        with torch.inference_mode():
            for start in range(0, len(second), batch_size):
                batch = [self.tokenizer.prepare_for_model(
                    first, ids, truncation='only_first', max_length=256, return_attention_mask=True,
                    return_token_type_ids=False) for ids in second[start:start+batch_size]]
                inputs = self.tokenizer.pad(batch, padding=True, return_tensors='pt')
                logits.append(self.model(**inputs).logits)
            values = torch.cat(logits)
            relative = values[:, self.entailment].softmax(dim=0).tolist()
            support = values[:, [self.contradiction, self.entailment]].softmax(dim=1)[:, 1].tolist()
        return [{'score': a, 'support': b} for a, b in zip(relative, support)]

    def rank(self, text):
        scores = self._score(text, NLI_LABELS + REJECT_LABELS)
        return sorted([{'category': category, **score} for category, score in
                       zip(list(CATEGORIES) + [None] * len(REJECT_LABELS), scores)],
                      key=lambda x: x['score'], reverse=True)

    def _hybrid(self, text, matches):
        if len(matches) > 6:
            return self._response([])
        # A single independent support score per business category, not per matched word.
        labels = [h['evidence'][0] for h in matches]
        scores = self._score(text, labels + REJECT_LABELS)
        # The generic "unclear thing" hypothesis is expected for short fragments;
        # it is not a veto when retrieval has concrete product evidence.
        intent_reject = max(s['score'] for s in scores[len(matches):-1])
        selected = []
        for hit, score in zip(matches, scores):
            minimum = float(self.config.get('CLASSIFICATION_HYBRID_MIN_SUPPORT', .55))
            if score['support'] >= minimum and not (intent_reject > .8 and score['score'] < .05):
                selected.append((hit, score))
        # Evidence tier first; model ranks within a tier. No uncalibrated score addition.
        selected.sort(key=lambda pair: (-pair[0]['tier'], -pair[1]['support'], -pair[0]['length']))
        if len(selected) > 3:
            # Only trim when the model actually separates third from fourth.
            if selected[2][0]['tier'] == selected[3][0]['tier'] and selected[2][1]['support'] - selected[3][1]['support'] < .15:
                return self._response([])
            selected = selected[:3]
        return self._response([self._candidate(hit, 'hybrid') for hit, _ in selected], 'hybrid')

    def recommend(self, text):
        if not self.config['CLASSIFICATION_ENABLED']:
            raise ClassificationUnavailable()
        if invalid_intent(text) or normalize(text) in BROAD_FRAGMENTS:
            return self._response([])
        # Lazy immutable lexicon initialization, independent of the inference lock.
        with self.lexicon_lock:
            matches = self._get_lexicon().match(text)
        if not self.lock.acquire(blocking=False):
            return self._lexical_fallback(matches, ClassificationBusy())
        started = time.perf_counter()
        try:
            if matches:
                return self._hybrid(text, matches)
            ranking = self.rank(text)
            top, second = ranking[:2]
            accepted = (top['category'] in CATEGORIES
                        and top['score'] >= self.config['CLASSIFICATION_MIN_SCORE']
                        and top['support'] >= self.config['CLASSIFICATION_MIN_SUPPORT']
                        and top['score'] - second['score'] >= self.config['CLASSIFICATION_MIN_MARGIN'])
            candidates = [self._candidate(top, 'model')] if accepted else []
            return self._response(candidates, 'model')
        except Exception as exc:
            logging.getLogger(__name__).warning('Classification inference unavailable (%s)', type(exc).__name__)
            return self._lexical_fallback(matches, ClassificationUnavailable())
        finally:
            self.lock.release()
            logging.getLogger(__name__).info('Classification request %.3fs', time.perf_counter() - started)

