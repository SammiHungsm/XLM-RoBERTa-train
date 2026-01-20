import re
from collections import defaultdict

class PIIProcessor:
    # =========================================================================
    # 🔧 1. Configuration & Rules (配置中心 - 業務邏輯集中管理)
    # =========================================================================
    
    # 信心門檻與窗口大小 (Magic Numbers)
    DEFAULT_CONFIDENCE = 0.30
    CONTEXT_WINDOW_SIZE = 20

    # 允許擴張邊界的標籤
    EXPANDABLE_LABELS = {"ID", "ACCOUNT", "PHONE", "LICENSE_PLATE"}
    
    # 基建後綴規則 (通用語言庫)
    INFRA_SUFFIXES = [
        "高鐵", "鐵路", "大橋", "隧道", "幹線", "公路", "通道", "線", "站",
        "High Speed Rail", "Bridge", "Tunnel", "Line", "Station", "Rail"
    ]
    
    # 年齡關鍵詞
    AGE_KEYWORDS = {'歲', 'years', 'yrs', 'age', 'old', '今年', '年紀', 'at'}

    # 粵語規則配置
    CANTONESE_PARTICLES = {'黎', '嚟', '巨', '咗', '度'}
    CANTONESE_VERBS = {'過', '打', '返', '嚟', '去', '左'} # 觸發粒詞檢查的前置動詞

    # 合併策略配置：定義不同實體允許的最大斷裂距離 (Token Gap)
    MERGE_GAP_TOLERANCE = {
        "ORG": 1, 
        "ADDRESS": 1, 
        "NAME": 1, 
        "PHONE": 2, 
        "ACCOUNT": 2, 
        "ID": 1
    }

    # 優先級配置：解決重疊時誰贏 (數值越大越優先)
    # Regex 抓到的通常由此邏輯保護
    LABEL_PRIORITY = {
        "LICENSE_PLATE": 50, 
        "ID": 50, 
        "EMAIL": 50, 
        "PHONE": 40, 
        "NAME": 30, 
        "ORG": 20, 
        "ADDRESS": 20, 
        "ACCOUNT": 10
    }

    # Regex 規則庫
    REGEX_PATTERNS = {
        "ID": r'(?<![A-Za-z0-9])[A-Z]{1,2}\s?[0-9]{6}\(?[0-9A]\)?(?![A-Za-z0-9])',
        "LICENSE_PLATE": r'(?<!\bof\s)(?<!\bage\s)(?<!\bat\s)(?<![a-z])[A-Z]{2}\s?[0-9]{1,4}(?![0-9])',
        "EMAIL": r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        "PHONE": r'(?<!\d)(?:\+852\s?)?[23569]\d{3}\s?\d{4}(?!\d)',
        "ACCOUNT": r'(?<!\d)\d{3}[-\s]?\d{3,6}[-\s]?\d{3,}(?!\d)'
    }

    # =========================================================================
    # ⚙️ 2. Initialization & Helpers
    # =========================================================================

    def __init__(self, text, raw_entities):
        self.text = text
        self.entities = raw_entities
        self.url_ranges = self._get_url_ranges()

    def _get_url_ranges(self):
        url_pattern = r'https?://[^\s,]+'
        return [match.span() for match in re.finditer(url_pattern, self.text)]

    def _is_in_forbidden_range(self, start, end):
        for r_start, r_end in self.url_ranges:
            if max(start, r_start) < min(end, r_end):
                return True
        return False

    def _is_valid_char_for_expansion(self, char, label):
        # 輔助函數：檢查是否為 ASCII 字母或數字 (排除中文)
        def is_ascii_alnum(c):
            return c.isascii() and c.isalnum()

        if label == "ID": 
            # ID 只允許 ASCII 字母、數字和括號
            return is_ascii_alnum(char) or char in "()"
            
        if label == "LICENSE_PLATE": 
            # 車牌只允許 ASCII 字母、數字和空格
            return is_ascii_alnum(char) or char == " "
            
        if label in ["PHONE", "ACCOUNT"]: 
            return char.isdigit() or char in "-+ "
            
        return False

    # =========================================================================
    # 🚀 3. Core Logic (Logic is now pure, referencing Configs)
    # =========================================================================

    def filter_low_confidence(self, threshold=None):
        # Use config default if not provided
        if threshold is None:
            threshold = self.DEFAULT_CONFIDENCE
            
        valid = []
        for r in self.entities:
            r['score'] = float(r['score'])
            if r['score'] > threshold and not self._is_in_forbidden_range(r['start'], r['end']):
                valid.append(r)
        self.entities = valid

    def normalize_infrastructure_labels(self):
        """利用後綴規則 (Suffix Rule) 校正地點標籤"""
        if not self.entities: return
        
        self.entities.sort(key=lambda x: x['start'])
        is_infra_chain = [False] * len(self.entities)

        for i in range(len(self.entities) - 1, -1, -1):
            ent = self.entities[i]
            next_text = self.text[ent['end']:].lstrip()
            
            touches_suffix = False
            for suffix in self.INFRA_SUFFIXES:
                if next_text.startswith(suffix):
                    touches_suffix = True
                    break
            
            touches_next_infra = False
            if i < len(self.entities) - 1:
                next_ent = self.entities[i+1]
                # 檢查是否接觸下一個已確認的基建實體
                if next_ent['start'] - ent['end'] == 0 and is_infra_chain[i+1]:
                    touches_next_infra = True

            if touches_suffix or touches_next_infra:
                ent['entity_group'] = "ADDRESS"
                is_infra_chain[i] = True

    def merge_fragments(self):
        if not self.entities: return
        self.entities.sort(key=lambda x: x['start'])
        
        merged = []
        curr = self.entities[0]
        
        for next_ent in self.entities[1:]:
            # ✅ 從配置讀取 Gap Tolerance
            max_gap = self.MERGE_GAP_TOLERANCE.get(curr['entity_group'], 2)
            gap = next_ent['start'] - curr['end']
            
            if next_ent['entity_group'] == curr['entity_group'] and gap <= max_gap:
                curr['end'] = next_ent['end']
                curr['word'] = self.text[curr['start']:curr['end']]
                curr['score'] = max(float(curr['score']), float(next_ent['score']))
            else:
                merged.append(curr)
                curr = next_ent
        merged.append(curr)
        self.entities = merged

    def filter_cantonese_particles(self):
        """過濾粵語助詞 (Kill Rule)"""
        valid_entities = []
        for ent in self.entities:
            keep = True
            word = ent['word'].strip()
            
            if ent['entity_group'] == "NAME" and len(word) == 1 and word in self.CANTONESE_PARTICLES:
                prev_char_idx = ent['start'] - 1
                if prev_char_idx >= 0:
                    prev_char = self.text[prev_char_idx]
                    # ✅ 從配置讀取動詞表
                    if prev_char in self.CANTONESE_VERBS:
                        keep = False
            
            if keep:
                valid_entities.append(ent)
        self.entities = valid_entities

    def cut_infrastructure_suffix(self):
        processed = []
        for ent in self.entities:
            word = self.text[ent['start']:ent['end']]
            suffix_found = False
            for suffix in self.INFRA_SUFFIXES:
                if word.endswith(suffix):
                    suffix_len = len(suffix)
                    if len(word) > suffix_len:
                        ent['end'] -= suffix_len
                        ent['word'] = self.text[ent['start']:ent['end']]
                        ent['entity_group'] = "ADDRESS"
                        processed.append(ent)
                    suffix_found = True
                    break
            if not suffix_found:
                processed.append(ent)
        self.entities = processed

    def refine_address_age(self):
        valid_entities = []
        for ent in self.entities:
            keep_entity = True
            clean_word = ent['word'].strip()
            
            if clean_word.lower() in self.AGE_KEYWORDS:
                keep_entity = False
            elif re.match(r'^[,，\.\s。？！!?-]+$', ent['word']):
                keep_entity = False
            elif re.match(r'^\d+$', clean_word):
                keep_entity = False

            if keep_entity and ent['entity_group'] == "ADDRESS":
                current_word = self.text[ent['start']:ent['end']]
                next_text = self.text[ent['end']:].lstrip().lower()
                
                # ✅ 使用配置的窗口大小
                prev_start = max(0, ent['start'] - self.CONTEXT_WINDOW_SIZE)
                prev_text = self.text[prev_start:ent['start']].lower()
                
                is_age_context = False
                for kw in self.AGE_KEYWORDS:
                    if next_text.startswith(kw):
                        is_age_context = True
                        break
                if not is_age_context:
                    if "age" in prev_text or "今年" in prev_text or "歲" in prev_text:
                        is_age_context = True
                    if "of" in prev_text and "age" in prev_text:
                         is_age_context = True

                if is_age_context:
                    match = re.search(r'([,，\s]*\d+)$', current_word)
                    if match:
                        cut_len = len(match.group(1))
                        ent['end'] -= cut_len
                        ent['word'] = self.text[ent['start']:ent['end']]

            if ent['end'] <= ent['start'] or not ent['word'].strip():
                keep_entity = False
            
            if keep_entity:
                valid_entities.append(ent)
        self.entities = valid_entities

    def expand_boundaries(self):
        for ent in self.entities:
            label = ent['entity_group']
            if label not in self.EXPANDABLE_LABELS:
                continue
            new_start = ent['start']
            while new_start > 0:
                char = self.text[new_start - 1]
                if self._is_valid_char_for_expansion(char, label):
                    new_start -= 1
                else:
                    break
            new_end = ent['end']
            while new_end < len(self.text):
                char = self.text[new_end]
                if self._is_valid_char_for_expansion(char, label):
                    new_end += 1
                else:
                    break
            ent['start'] = new_start
            ent['end'] = new_end
            ent['word'] = self.text[new_start:new_end]

    def apply_regex_fallback(self):
        existing_ranges = [(e['start'], e['end']) for e in self.entities]
        new_entities = []
        for label, pattern in self.REGEX_PATTERNS.items():
            for match in re.finditer(pattern, self.text):
                start, end = match.span()
                if self._is_in_forbidden_range(start, end):
                    continue
                is_overlap = False
                for e_start, e_end in existing_ranges:
                    if max(start, e_start) < min(end, e_end):
                        is_overlap = True
                        break
                if not is_overlap:
                    new_entities.append({
                        "entity_group": label, "score": 1.0, 
                        "word": self.text[start:end], "start": start, "end": end
                    })
                    existing_ranges.append((start, end))
        self.entities.extend(new_entities)

    def resolve_overlaps(self):
        if not self.entities: return
        
        # ✅ 從配置讀取優先級
        self.entities.sort(key=lambda x: (
            self.LABEL_PRIORITY.get(x['entity_group'], 0), 
            x['end'] - x['start'], 
            x['score']
        ), reverse=True)
        
        final = []
        for ent in self.entities:
            is_overlapping = False
            for kept in final:
                if max(ent['start'], kept['start']) < min(ent['end'], kept['end']):
                    is_overlapping = True
                    break
            if not is_overlapping:
                final.append(ent)
        final.sort(key=lambda x: x['start'])
        self.entities = final

    def assign_numbered_tags(self):
        """
        Assigns consistent numbered tags.
        """
        type_counts = defaultdict(int)
        entity_value_map = {}

        for ent in self.entities:
            label = ent['entity_group']
            clean_word = ent['word'].strip().lower()
            key = (label, clean_word)

            if key not in entity_value_map:
                type_counts[label] += 1
                entity_value_map[key] = type_counts[label]
            
            ent['numbered_tag'] = f"{label}-{entity_value_map[key]}"

    # =========================================================================
    # 🚀 4. Execution Pipeline
    # =========================================================================
    
    def process(self):
        self.filter_low_confidence()
        self.normalize_infrastructure_labels()
        self.merge_fragments()
        
        # Kill Phase
        self.cut_infrastructure_suffix()
        self.refine_address_age()
        self.filter_cantonese_particles()
        
        # Fill Phase
        self.expand_boundaries()
        self.apply_regex_fallback()
        
        # Finalize
        self.resolve_overlaps()
        self.assign_numbered_tags()
        return self.entities

    def get_masked_text(self):
        masked = self.text
        for ent in sorted(self.entities, key=lambda x: x['start'], reverse=True):
            if ent['end'] <= ent['start']: continue
            original_word = self.text[ent['start']:ent['end']]
            prefix = " " if original_word.startswith(" ") else ""
            suffix = " " if original_word.endswith(" ") else ""
            tag = f"{prefix}[{ent['numbered_tag']}]{suffix}"
            masked = masked[:ent['start']] + tag + masked[ent['end']:]
        return masked