"""Offline NLI inference. No database access; model is loaded only on first use."""
import logging
import threading
import time
from pathlib import Path

MODEL_ID = 'MoritzLaurer/mDeBERTa-v3-base-mnli-xnli'
MODEL_REVISION = '8adb042d524ecd5c26d3e3ba0e3fbcf7e2d0864c'
CATEGORIES = {
    '电子产品': '电子产品，如手机、电脑、耳机、相机及电子配件',
    '书籍': '书籍文具，如教材、小说、笔、本子和学习文具',
    '服装': '服装配饰，如衣服、鞋、帽、包和穿戴饰品',
    '家居用品': '生活家居用品，如床品、餐具、收纳、清洁用品和家具',
    '运动器材': '运动器材，如球拍、球、健身器材和户外运动装备',
    '乐器': '乐器，如吉他、钢琴、笛子和演奏配件',
    '工具': '工具，如螺丝刀、扳手、钳子和维修工具',
    '玩具': '玩具，如积木、玩偶、拼图和玩具模型',
    '艺术品': '艺术品，如绘画作品、雕塑、书法作品和艺术摆件',
    '其他': '其他实物商品，如植物、花种和不属于上述类别的闲置物品',
}
NLI_LABELS = ['电子数码设备', '书籍或学习文具', '衣服或穿戴配饰', '家居生活日用品',
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

    def _load(self):
        if self.model is not None:
            return
        if time.monotonic() < self.retry_after:
            raise ClassificationUnavailable()
        started = time.perf_counter()
        try:
            import torch
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            path = Path(self.config['CLASSIFICATION_MODEL_PATH'])
            if not (path / 'model.safetensors').is_file():
                raise FileNotFoundError('Prepare local model first')
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

    def rank(self, text):
        import torch
        self._load()
        descriptions = NLI_LABELS + REJECT_LABELS
        hypotheses = [self.config['CLASSIFICATION_TEMPLATE'].format(label=x) for x in descriptions]
        inputs = self.tokenizer([text] * len(hypotheses), hypotheses, padding=True,
                                truncation='only_first', max_length=256, return_tensors='pt')
        with torch.inference_mode():
            logits = self.model(**inputs).logits
            relative = logits[:, self.entailment].softmax(dim=0).tolist()
            support = logits[:, [self.contradiction, self.entailment]].softmax(dim=1)[:, 1].tolist()
        return sorted([
            {'category': key, 'score': relative[i], 'support': support[i]}
            for i, key in enumerate(list(CATEGORIES) + [None] * len(REJECT_LABELS))
        ], key=lambda x: x['score'], reverse=True)

    def recommend(self, text):
        if not self.config['CLASSIFICATION_ENABLED']:
            raise ClassificationUnavailable()
        if not self.lock.acquire(blocking=False):
            raise ClassificationBusy()
        started = time.perf_counter()
        try:
            ranking = self.rank(text)
            top, second = ranking[:2]
            accepted = (top['category'] is not None
                        and top['score'] >= self.config['CLASSIFICATION_MIN_SCORE']
                        and top['support'] >= self.config['CLASSIFICATION_MIN_SUPPORT']
                        and top['score'] - second['score'] >= self.config['CLASSIFICATION_MIN_MARGIN'])
            return {'status': 'suggested' if accepted else 'uncertain',
                    'category': top['category'] if accepted else None,
                    'message': '请确认是否使用此分类' if accepted else '信息不足或分类不明确，请手动选择'}
        except (ClassificationBusy, ClassificationUnavailable):
            raise
        except Exception as exc:
            logging.getLogger(__name__).warning('Classification inference failed (%s)', type(exc).__name__)
            raise ClassificationUnavailable() from exc
        finally:
            self.lock.release()
            logging.getLogger(__name__).info('Classification request %.3fs', time.perf_counter() - started)
