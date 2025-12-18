import re
import json
from transformers import pipeline

class HK_PII_Tokenizer_Ultimate:
    def __init__(self, device=0):
        print("正在載入 XLM-RoBERTa (對中文/英文混合支援最佳)...")
        self.ner_pipeline = pipeline(
            "ner",
            model="Davlan/xlm-roberta-large-ner-hrl",
            tokenizer="Davlan/xlm-roberta-large-ner-hrl",
            aggregation_strategy="simple",
            device=device
        )
        print("模型載入完成。")

    def _expand_person_name(self, entities, text):
        """ [邏輯 1] 修復單字中文人名 ("陳" -> "陳大文") """
        chinese_char_pattern = r'[\u4e00-\u9fa5]'
        for entity in entities:
            if entity['type'] == 'Person' and len(entity['text']) == 1:
                if re.match(chinese_char_pattern, entity['text']):
                    current_end = entity['end']
                    next_chars = text[current_end:current_end+2]
                    extend_len = 0
                    for char in next_chars:
                        if re.match(chinese_char_pattern, char):
                            extend_len += 1
                        else:
                            break
                    if extend_len > 0:
                        new_end = current_end + extend_len
                        entity['text'] = text[entity['start']:new_end]
                        entity['end'] = new_end
        return entities

    def _vacuum_address_prefix(self, entities, text):
        """
        [邏輯 2] 地址前綴吸塵器 (The Vacuum Cleaner)
        當 AI 找到路名 (e.g., "Nathan Road") 時，
        這段 Regex 會「向左吸入」所有的座號、樓層、門牌。

        匹配模式：
        - 關鍵字: Block, Flat, Room, Tower, Phase...
        - 數字/混合: 123, 15/F, 10A
        - 分隔符: 逗號, 空格, 點
        """

        # 定義香港地址前綴關鍵字
        keywords = r"No\.|Flat|Rm|Room|Unit|Shop|Suite|Block|Blk|Tower|Phase|Level|Lvl|Floor|Flr|G\/F|Basement|Estate|Garden|Court|Mansion|Bldg|Building"

        # Regex 解釋：
        # 尋找位於字串結尾 ($) 的連續片段，片段需符合：
        # (關鍵字+編號) 或 (純數字/樓層) + (分隔符)
        prefix_pattern = r'((?:(?:' + keywords + r')[\s\.]*[A-Za-z0-9\-\/]*|[\d\-\/]+[A-Za-z]?)(?:[\s,.\-]+))+$'

        for entity in entities:
            if entity['type'] == 'Address':
                current_start = entity['start']
                # 截取實體前面的文字
                preceding_text = text[:current_start]

                # 向左執行 Regex
                match = re.search(prefix_pattern, preceding_text, re.IGNORECASE)

                if match:
                    prefix_str = match.group(1)
                    # print(f"吸入前綴: '{prefix_str}'") # Debug 用

                    # 更新實體起始位置
                    new_start = current_start - len(prefix_str)
                    entity['start'] = new_start
                    entity['text'] = prefix_str + entity['text']
        return entities

    def _merge_adjacent_entities(self, entities, text, threshold=10):
        """
        [邏輯 3] 碎片合併
        解決 "香港" + "中環" 斷開的問題。
        允許中間是空字串 (Gap=0) 或標點。
        """
        if not entities:
            return []

        entities.sort(key=lambda x: x['start'])
        merged = []
        current = entities[0]

        for next_ent in entities[1:]:
            gap_start = current['end']
            gap_end = next_ent['start']
            gap_text = text[gap_start:gap_end]

            # 關鍵：允許 Gap 為空 (中文特性) 或包含數字/符號
            is_gap_safe = bool(re.match(r'^[\s\d,.\-/()]*$', gap_text))

            if current['type'] == next_ent['type'] and (len(gap_text) <= threshold and is_gap_safe):
                new_end = next_ent['end']
                current['text'] = text[current['start']:new_end]
                current['end'] = new_end
                current['priority'] = max(current['priority'], next_ent['priority'])
            else:
                merged.append(current)
                current = next_ent

        merged.append(current)
        return merged

    def tokenize(self, text):
        candidates = []

        # --- 1. Regex (處理固定格式，優先級最高) ---
        # HKID
        for match in re.finditer(r'[A-Za-z]{1,2}\d{6}\(?[0-9A-Za-z]\)?', text):
            candidates.append({"start": match.start(), "end": match.end(), "type": "HKID", "text": match.group(), "priority": 10})
        # Phone (8位)
        for match in re.finditer(r'\b[23569]\d{7}\b', text):
            candidates.append({"start": match.start(), "end": match.end(), "type": "Phone", "text": match.group(), "priority": 10})
        # Bank Account
        for match in re.finditer(r'\b\d{9,16}\b', text):
            candidates.append({"start": match.start(), "end": match.end(), "type": "BankAccount", "text": match.group(), "priority": 10})

        # --- 2. AI NER (XLM-RoBERTa) ---
        ai_entities = self.ner_pipeline(text)
        target_labels = {"PER": "Person", "LOC": "Address", "ORG": "Org"}

        raw_ai_candidates = []
        for entity in ai_entities:
            if entity['entity_group'] in target_labels:
                # 稍微降低門檻以確保抓取率
                if entity['score'] > 0.30:
                    raw_ai_candidates.append({
                        "start": entity['start'],
                        "end": entity['end'],
                        "type": target_labels[entity['entity_group']],
                        "text": text[entity['start']:entity['end']],
                        "priority": 5
                    })

        # --- 3. 修復流水線 (Magic happens here) ---

        # A. 修復人名
        candidates_v1 = self._expand_person_name(raw_ai_candidates, text)

        # B. 向左吸入地址前綴 (Block A, 123)
        candidates_v2 = self._vacuum_address_prefix(candidates_v1, text)

        # C. 合併斷開的實體 (Flat B + Tower 2)
        candidates_v3 = self._merge_adjacent_entities(candidates_v2, text)

        candidates.extend(candidates_v3)

        # --- 4. 解決衝突 ---
        candidates.sort(key=lambda x: (-x['priority'], x['start']))
        final_entities = []
        occupied_mask = [False] * len(text)

        for cand in candidates:
            is_occupied = any(occupied_mask[i] for i in range(cand['start'], cand['end']))
            if not is_occupied:
                final_entities.append(cand)
                for i in range(cand['start'], cand['end']):
                    occupied_mask[i] = True

        # --- 5. 格式化輸出 ---
        final_entities.sort(key=lambda x: x['start'])
        mappings = {}
        counters = {"Person": 1, "Address": 1, "Org": 1, "Phone": 1, "HKID": 1, "BankAccount": 1}

        result_text = ""
        last_idx = 0

        for entity in final_entities:
            result_text += text[last_idx:entity['start']]
            etype = entity['type']
            count = counters.get(etype, 1)
            tag = f"[{etype}{count:02d}]"
            counters[etype] += 1
            mappings[tag] = entity['text']
            result_text += tag
            last_idx = entity['end']

        result_text += text[last_idx:]

        return {"Output": {"MaskedInput": result_text, "Mappings": mappings}}

    def process_request(self, text):
        return json.dumps(self.tokenize(text), ensure_ascii=False)

# --- 驗證 (針對你之前的失敗案例) ---
if __name__ == "__main__":
    tokenizer = HK_PII_Tokenizer_Ultimate(device=0) # 0 for GPU, -1 for CPU

    test_cases = [
        "請把貨送到 Block A, 123 Nathan Road.", # 之前 GLiNER 切碎了這個
        "陳大文先生住在香港中環皇后大道中100號。", # 之前 GLiNER 沒抓到
        "Address: Flat 5B, Tower 2, 88 Queensway.", # 複雜英文地址
        "我的恆生銀行戶口是 288123456789。"
    ]

    print("\n--- Ultimate XLM-R 執行結果 ---")
    for t in test_cases:
        print(f"\n原句: {t}")
        print(f"結果: {tokenizer.process_request(t)}")