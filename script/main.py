import os
import re
import json
import requests

from transformers import pipeline



# ==========================================
# 1. PII 脫敏核心類 (HK_PII_Tokenizer_Ultimate)
# ==========================================
class HK_PII_Tokenizer_Ultimate:
    def __init__(self, device=-1):
        print("--- [Step 1] 初始化本地脫敏模型 (XLM-RoBERTa) ---")
        #強制使用 use_fast=False 避開 Windows 環境報錯
        self.ner_pipeline = pipeline(
            "ner",
            model="Davlan/xlm-roberta-large-ner-hrl",
            tokenizer="Davlan/xlm-roberta-large-ner-hrl",
            use_fast=False, 
            aggregation_strategy="simple",
            device=device
        )
        print("--- 模型載入完成 ---")

    def _expand_person_name(self, entities, text):
        if not entities: return []
        chinese_char_pattern = r'[\u4e00-\u9fa5]'
        for entity in entities:
            if entity and isinstance(entity, dict) and entity.get('type') == 'Person':
                text_content = entity.get('text', '')
                if text_content and len(text_content) == 1 and re.match(chinese_char_pattern, text_content):
                    current_end = entity.get('end')
                    if current_end is not None:
                        next_chars = text[current_end:current_end+2]
                        extend_len = 0
                        for char in next_chars:
                            if re.match(chinese_char_pattern, char): extend_len += 1
                            else: break
                        if extend_len > 0:
                            new_end = current_end + extend_len
                            entity['text'] = text[entity['start']:new_end]
                            entity['end'] = new_end
        return [e for e in entities if e]

    def _vacuum_address_prefix(self, entities, text):
        if not entities: return []
        keywords = r"No\.|Flat|Rm|Room|Unit|Shop|Suite|Block|Blk|Tower|Phase|Level|Lvl|Floor|Flr|G\/F|Basement|Estate|Garden|Court|Mansion|Bldg|Building"
        prefix_pattern = r'((?:(?:' + keywords + r')[\s\.]*[A-Za-z0-9\-\/]*|[\d\-\/]+[A-Za-z]?)(?:[\s,.\-]+))+$'
        for entity in entities:
            if entity and isinstance(entity, dict) and entity.get('type') == 'Address':
                current_start = entity.get('start')
                if current_start is not None:
                    preceding_text = text[:current_start]
                    match = re.search(prefix_pattern, preceding_text, re.IGNORECASE)
                    if match:
                        prefix_str = match.group(1)
                        new_start = current_start - len(prefix_str)
                        entity['start'] = new_start
                        entity['text'] = prefix_str + entity['text']
        return [e for e in entities if e]

    def _merge_adjacent_entities(self, entities, text, threshold=10):
        if not entities: return []
        # 安全排序過濾
        valid_entities = [e for e in entities if e and isinstance(e, dict) and isinstance(e.get('start'), int)]
        if not valid_entities: return []
        valid_entities.sort(key=lambda x: x['start'])
        
        merged = []
        current = valid_entities[0]
        for next_ent in valid_entities[1:]:
            gap_start = current.get('end', current['start'])
            gap_end = next_ent.get('start', 0)
            gap_text = text[gap_start:gap_end]
            is_gap_safe = bool(re.match(r'^[\s\d,.\-/()]*$', gap_text))
            if current['type'] == next_ent['type'] and (len(gap_text) <= threshold and is_gap_safe):
                new_end = next_ent['end']
                current['text'] = text[current['start']:new_end]
                current['end'] = new_end
            else:
                merged.append(current)
                current = next_ent
        merged.append(current)
        return merged

    def tokenize(self, text):
        candidates = []
        # Regex 部分 (HKID, Phone)
        for match in re.finditer(r'[A-Za-z]{1,2}\d{6}\(?[0-9A-Za-z]\)?', text):
            candidates.append({"start": match.start(), "end": match.end(), "type": "HKID", "text": match.group(), "priority": 10})
        for match in re.finditer(r'\b[23569]\d{7}\b', text):
            candidates.append({"start": match.start(), "end": match.end(), "type": "Phone", "text": match.group(), "priority": 10})

        # AI NER 部分
        try:
            ai_output = self.ner_pipeline(text)
        except: ai_output = []
        target_labels = {"PER": "Person", "LOC": "Address", "ORG": "Org"}
        raw_ai = []
        if ai_output:
            for e in ai_output:
                if isinstance(e, dict) and e.get('entity_group') in target_labels and e.get('score', 0) > 0.3:
                    raw_ai.append({"start": e['start'], "end": e['end'], "type": target_labels[e['entity_group']], "text": text[e['start']:e['end']], "priority": 5})

        # 修復流水線
        c1 = self._expand_person_name(raw_ai, text) or []
        c2 = self._vacuum_address_prefix(c1, text) or []
        c3 = self._merge_adjacent_entities(c2, text) or []
        candidates.extend(c3)

        if not candidates: return {"MaskedInput": text, "Mappings": {}}

        # 最終過濾與遮蔽
        final_candidates = [c for c in candidates if c and isinstance(c.get('start'), int)]
        final_candidates.sort(key=lambda x: (-x.get('priority', 0), x.get('start', 0)))
        
        final_entities, occupied_mask = [], [False] * len(text)
        for cand in final_candidates:
            if not any(occupied_mask[i] for i in range(cand['start'], cand['end'])):
                final_entities.append(cand)
                for i in range(cand['start'], cand['end']): occupied_mask[i] = True

        final_entities.sort(key=lambda x: x['start'])
        mappings, result_text, last_idx = {}, "", 0
        counters = {"Person": 1, "Address": 1, "Org": 1, "Phone": 1, "HKID": 1}

        for entity in final_entities:
            result_text += text[last_idx:entity['start']]
            etype = entity['type']
            tag = f"[{etype}{counters.get(etype, 1):02d}]"
            counters[etype] = counters.get(etype, 1) + 1
            mappings[tag] = entity['text']
            result_text += tag
            last_idx = entity['end']
        
        result_text += text[last_idx:]
        return {"MaskedInput": result_text, "Mappings": mappings}

# ==========================================
# 2. AI 段落生成模組 (Step 2)
# ==========================================
def call_ollama_for_paragraph(masked_data):
    url = "http://localhost:11434/api/chat"
    
    # 這裡明確要求 Qwen 不要輸出 JSON，只輸出段落
    payload = {
        "model": "qwen3:8b", 
        "messages": [
            {
                "role": "system", 
                "content": "你是一個行政助手。請根據用戶要求撰寫一段文字段落。必須原封不動保留所有 [TagXX] 格式標籤。嚴禁輸出 JSON。直接輸出最終段落。"
            },
            {
                "role": "user", 
                "content": f"根據以下內容寫一份聯繫備忘錄段落：\n{masked_data['MaskedInput']}"
            }
        ],
        "stream": False,
        "options": {"temperature": 0.2}
    }

    print("--- [Step 2] 傳送脫敏文字至 Ollama (Qwen3:8b) ---")
    print("提示：模型正在推理中，請等候大約 1 分鐘...")
    
    try:
        response = requests.post(url, json=payload, timeout=300)
        response.raise_for_status()
        content = response.json()['message']['content']
        # 移除 Qwen 的推理標籤 <think>
        ai_reply = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
        return ai_reply
    except Exception as e:
        print(f"❌ AI 處理失敗: {e}")
        return None

# ==========================================
# 3. 本地還原模組 (Step 3)
# ==========================================
def unmask_final_paragraph(ai_paragraph, mappings):
    print("--- [Step 3] 本地還原數據至段落中 ---")
    
    final_text = ai_paragraph
    # 遍歷所有的標籤並替換回真實內容
    for tag, real_value in mappings.items():
        if tag in final_text:
            final_text = final_text.replace(tag, real_value)
    
    return final_text

# ==========================================
# 執行主程序
# ==========================================
if __name__ == "__main__":
    # 初始化
    tokenizer = HK_PII_Tokenizer_Ultimate(device=-1)
    
    # 用戶輸入 (包含人名、電話、地址)
    user_input = "請幫我聯絡陳大文，電話係 61234567，叫佢聽日去中環皇后大道中100號開會。"
    print(f"\n[原始用戶輸入]: {user_input}")

    # 1. 脫敏 (Step 1)
    masked_data = tokenizer.tokenize(user_input)
    print(f"\n[Step 1 脫敏結果]:\n{masked_data['MaskedInput']}")

    # 2. AI 處理 (Step 2)
    ai_result = call_ollama_for_paragraph(masked_data)

    if ai_result:
        print(f"\n[Step 2 AI 原始段落 (含標籤)]:\n{ai_result}")

        # 3. 還原 (Step 3)
        final_paragraph = unmask_final_paragraph(ai_result, masked_data['Mappings'])
        
        print(f"\n✅ [Step 3 還原後的最終段落]:\n{final_paragraph}")
        
        # 這裡你可以將 final_paragraph 傳送到 API 或存成檔案
    else:
        print("程序因錯誤而中斷。")