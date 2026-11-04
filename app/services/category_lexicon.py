"""Deterministic retrieval, explicitly not machine learning."""
import json
import re
import unicodedata
from collections import defaultdict
from .category_policy import CATEGORIES, LEXICON_PATH, SINGLE_FRAGMENTS, BROAD_FRAGMENTS, NON_PRODUCT_INTENT


def normalize(text):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', text).lower())


def invalid_intent(title):
    text = normalize(title)
    return (any(word in text for word in NON_PRODUCT_INTENT)
            or bool(re.search(r'怎么(?:修|用|去|选|做|买|卖|操作)', text)))


class Lexicon:
    def __init__(self, path=LEXICON_PATH):
        self.entries = []
        self.surfaces = []
        ids, terms, surfaces, categories = set(), set(), {}, set()
        for file in sorted(path.glob('*.json')):
            data = json.loads(file.read_text(encoding='utf-8'))
            category = data['category']
            rows = data['entries']
            if category not in CATEGORIES or category == '其他' or category in categories or len(rows) != 100:
                raise ValueError('Invalid lexicon category/count')
            categories.add(category)
            for row in rows:
                key, term = row['id'], row['term']
                if not isinstance(key, str) or not key or key in ids or not isinstance(term, str) or not normalize(term):
                    raise ValueError('Invalid lexicon identifier/term')
                if normalize(term) in terms or not isinstance(row['aliases'], list):
                    raise ValueError('Duplicate term or malformed aliases')
                ids.add(key)
                terms.add(normalize(term))
                entry = {**row, 'category': category}
                self.entries.append(entry)
                for surface in [term] + row['aliases']:
                    if not isinstance(surface, str) or not normalize(surface):
                        raise ValueError('Empty/invalid alias')
                    value = normalize(surface)
                    if value in surfaces:
                        raise ValueError('Conflicting or duplicate alias: ' + value)
                    surfaces[value] = key
                    self.surfaces.append((value, entry, surface != term))
        if categories != set(CATEGORIES) - {'其他'} or len(self.entries) != 900:
            raise ValueError('Incomplete lexicon')
        self.surfaces.sort(key=lambda x: (-len(x[0]), x[1]['id']))
        self.fragment_index = defaultdict(list)
        for value, entry, alias in self.surfaces:
            for length in range(2, len(value) + 1):
                for start in range(len(value) - length + 1):
                    fragment = value[start:start + length]
                    if fragment not in BROAD_FRAGMENTS:
                        self.fragment_index[fragment].append((entry, alias))
            for fragment in SINGLE_FRAGMENTS:
                if fragment in value:
                    self.fragment_index[fragment].append((entry, alias))

    def match(self, title):
        text = normalize(title)
        if invalid_intent(text) or text in BROAD_FRAGMENTS:
            return []
        hits = []
        # Separators preserve separate products. Do not join unrelated characters.
        clauses = re.split(r'[，,、+＋/与和及\s;；]+', text)
        for clause in filter(None, clauses):
            full = []
            for surface, entry, alias in self.surfaces:
                if len(surface) == 1 and surface not in SINGLE_FRAGMENTS:
                    continue
                for match in re.finditer(re.escape(surface), clause):
                    full.append((match.start(), match.end(), entry, alias, surface))
            # A longer explicit product owns its span (e.g. basketball shoes, toy piano).
            full = [h for h in full if not any(
                k[0] <= h[0] and k[1] >= h[1] and k[1]-k[0] > h[1]-h[0] for k in full)]
            # Size modifiers are not independent products when another explicit item is present.
            if any(h[4] not in BROAD_FRAGMENTS for h in full):
                full = [h for h in full if h[4] not in BROAD_FRAGMENTS]
            if full:
                hits.extend(dict(category=e['category'], term=e['term'], id=e['id'],
                                 kind='alias' if alias else 'full', tier=3,
                                 length=end-start, fragment=surface)
                            for start, end, e, alias, surface in full)
                continue
            core = re.sub(r'^(?:出|出售|转让|闲置|二手|全新|毕业出|便宜出|一个|一套)+', '', clause)
            core = re.sub(r'(?:便宜出|低价出|转让|出售|出|一套|一个)$', '', core)
            if not core or core in BROAD_FRAGMENTS:
                continue
            fragments = []
            for length in range(len(core), 1, -1):
                for start in range(len(core)-length+1):
                    fragment = core[start:start+length]
                    if length / len(core) >= .5 and fragment in self.fragment_index:
                        fragments.append(fragment)
                if fragments:
                    break
            if core in SINGLE_FRAGMENTS:
                fragments = [core]
            for fragment in fragments:
                for entry, alias in self.fragment_index[fragment]:
                    hits.append(dict(category=entry['category'], term=entry['term'], id=entry['id'],
                                     kind='single' if len(fragment) == 1 else 'fragment',
                                     tier=1 if len(fragment) == 1 else 2, length=len(fragment), fragment=fragment))
        grouped = defaultdict(list)
        for hit in hits:
            grouped[hit['category']].append(hit)
        result = []
        for category, matches in grouped.items():
            matches.sort(key=lambda h: (-h['tier'], -h['length'], len(h['term']), h['id']))
            best = matches[0]
            evidence = list(dict.fromkeys(h['term'] for h in matches))[:2]
            result.append({**best, 'evidence': evidence})
        return sorted(result, key=lambda h: (-h['tier'], -h['length'], h['category']))

    @staticmethod
    def strong(matches):
        # Only explicit multi-character matches survive a model failure.
        return [h for h in matches if h['tier'] == 3 and h['length'] >= 2]

