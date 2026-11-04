import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app.config import Config
from app.services.category_policy import CATEGORIES
from app.services.category_lexicon import Lexicon
from app.services.classification import Classifier, ClassificationUnavailable


class LexiconTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lex = Lexicon()

    def categories(self, title):
        return [r['category'] for r in self.lex.match(title)]

    def test_counts_ids_and_frontend_mapping(self):
        self.assertEqual(len(self.lex.entries), 900)
        self.assertEqual(len(set(r['id'] for r in self.lex.entries)), 900)
        for category in set(CATEGORIES)-{'其他'}:
            self.assertEqual(sum(r['category']==category for r in self.lex.entries), 100)
        frontend = Path('frontend/src/constants/itemCategories.js').read_text(encoding='utf-8')
        for cat in CATEGORIES:
            self.assertIn("'" + cat + "'", frontend)

    def test_full_alias_fragment_and_single(self):
        self.assertEqual(self.categories('马赛克'), ['艺术品'])
        self.assertEqual(self.categories('闲置充电头'), ['电子产品'])
        self.assertEqual(set(self.categories('琴')), {'乐器', '玩具'})
        for title in ['机', '品', '器', '东西', '这是一个机遇']:
            self.assertEqual(self.categories(title), [])

    def test_specific_span_wins_and_evidence_deduplicates(self):
        for title, category in [('玩具琴', '玩具'), ('篮球鞋', '服装'),
                                ('手机拆机工具', '工具'), ('吉他音箱', '乐器'),
                                ('乐谱架', '乐器'), ('娃娃服装', '玩具')]:
            self.assertEqual(self.categories(title), [category])
        self.assertEqual(len(self.categories('鼠标和手机壳和键盘')), 1)
        self.assertEqual(set(self.categories('电钻和跑鞋')), {'工具','服装'})
        self.assertTrue(all(len(r['evidence'])<=2 for r in self.lex.match('琴')))

    def test_intent_not_product(self):
        for title in ['招聘吉他老师', '帮我修手机', '求购充电头', '马赛克怎么去掉', '这个台灯不卖']:
            self.assertEqual(self.categories(title), [])
        self.assertEqual(self.categories('没怎么穿的跑鞋'), ['服装'])
        self.assertEqual(self.categories('小号帆布包'), ['服装'])
        self.assertEqual(self.categories('大号收纳箱'), ['家居用品'])
        self.assertEqual(self.categories('古琴招生'), [])
        self.assertEqual(self.categories('钱包寻物启事'), [])

    def test_corrupt_dictionary_validation(self):
        source = Path('app/data/category_lexicon')
        for mutation in ['category','count','empty','id','alias','term']:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                for file in source.glob('*.json'):
                    data = json.loads(file.read_text(encoding='utf-8'))
                    if file.name == 'books.json':
                        if mutation=='category': data['category']='不存在'
                        if mutation=='count': data['entries'].pop()
                        if mutation=='empty': data['entries'][0]['term']=' '
                        if mutation=='id': data['entries'][0]['id']=data['entries'][1]['id']
                        if mutation=='alias': data['entries'][0]['aliases']=['手机']
                        if mutation=='term': data['entries'][0]['term']=data['entries'][1]['term']
                    Path(tmp,file.name).write_text(json.dumps(data),encoding='utf-8')
                with self.assertRaises(ValueError):
                    Lexicon(Path(tmp))


class HybridTests(unittest.TestCase):
    def setUp(self):
        self.service = Classifier({k:getattr(Config,k) for k in dir(Config) if k.isupper()})
        self.service.lexicon = Lexicon()

    def scores(self, n, support=.9):
        return [{'support':support,'score':.2} for _ in range(n)] + [{'support':.01,'score':.001} for _ in range(5)]

    def test_multiple_selection_contract_and_same_category_once(self):
        with patch.object(self.service, '_score', return_value=self.scores(2)):
            response=self.service.recommend('琴')
        self.assertEqual(len(response['candidates']), 2)
        self.assertIsNone(response['category'])
        self.assertEqual(response['status'], 'suggested')
        self.assertEqual(response['source'], 'hybrid')
        self.assertTrue(all(r['source']=='hybrid' and r['evidence'] for r in response['candidates']))

    def test_low_support_rejected(self):
        with patch.object(self.service, '_score', return_value=self.scores(1,.1)):
            response=self.service.recommend('马赛克')
        self.assertEqual(response['candidates'], [])

    def test_too_many_equivalent_candidates_not_arbitrarily_trimmed(self):
        with patch.object(self.service,'_score',return_value=self.scores(4)):
            response=self.service.recommend('篮球和手机和台灯和吉他')
        self.assertEqual(response['candidates'], [])

    def test_model_sorts_equal_evidence_tiers(self):
        scores=self.scores(2)
        scores[0]['support']=.6
        scores[1]['support']=.95
        hits=self.service.lexicon.match('琴')
        with patch.object(self.service,'_score',return_value=scores):
            response=self.service.recommend('琴')
        self.assertEqual(response['candidates'][0]['category'],hits[1]['category'])

    def test_no_match_semantic_fallback_and_other(self):
        with patch.object(self.service.lexicon,'match',return_value=[]), patch.object(self.service,'rank',return_value=[
            {'category':'其他','score':.95,'support':.99},
            {'category':'家居用品','score':.01,'support':.1}]):
            response=self.service.recommend('植物盆栽')
        self.assertEqual(response['source'],'model')
        self.assertEqual(response['category'],'其他')
        self.assertEqual(response['candidates'][0]['evidence'],[])

    def test_failure_returns_only_strong_lexical_candidates(self):
        with patch.object(self.service,'_score',side_effect=RuntimeError('failure')):
            response=self.service.recommend('充电头')
            self.assertEqual(response['source'],'lexicon')
            self.assertEqual(response['category'],'电子产品')
            with self.assertRaises(ClassificationUnavailable):
                self.service.recommend('琴')
        self.assertFalse(self.service.lock.locked())

    def test_disabled_and_broken_lexicon_do_not_load_model(self):
        self.service.config['CLASSIFICATION_ENABLED']=False
        with patch.object(self.service,'_load') as loader:
            with self.assertRaises(ClassificationUnavailable):
                self.service.recommend('手机')
            loader.assert_not_called()
        self.service.config['CLASSIFICATION_ENABLED']=True
        self.service.lexicon=None
        with patch('app.services.classification.Lexicon',side_effect=ValueError('invalid')):
            with self.assertRaises(ClassificationUnavailable):
                self.service.recommend('手机')

    def test_intent_is_checked_before_model_and_fallback(self):
        with patch.object(self.service,'_score') as score:
            self.assertEqual(self.service.recommend('帮我修手机')['status'],'uncertain')
            score.assert_not_called()

