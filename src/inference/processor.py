import re
from collections import defaultdict

class PIIProcessor:
    # ===========================
    # 🔧 Configuration & Constants
    # ===========================
    EXPANDABLE_LABELS = {"ID", "ACCOUNT", "PHONE", "LICENSE_PLATE"}
    
    # Generic suffix rules (Language-based, not entity-specific)
    INFRA_SUFFIXES = [
        "高鐵", "鐵路", "大橋", "隧道", "幹線", "公路", "通道", "線", "站",
        "High Speed Rail", "Bridge", "Tunnel", "Line", "Station", "Rail"
    ]
    
    AGE_KEYWORDS = {'歲', 'years', 'yrs', 'age', 'old', '今年', '年紀', 'at'}

    # Cantonese particle filter list
    CANTONESE_PARTICLES = {'黎', '嚟', '巨', '咗', '度'}

    REGEX_PATTERNS = {
        "ID": r'(?<![A-Za-z0-9])[A-Z]{1,2}\s?[0-9]{6}\(?[0-9A]\)?(?![A-Za-z0-9])',
        "LICENSE_PLATE": r'(?<!\bof\s)(?<!\bage\s)(?<!\bat\s)(?<![a-z])[A-Z]{2}\s?[0-9]{1,4}(?![0-9])',
        "EMAIL": r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        "PHONE": r'(?<!\d)(?:\+852\s?)?[23569]\d{3}\s?\d{4}(?!\d)',
        "ACCOUNT": r'(?<!\d)\d{3}[-\s]?\d{3,6}[-\s]?\d{3,}(?!\d)'
    }

    # 🗑️ Removed OVERRIDE_TYPES to avoid hardcoding. Trust the model.

    def __init__(self, text, raw_entities):
        self.text = text
        self.entities = raw_entities
        self.url_ranges = self._get_url_ranges()

    # ===========================
    # 🛠️ Internal Helpers
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

    def normalize_infrastructure_labels(self):
        """
        Normalize labels based on infrastructure suffixes.
        E.g., if an entity is followed by "Rail", it's likely an ADDRESS.
        """
        if not self.entities: return
        
        self.entities.sort(key=lambda x: x['start'])
        is_infra_chain = [False] * len(self.entities)

        # Scan backwards
        for i in range(len(self.entities) - 1, -1, -1):
            ent = self.entities[i]
            next_text = self.text[ent['end']:].lstrip()
            
            # A. Check if touching a suffix
            touches_suffix = False
            for suffix in self.INFRA_SUFFIXES:
                if next_text.startswith(suffix):
                    touches_suffix = True
                    break
            
            # B. Check if touching a verified infrastructure entity
            touches_next_infra = False
            if i < len(self.entities) - 1:
                next_ent = self.entities[i+1]
                if next_ent['start'] - ent['end'] == 0 and is_infra_chain[i+1]:
                    touches_next_infra = True

            # Decision: Force to ADDRESS if part of infra chain
            if touches_suffix or touches_next_infra:
                ent['entity_group'] = "ADDRESS"
                is_infra_chain[i] = True

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

    def filter_cantonese_particles(self):
        """Filter out common Cantonese particles mistaken for Names"""
        valid_entities = []
        for ent in self.entities:
            keep = True
            word = ent['word'].strip()
            
            # If single char NAME and is a particle
            if ent['entity_group'] == "NAME" and len(word) == 1 and word in self.CANTONESE_PARTICLES:
                # Check preceding character
                prev_char_idx = ent['start'] - 1
                if prev_char_idx >= 0:
                    prev_char = self.text[prev_char_idx]
                    # Common verb endings in Cantonese
                    if prev_char in {'過', '打', '返', '嚟', '去', '左'}:
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
            
            # Aggressive Filtering: Pure numbers, punctuation, keywords
            if clean_word.lower() in self.AGE_KEYWORDS:
                keep_entity = False
            elif re.match(r'^[,，\.\s。？！!?-]+$', ent['word']):
                keep_entity = False
            elif re.match(r'^\d+$', clean_word):
                keep_entity = False

            if keep_entity and ent['entity_group'] == "ADDRESS":
                current_word = self.text[ent['start']:ent['end']]
                next_text = self.text[ent['end']:].lstrip().lower()
                prev_start = max(0, ent['start'] - 20)
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
        label_priority = {
            "LICENSE_PLATE": 5, "ID": 5, "EMAIL": 5, "PHONE": 4, 
            "NAME": 3, "ORG": 2, "ADDRESS": 2, "ACCOUNT": 1
        }
        self.entities.sort(key=lambda x: (
            label_priority.get(x['entity_group'], 0), 
            x['end'] - x['start'], x['score']
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
        Example: First "Google" -> ORG-1. Second "Google" -> ORG-1. "Apple" -> ORG-2.
        """
        type_counts = defaultdict(int)
        entity_value_map = {} # Map content to tag number

        for ent in self.entities:
            label = ent['entity_group']
            # Normalize text to ignore case/spacing differences
            clean_word = ent['word'].strip().lower()
            key = (label, clean_word)

            if key not in entity_value_map:
                type_counts[label] += 1
                entity_value_map[key] = type_counts[label]
            
            ent['numbered_tag'] = f"{label}-{entity_value_map[key]}"

    # ===========================
    # 🚀 Main Execution Pipeline
    # ===========================
    
    def process(self):
        # 1. Basic Cleaning
        self.filter_low_confidence()
        # Infrastructure normalization (Suffix Rule) - NO HARDCODING
        self.normalize_infrastructure_labels()
        self.merge_fragments()
        
        # 2. 🔥 Kill First: Remove invalid entities
        # Remove "黎" in "打過黎"
        # Remove pure numbers mistakenly labeled as ADDRESS (so Regex can catch them later)
        self.cut_infrastructure_suffix()
        self.refine_address_age()
        self.filter_cantonese_particles()
        
        # 3. 🔥 Fill Later: Regex + Expansion
        # Expand remaining valid entities
        self.expand_boundaries()
        # Catch any phone/account numbers that were cleared in step 2
        self.apply_regex_fallback()
        
        # 4. Finalize
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