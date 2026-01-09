# src/inference/utils.py
import re
from collections import defaultdict
from src.config import MIN_SCORE_THRESHOLD, BLACKLIST, CANTONESE_NOISE

def get_url_ranges(text):
    """找出所有網址的索引區間，作為『禁止觸碰區』"""
    url_pattern = r'https?://[^\s,]+'
    return [match.span() for match in re.finditer(url_pattern, text)]

def is_in_forbidden_range(start, end, ranges):
    """檢查實體是否落在禁止區內"""
    for r_start, r_end in ranges:
        # 如果實體與 URL 區間有任何重疊，就視為在禁止區內
        if not (end <= r_start or start >= r_end):
            return True
    return False
# src/inference/utils.py

def merge_fragmented_entities(entities, text, label_configs):
    """
    label_configs: 定義不同標籤的合併距離，例如 ORG 可以跨 8 個字，PHONE 只跨 2 個字
    """
    if not entities: return []
    entities.sort(key=lambda x: x['start'])
    
    merged = []
    curr = entities[0]
    
    for next_ent in entities[1:]:
        # 獲取該標籤允許的最大間距，預設為 2
        max_gap = label_configs.get(curr['entity_group'], 2)
        gap = next_ent['start'] - curr['end']
        
        if next_ent['entity_group'] == curr['entity_group'] and gap <= max_gap:
            # 膠水邏輯：更新結束位置，並從原文重新截取完整字串
            curr['end'] = next_ent['end']
            curr['word'] = text[curr['start']:curr['end']]
            curr['score'] = max(float(curr['score']), float(next_ent['score']))
        else:
            merged.append(curr)
            curr = next_ent
    merged.append(curr)
    return merged

def clean_and_process_entities(results, text):
    url_ranges = get_url_ranges(text)
    
    # --- Phase 1: 彈性過濾 ---
    # 保留較多實體，讓後面的合併邏輯有材料可以用
    valid_ents = [r for r in results if float(r['score']) > 0.30] 
    valid_ents = [r for r in valid_ents if not is_in_forbidden_range(r['start'], r['end'], url_ranges)]

    # --- Phase 2: 分層合併 (Point 1 核心) ---
    # 針對機構和地址，給予強力的合併間距 (max_gap=8)
    # 針對人名、電話，給予保守的合併間距 (max_gap=2)
    configs = {
        "ORG": 8, 
        "ADDRESS": 8,
        "NAME": 2,
        "PHONE": 2
    }
    merged_ents = merge_fragmented_entities(valid_ents, text, configs)


def mask_text(text, entities):
    """根據識別出的實體由後往前進行遮蓋，避免索引偏移"""
    masked = text
    # 必須 reverse=True，否則前面替換後後面位置會亂掉
    for ent in sorted(entities, key=lambda x: x['start'], reverse=True):
        tag = f"[{ent['numbered_tag']}]"
        masked = masked[:ent['start']] + tag + masked[ent['end']:]
    return masked