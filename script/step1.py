import re
import json
from transformers import pipeline

class HK_PII_Tokenizer_Ultimate:
    def __init__(self, device=-1):
        print("載入 XLM-RoBERTa 模型...")
        self.ner_pipeline = pipeline(
            "ner", model="Davlan/xlm-roberta-large-ner-hrl",
            tokenizer="Davlan/xlm-roberta-large-ner-hrl",
            use_fast=False, aggregation_strategy="simple", device=device
        )

    def tokenize(self, text):
        candidates = []
        
        # --- 1. Regex 規則 ---
        
        # [地址] 強化版中文地址匹配 (防止食咗「號碼」個「號」)
        chi_addr = r'(?:香港|九龍|新界)(?:[\u4e00-\u9fa5]{1,5}(?:區|市|邨|苑|里|街|路|大道|段)){1,5}(?:\d+[-]\d+|\d+)[號樓室ABCDE]?'
        for m in re.finditer(chi_addr, text):
            candidates.append({"start": m.start(), "end": m.end(), "type": "Address", "text": m.group(), "priority": 9})

        # [電話] 8位香港電話
        for m in re.finditer(r'\b[23456789]\d{7}\b', text):
            candidates.append({"start": m.start(), "end": m.end(), "type": "Phone", "text": m.group(), "priority": 10})

        # [人名] 常見姓氏開頭
        simple_name = r'[陳李張黃何林王梁郭吳趙周徐孫馬朱胡郭謝鄭][\u4e00-\u9fa5]{1,2}'
        for m in re.finditer(simple_name, text):
            candidates.append({"start": m.start(), "end": m.end(), "type": "Person", "text": m.group(), "priority": 7})

        # --- 2. AI NER 補充 (加入防錯保護) ---
        try:
            ai_output = self.ner_pipeline(text)
            target_labels = {"PER": "Person", "LOC": "Address", "ORG": "Org"}
            for e in ai_output:
                # 關鍵修復：確保 start 同 end 唔係 None 且係數字
                if e.get('entity_group') in target_labels and e.get('score', 0) > 0.4:
                    s, env = e.get('start'), e.get('end')
                    if isinstance(s, int) and isinstance(env, int):
                        candidates.append({"start": s, "end": env, "type": target_labels[e['entity_group']], "text": text[s:env], "priority": 5})
        except Exception as err:
            print(f"AI 識別小錯誤: {err}")

        # --- 3. 解決衝突與數據清理 ---
        # 排除任何無效數據
        candidates = [c for c in candidates if c.get('start') is not None and c.get('end') is not None]
        
        # 排序：優先級(高->低)，長度(長->短)
        candidates.sort(key=lambda x: (-x['priority'], -(x['end'] - x['start'])))
        
        final_entities = []
        occupied = [False] * len(text)
        
        for cand in candidates:
            s, e = cand['start'], cand['end']
            if not any(occupied[i] for i in range(s, e)):
                final_entities.append(cand)
                for i in range(s, e): occupied[i] = True

        # --- 4. 產出結果 ---
        final_entities.sort(key=lambda x: x['start'])
        mappings, result_text, last_idx, counters = {}, "", 0, {"Person":1, "Address":1, "Org":1, "Phone":1}

        for entity in final_entities:
            result_text += text[last_idx:entity['start']]
            etype = entity['type']
            tag = f"[{etype}{counters.get(etype, 1):02d}]"
            counters[etype] = counters.get(etype, 1) + 1
            mappings[tag] = entity['text']
            result_text += tag
            last_idx = entity['end']
            
        result_text += text[last_idx:]
        return result_text, mappings

if __name__ == "__main__":
    raw_input = input("請輸入原始指令: ")
    tokenizer = HK_PII_Tokenizer_Ultimate()
    masked_text, mapping_data = tokenizer.tokenize(raw_input)

    with open("masked_input.txt", "w", encoding="utf-8") as f:
        f.write(masked_text)
    with open("mappings.json", "w", encoding="utf-8") as f:
        json.dump(mapping_data, f, ensure_ascii=False, indent=2)
    
    print(f"\nStep 1 脫敏完成！")
    print(f"脫敏文字: {masked_text}")