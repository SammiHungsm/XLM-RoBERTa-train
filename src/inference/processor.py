import re
from collections import defaultdict

class PIIProcessor:
    # =========================================================================
    # 🔧 1. Configuration (No Business Rules)
    # =========================================================================
    
    DEFAULT_CONFIDENCE = 0.40
    
    # Regex 僅用於定義「格式固定」的 PII (ID/Phone/Email)，這不屬於業務 Hardcode，而是格式標準。
    # 如果你連這個都不想要，可以清空，但建議保留以作保底。
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
        # 排除 URL 範圍，避免誤抓網址內的代碼
        url_pattern = r'https?://[^\s,]+'
        return [match.span() for match in re.finditer(url_pattern, self.text)]

    def _is_in_forbidden_range(self, start, end):
        for r_start, r_end in self.url_ranges:
            if max(start, r_start) < min(end, r_end):
                return True
        return False

    # =========================================================================
    # 🚀 3. Core Logic (Logic Driven, Not Rule Driven)
    # =========================================================================
        
    def filter_low_confidence(self, threshold=None): 
        if threshold is None: threshold = self.DEFAULT_CONFIDENCE
        valid = []
        for r in self.entities:
            r['score'] = float(r['score'])
            if r['score'] > threshold and not self._is_in_forbidden_range(r['start'], r['end']):
                valid.append(r)
        self.entities = valid

    def merge_fragments(self):
        """
        [Logic] 只合併緊密相連的實體。
        使用標點符號 (Punctuation) 作為通用邊界，這適用於任何語言。
        """
        if not self.entities: return
        self.entities.sort(key=lambda x: x['start'])
        
        merged = []
        curr = self.entities[0]
        
        for next_ent in self.entities[1:]:
            gap_text = self.text[curr['end']:next_ent['start']]
            
            # 通用邏輯：標點符號是天然邊界
            has_punctuation = any(c in "，。、,.;?!（）()" for c in gap_text)
            
            # 只有同類別 + 無標點 + 距離極短 (<=1 space) 才合併
            if (next_ent['entity_group'] == curr['entity_group'] and 
                not has_punctuation and 
                len(gap_text.strip()) == 0): 
                
                curr['end'] = next_ent['end']
                curr['word'] = self.text[curr['start']:curr['end']]
                curr['score'] = max(curr['score'], next_ent['score'])
            else:
                merged.append(curr)
                curr = next_ent
        merged.append(curr)
        self.entities = merged

    def recover_brackets(self):
        """
        [Syntactic Logic] 括號成對修復。
        這是基於語法的邏輯，不涉及業務內容。
        """
        for ent in self.entities:
            word = ent['word']
            # 檢測左括號
            if word.startswith('(') or word.startswith('（'):
                # 檢測是否缺右括號
                if not (word.endswith(')') or word.endswith('）')):
                    # 向後探測 1 個字符
                    if ent['end'] < len(self.text):
                        next_char = self.text[ent['end']]
                        if next_char in [')', '）']:
                            ent['end'] += 1
                            ent['word'] = self.text[ent['start']:ent['end']]

    def apply_regex_fallback(self):
        """
        [Safety Net] 使用 Regex 補足模型漏掉的格式化實體。
        """
        existing_ranges = [(e['start'], e['end']) for e in self.entities]
        new_entities = []
        for label, pattern in self.REGEX_PATTERNS.items():
            for match in re.finditer(pattern, self.text):
                start, end = match.span()
                if self._is_in_forbidden_range(start, end): continue
                
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

    def assign_numbered_tags(self):
        """
        [Entity Resolution] 指代消解
        將「陳先生」關聯到「陳永安」，這是不依賴關鍵字的純邏輯。
        """
        type_counts = defaultdict(int)
        entity_map = {}
        
        # 1. 按長度排序：優先處理全名 (e.g., "陳永安")，再處理簡稱 (e.g., "陳")
        sorted_entities = sorted(self.entities, key=lambda x: len(x['word']), reverse=True)
        
        for ent in sorted_entities:
            label = ent['entity_group']
            # 移除空格以確保中文匹配準確 (e.g. "陳 " vs "陳")
            clean_word = ent['word'].replace(" ", "").strip()
            if not clean_word: clean_word = ent['word'].strip()
            
            matched_key = None
            if label == "NAME":
                for (m_label, m_word), tag_id in entity_map.items():
                    # 邏輯：如果當前名字是已知名字的子集 (e.g. "陳" in "陳永安")
                    if m_label == "NAME" and (clean_word in m_word or m_word in clean_word):
                        matched_key = (m_label, m_word)
                        break
            
            key = (label, clean_word.lower()) # 英文用 lower，中文無影響
            
            if matched_key:
                ent['numbered_tag'] = f"{label}-{entity_map[matched_key]}"
            elif key not in entity_map:
                type_counts[label] += 1
                entity_map[key] = type_counts[label]
                ent['numbered_tag'] = f"{label}-{type_counts[label]}"
            else:
                ent['numbered_tag'] = f"{label}-{entity_map[key]}"

    def process(self):
        # 1. 基礎過濾
        self.filter_low_confidence()
        
        # 2. 保底填充 (Regex)
        self.apply_regex_fallback()
        
        # 3. 邏輯合併
        self.merge_fragments()
        
        # 4. 語法修復
        self.recover_brackets()
        
        # 5. 標籤與消解
        self.assign_numbered_tags()
        
        return self.entities

    def get_masked_text(self):
        masked = self.text
        for ent in sorted(self.entities, key=lambda x: x['start'], reverse=True):
            tag = f"[{ent['numbered_tag']}]"
            masked = masked[:ent['start']] + tag + masked[ent['end']:]
        return masked