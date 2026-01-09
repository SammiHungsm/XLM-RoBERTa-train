# src/inference/utils.py
import re
from collections import defaultdict
# 匯入 config 中的過濾名單與閾值
from src.config import BLACKLIST, CANTONESE_NOISE, MIN_SCORE_THRESHOLD

def clean_and_process_entities(results, text):
    """
    核心清理邏輯：
    1. 去除重疊實體 (De-overlap)
    2. 信心分數過濾與黑名單過濾
    3. 正則表達式補位 (Regex Fallback)
    4. 自動編號 (Numbered Tags)
    """
    
    # --- Phase 1: 去重疊 (優先保留較長的實體，長度相同則比分數) ---
    merged_entities = sorted(results, key=lambda x: (x['start'], -x['end']))
    no_overlap = []
    if merged_entities:
        last = merged_entities[0]
        for curr in merged_entities[1:]:
            if curr['start'] < last['end']:
                # 如果重疊，保留長度較長者
                if (curr['end'] - curr['start']) > (last['end'] - last['start']):
                    last = curr
                # 長度相同則保留分數較高者
                elif (curr['end'] - curr['start']) == (last['end'] - last['start']):
                    if curr['score'] > last['score']:
                        last = curr
            else:
                no_overlap.append(last)
                last = curr
        no_overlap.append(last)

    # --- Phase 2: 規則過濾與修正 ---
    final_cleaned = []
    for ent in no_overlap:
        # 清理字串前後的標點符號
        word = ent['word'].strip().strip("「」『』《》()（）。，、！？：；")
        ent['word'] = word
        label = ent['entity_group']
        
        # 轉為原生 float 防止 JSON 序列化失敗 (float32 Error)
        ent['score'] = float(ent['score'])

        # 1. 基本過濾
        if not word or ent['score'] < MIN_SCORE_THRESHOLD: continue
        if word in BLACKLIST or word in CANTONESE_NOISE: continue
        if re.match(r'^[\W_]+$', word): continue # 排除純符號

        # 2. URL 保護：防止捉到網址路徑裡的關鍵字
        if any(x in word.lower() for x in ['http', 'www.', '.com', '.html']): continue

        # 3. ID 括號自動補完：如果 AI 漏掉最後一個括號
        if label == 'ID' and ent['end'] < len(text) and text[ent['end']] == ')':
             ent['end'] += 1
             ent['word'] += ')'

        final_cleaned.append(ent)

    # --- Phase 3: 正則補漏 (針對 HKID, Phone, Account 的終極保險) ---
    existing_ranges = set()
    for ent in final_cleaned:
        for i in range(ent['start'], ent['end']):
            existing_ranges.add(i)

    fallback_patterns = [
        {"name": "ID", "pattern": r'\b[A-Z]{1,2}\d{6}\(?[0-9A]\)?\b'}, # 香港身份證
        {"name": "PHONE", "pattern": r'\b[23569]\d{7}\b'},             # 香港 8 位電話
        {"name": "ACCOUNT", "pattern": r'\b\d{10,12}\b'}               # 一般銀行戶口格式
    ]

    for rule in fallback_patterns:
        for match in re.finditer(rule["pattern"], text):
            start, end = match.span()
            # 如果 AI 沒有捕捉到這個區間，則由正則補上
            if not any(i in existing_ranges for i in range(start, end)):
                final_cleaned.append({
                    "entity_group": rule["name"],
                    "word": match.group(),
                    "start": start,
                    "end": end,
                    "score": 1.0, # 正則匹配給予滿分
                    "numbered_tag": ""
                })
                for i in range(start, end):
                    existing_ranges.add(i)

    # --- Phase 4: 自動編號 (例如：NAME-01, NAME-02) ---
    final_output = []
    counters = defaultdict(int)
    registry = {} # 確保同一個詞在同文章中編號一致
    
    final_cleaned.sort(key=lambda x: x['start'])
    
    for ent in final_cleaned:
        label = ent['entity_group']
        word = ent['word']
        key = (label, word)
        
        if key in registry:
            seq = registry[key]
        else:
            counters[label] += 1
            seq = counters[label]
            registry[key] = seq
        
        ent['numbered_tag'] = f"{label}-{seq:02d}"
        final_output.append(ent)
        
    return final_output

def mask_text(text, entities):
    """
    根據識別出的實體，由後往前進行文本遮蓋，避免索引偏移
    """
    masked = text
    # 必須 reverse=True，否則前面替換後後面位置會亂掉
    for ent in sorted(entities, key=lambda x: x['start'], reverse=True):
        tag = f"[{ent['numbered_tag']}]"
        masked = masked[:ent['start']] + tag + masked[ent['end']:]
    return masked