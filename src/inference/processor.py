import re
from collections import defaultdict

class PIIProcessor:
    # ===========================
    # 🔧 Configuration & Constants
    # ===========================
    EXPANDABLE_LABELS = {"ID", "ACCOUNT", "PHONE", "LICENSE_PLATE"}
    
    INFRA_SUFFIXES = [
        "高鐵", "鐵路", "大橋", "隧道", "幹線", "公路", "通道", "線", "站",
        "High Speed Rail", "Bridge", "Tunnel", "Line", "Station", "Rail"
    ]
    
    # 🔥 關鍵詞擴充：加入 "今年", "年紀" 等
    AGE_KEYWORDS = {'歲', 'years', 'yrs', 'age', 'old', '今年', '年紀', 'at'}

    # Regex 安全網
    REGEX_PATTERNS = {
        "ID": r'(?<![A-Za-z0-9])[A-Z]{1,2}\s?[0-9]{6}\(?[0-9A]\)?(?![A-Za-z0-9])',
        "LICENSE_PLATE": r'(?<!\bof\s)(?<!\bage\s)(?<!\bat\s)(?<![a-z])[A-Z]{2}\s?[0-9]{1,4}(?![0-9])',
        "EMAIL": r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        "PHONE": r'(?<!\d)(?:\+852\s?)?[23569]\d{3}\s?\d{4}(?!\d)',
        "ACCOUNT": r'(?<!\d)\d{3}[-\s]?\d{3,6}[-\s]?\d{3,}(?!\d)'
    }

    def __init__(self, text, raw_entities):
        """
        Initialize with text and AI-predicted entities.
        """
        self.text = text
        self.entities = raw_entities
        self.url_ranges = self._get_url_ranges()

    # ===========================
    # 🛠️ Helper Methods (Internal)
    # ===========================
    def _get_url_ranges(self):
        url_pattern = r'https?://[^\s,]+'
        return [match.span() for match in re.finditer(url_pattern, self.text)]

    def _is_in_forbidden_range(self, start, end):
        for r_start, r_end in self.url_ranges:
            if max(start, r_start) < min(end, r_end):
                return True
        return False

    def _is_valid_char_for_expansion(self, char, label):
        if label == "ID": return char.isalnum() or char in "()"
        if label == "LICENSE_PLATE": return char.isalnum() or char == " "
        if label in ["PHONE", "ACCOUNT"]: return char.isdigit() or char in "-+ "
        return False

    # ===========================
    # ⚙️ Processing Steps
    # ===========================

    def filter_low_confidence(self, threshold=0.30):
        valid = []
        for r in self.entities:
            r['score'] = float(r['score'])
            if r['score'] > threshold and not self._is_in_forbidden_range(r['start'], r['end']):
                valid.append(r)
        self.entities = valid

    def merge_fragments(self):
        if not self.entities: return
        self.entities.sort(key=lambda x: x['start'])
        configs = {"ORG": 1, "ADDRESS": 1, "NAME": 1, "PHONE": 2, "ACCOUNT": 2, "ID": 1}
        
        merged = []
        curr = self.entities[0]
        for next_ent in self.entities[1:]:
            max_gap = configs.get(curr['entity_group'], 2)
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

    def expand_boundaries(self):
        for ent in self.entities:
            label = ent['entity_group']
            if label not in self.EXPANDABLE_LABELS:
                continue

            # Left expansion
            new_start = ent['start']
            while new_start > 0:
                char = self.text[new_start - 1]
                if self._is_valid_char_for_expansion(char, label):
                    new_start -= 1
                else:
                    break
            
            # Right expansion
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
                        "entity_group": label, 
                        "score": 1.0, 
                        "word": self.text[start:end], 
                        "start": start, 
                        "end": end
                    })
                    existing_ranges.append((start, end))
        
        self.entities.extend(new_entities)

    def resolve_overlaps(self):
        if not self.entities: return
        label_priority = {
            "LICENSE_PLATE": 5, "ID": 5, "EMAIL": 5, "PHONE": 4, 
            "NAME": 3, "ORG": 2, "ADDRESS": 2, "ACCOUNT": 1
        }
        
        self.entities.sort(key=lambda x: (
            label_priority.get(x['entity_group'], 0), 
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
        """步驟 7: 年齡修復 (雙向檢查 + 強力過濾)"""
        valid_entities = []
        for ent in self.entities:
            keep_entity = True
            
            # 取得實體文字 (去除前後空白)
            clean_word = ent['word'].strip()
            
            # =========================================
            # 🛡️ 強力過濾器 (The Ghost Buster)
            # =========================================
            
            # 1. 如果實體只包含標點符號 (例如 ".", ",", "。") -> 殺掉！
            # 這是解決 [ADDRESS-3] 變成句號的關鍵
            if re.match(r'^[,，\.\s。？！!?-]+$', ent['word']):
                keep_entity = False

            # 2. 如果實體是純數字 (例如 "82", "31") -> 殺掉！
            elif re.match(r'^\d+$', clean_word):
                keep_entity = False
                
            # 3. 如果實體本身就是年齡關鍵字 (如 "歲") -> 殺掉！
            elif clean_word.lower() in self.AGE_KEYWORDS:
                keep_entity = False

            # =========================================
            # 🧠 上下文修復邏輯
            # =========================================
            if keep_entity and ent['entity_group'] == "ADDRESS":
                current_word = self.text[ent['start']:ent['end']]
                
                # 上下文檢查
                next_text = self.text[ent['end']:].lstrip().lower()
                prev_start = max(0, ent['start'] - 20)
                prev_text = self.text[prev_start:ent['start']].lower()
                
                is_age_context = False
                
                # 向後看: "82 years old"
                for kw in self.AGE_KEYWORDS:
                    if next_text.startswith(kw):
                        is_age_context = True
                        break
                
                # 向前看: "At the age of", "今年"
                if not is_age_context:
                    if "age" in prev_text or "今年" in prev_text or "歲" in prev_text:
                        is_age_context = True
                    if "of" in prev_text and "age" in prev_text:
                         is_age_context = True

                if is_age_context:
                    # 如果是地址結尾帶數字 (例如 "萬宜大廈 12 樓") -> 切尾
                    match = re.search(r'([,，\s]*\d+)$', current_word)
                    if match:
                        cut_len = len(match.group(1))
                        ent['end'] -= cut_len
                        ent['word'] = self.text[ent['start']:ent['end']]

            # 🔥 最終檢查：切完後如果變成空，或者只剩標點 -> 殺掉！
            if ent['end'] <= ent['start'] or not ent['word'].strip():
                keep_entity = False
            elif re.match(r'^[,，\.\s]+$', ent['word']): # 防止切完數字剩下逗號
                keep_entity = False

            if keep_entity:
                valid_entities.append(ent)
                
        self.entities = valid_entities
                
    def assign_numbered_tags(self):
        type_counts = defaultdict(int)
        for ent in self.entities:
            label = ent['entity_group']
            type_counts[label] += 1
            ent['numbered_tag'] = f"{label}-{type_counts[label]}"

    # ===========================
    # 🚀 Main Execution & Output
    # ===========================
    
    def process(self):
        """Run the full cleaning pipeline"""
        self.filter_low_confidence()
        self.merge_fragments()
        self.expand_boundaries()
        self.apply_regex_fallback()
        self.resolve_overlaps()
        self.cut_infrastructure_suffix()
        self.refine_address_age()
        self.assign_numbered_tags()
        return self.entities

    def get_masked_text(self):
        """Generate the masked string"""
        masked = self.text
        # Sort reverse to avoid index shifting
        for ent in sorted(self.entities, key=lambda x: x['start'], reverse=True):
            # 雙重保險：如果實體已經被切空了，就跳過
            if ent['end'] <= ent['start']:
                continue
                
            original_word = self.text[ent['start']:ent['end']]
            prefix = " " if original_word.startswith(" ") else ""
            suffix = " " if original_word.endswith(" ") else ""
            
            tag = f"{prefix}[{ent['numbered_tag']}]{suffix}"
            masked = masked[:ent['start']] + tag + masked[ent['end']:]
        return masked