import json
import os
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
from peft import PeftModel
import re
from collections import defaultdict
import torch # 記得要 import torch

# ==========================================
# 1. Model Setup and Loading
# ==========================================
base_model_name = "Davlan/xlm-roberta-large-ner-hrl"
lora_model_path = "./final_lora_model" 

label_list = [
    "O", "B-NAME", "I-NAME", "B-ADDRESS", "I-ADDRESS", "B-PHONE", "I-PHONE", 
    "B-ID", "I-ID", "B-ACCOUNT", "I-ACCOUNT", "B-LICENSE_PLATE", "I-LICENSE_PLATE",
    "B-ORG", "I-ORG"
]

label2id = {l: i for i, l in enumerate(label_list)}
id2label = {i: l for l, i in label2id.items()}

print("Loading model...")
try:
    tokenizer = AutoTokenizer.from_pretrained(lora_model_path)
    base_model = AutoModelForTokenClassification.from_pretrained(
        base_model_name, num_labels=len(label2id), id2label=id2label, label2id=label2id, ignore_mismatched_sizes=True
    )
    model = PeftModel.from_pretrained(base_model, lora_model_path)
    model.eval()
except Exception as e:
    print(f"Model loading failed: {e}")
    exit()

#nlp = pipeline("token-classification", model=model, tokenizer=tokenizer, aggregation_strategy="simple", device=0)
if torch.cuda.is_available():
    device_id = 0
    print("🚀 Using Device: GPU (CUDA)")
elif torch.backends.mps.is_available():
    # 對於 Mac M1/M2 用戶
    device_id = "mps" 
    print("🍎 Using Device: Mac GPU (MPS)")
else:
    device_id = -1
    print("🐢 Using Device: CPU")

# 2. 初始化 Pipeline 時傳入 device_id
nlp = pipeline(
    "token-classification", 
    model=model, 
    tokenizer=tokenizer, 
    aggregation_strategy="simple", 
    device=device_id  # 改用變數
)
# ==========================================
# 2. Debugging Helper Functions
# ==========================================
def clean_and_process_entities(results, text):
    merged_entities = []
    merged_entities.sort(key=lambda x: (x['start'], -x['end'])) # 按開始位置排序
    
    no_overlap_entities = []
    if merged_entities:
        last_ent = merged_entities[0]
        for curr_ent in merged_entities[1:]:
            # 如果當前實體嘅開始位置，小於上一個實體嘅結束位置 -> 重疊
            if curr_ent['start'] < last_ent['end']:
                # 簡單策略：保留長度較長的
                if (curr_ent['end'] - curr_ent['start']) > (last_ent['end'] - last_ent['start']):
                    last_ent = curr_ent
                # 否則忽略 current
            else:
                no_overlap_entities.append(last_ent)
                last_ent = curr_ent
        no_overlap_entities.append(last_ent)
    
    merged_entities = no_overlap_entities
    # --- Phase 1: Initial Filter & Merge ---
    current_entity = None
    for res in results:
        # [Rule 1] Confidence Threshold
        if res['score'] < 0.60: 
            # DEBUG PRINT
            # print(f"❌ [Low Score] {text[res['start']:res['end']]} ({res['score']:.2f})")
            continue
        
        entity_group = res['entity_group']
        word = text[res['start']:res['end']]
        
        if current_entity and res['start'] == current_entity['end'] and current_entity['entity_group'] == entity_group:
            current_entity['word'] += word
            current_entity['end'] = res['end']
            current_entity['score_sum'] += res['score']
            current_entity['token_count'] += 1
        else:
            if current_entity:
                current_entity['score'] = current_entity['score_sum'] / current_entity['token_count']
                merged_entities.append(current_entity)
            current_entity = {
                "entity_group": entity_group, "word": word, "start": res['start'],
                "end": res['end'], "score": res['score'], "score_sum": res['score'], "token_count": 1
            }
    if current_entity:
        current_entity['score'] = current_entity['score_sum'] / current_entity['token_count']
        merged_entities.append(current_entity)

    # ================= NEW CODE START =================
    # [新增] 解決重疊問題 (De-overlap Logic)
    # 策略：如果位置重疊，保留「長度較長」的那個 (例如保留 "微軟" 棄 "微")
    if merged_entities:
        # 按開始位置排序，如果開始位置相同，則按長度(長到短)排序
        merged_entities.sort(key=lambda x: (x['start'], -x['end']))
        
        no_overlap_entities = []
        last_ent = merged_entities[0]
        
        for curr_ent in merged_entities[1:]:
            # 檢查重疊：如果當前實體的 Start < 上一個實體的 End
            if curr_ent['start'] < last_ent['end']:
                # 重疊了！比較長度
                last_len = last_ent['end'] - last_ent['start']
                curr_len = curr_ent['end'] - curr_ent['start']
                
                if curr_len > last_len:
                    last_ent = curr_ent  # 取代為更長的
                elif curr_len == last_len:
                    if curr_ent['score'] > last_ent['score']: # 長度一樣，比分數
                        last_ent = curr_ent
                # 否則保持 last_ent (忽略較短的 current)
            else:
                # 無重疊，將上一個存入結果，並更新 last 為當前
                no_overlap_entities.append(last_ent)
                last_ent = curr_ent
        
        no_overlap_entities.append(last_ent) # 別忘了最後一個
        merged_entities = no_overlap_entities
    # ================= NEW CODE END =================

    # ... (接 Phase 2: Advanced Cleaning Rules)
    # --- Phase 2: Advanced Cleaning Rules ---
    final_cleaned = []
    blacklist_words = ["健在", "不詳", "未知", "無業", "離異", "單身", "不便", "整合", "處理", "錯誤", "高度", "闊度"]
    cantonese_noise = ["黎", "係", "打", "之前", "主席", "職", "仲要"] 

    for ent in merged_entities:
        original_word = ent['word']
        # [Pre-clean]: Strip punctuation
        word = ent['word'].strip().strip("「」『』《》()（）。，、！？：；")
        ent['word'] = word
        
        label = ent['entity_group']
        start = ent['start']
        end = ent['end']
        
        # 1. Basic Filters
        if not word: 
            print(f"❌ [Empty] {original_word}")
            continue
        if word in blacklist_words or word in cantonese_noise: 
            print(f"❌ [Blacklist] {word}")
            continue
        if re.match(r'^[\W_]+$', word): 
            print(f"❌ [Symbol Only] {word}")
            continue

        # 2. [Rule A: URL/Path Filter] (Fixed)
        is_url = False
        if any(x in word.lower() for x in ['http', 'www.', '.com', '.org', '.net', '.html', '.php']):
            is_url = True
        if '%' in word and re.search(r'%[0-9A-Fa-f]{2}', word):
            is_url = True
        if is_url: 
            print(f"❌ [Rule A: URL] {word}")
            continue

        # 3. [Rule B: Measurement Filter]
        if label in ['ID', 'ACCOUNT', 'PHONE', 'LICENSE_PLATE']:
            if re.search(r'\d+(cm|kg|km|m|g|ml|L|Hz|GB|MB|KB|ft|in)$', word, re.IGNORECASE): 
                print(f"❌ [Rule B: Unit] {word}")
                continue

        # 4. [Rule C: Account/Phone Strict Clean]
        if label in ['ACCOUNT', 'PHONE']:
            cleaned_word = re.sub(r'[^\d\+\-\(\)\s]', '', word).strip()
            if len(cleaned_word) < 3: 
                print(f"❌ [Rule C: Short Acc/Phone] {word} -> {cleaned_word}")
                continue
            ent['word'] = cleaned_word

        # 5. [Rule D: ID/Plate Clean Chinese]
        if label in ['ID', 'LICENSE_PLATE']:
            cleaned_word = re.sub(r'[\u4e00-\u9fff]+', '', word).strip()
            if len(cleaned_word) < 2: 
                print(f"❌ [Rule D: Short ID/Plate] {word} -> {cleaned_word}")
                continue
            ent['word'] = cleaned_word

        # 6. [Rule E: License Plate Left-Extension]
        if label == 'LICENSE_PLATE' and re.match(r'^\d+$', ent['word']):
            pre_start = start - 3 if start >=3 else 0
            prefix_text = text[pre_start:start]
            prefix_match = re.search(r'([A-Z]{1,2})\s?$', prefix_text)
            if prefix_match:
                prefix = prefix_match.group(1)
                ent['start'] = start - len(prefix_match.group(0))
                ent['word'] = prefix + ent['word']

        # 7. [Rule F: Smart Name Length & Logic]
        if label == 'NAME':
            has_chinese = bool(re.search(r'[\u4e00-\u9fff]', word))
            has_english = bool(re.search(r'[a-zA-Z]', word))
            has_separator = bool(re.search(r'[·．]', word))

            if has_chinese:
                if has_english and len(word) > 12: 
                    print(f"❌ [Rule F: Mixed Name Too Long] {word}")
                    continue
                if not has_english:
                    if has_separator:
                        if len(word) > 15: 
                            print(f"❌ [Rule F: Transliterated Name Too Long] {word}")
                            continue
                    elif len(word) > 5: 
                        print(f"❌ [Rule F: Chinese Name Too Long] {word}")
                        continue
                if len(word) == 1 and ent['score'] < 0.995: 
                    print(f"❌ [Rule F: Single Char Name] {word}")
                    continue
            else:
                if len(word) > 25: 
                    print(f"❌ [Rule F: English Name Too Long] {word}")
                    continue
                if len(word) < 2: 
                    print(f"❌ [Rule F: English Name Too Short] {word}")
                    continue

        # 8. [Rule G: ID Bracket Fix]
        if label == 'ID' and end < len(text) and text[end] == ')':
             ent['end'] += 1
             ent['word'] += ')'

        # 9. [Rule H: English Name Right-Completion]
        if label == 'NAME':
            if re.search(r'[a-zA-Z]$', ent['word']):
                remaining_text = text[ent['end']:]
                suffix_match = re.match(r'^([a-z]+)', remaining_text)
                if suffix_match:
                    suffix = suffix_match.group(1)
                    ent['end'] += len(suffix)
                    ent['word'] += suffix

        # 10. [Rule I: Address Cleaning]
        if label == 'ADDRESS':
            if len(word) < 2 and re.search(r'[\u4e00-\u9fff]', word):
                print(f"❌ [Rule I: Single Char Address] {word}")
                continue
            geo_terms = ["平原", "山脈", "盆地", "沙漠", "地貌", "高地", "高原", "河流", "水庫", "台塬"]
            if any(term in word for term in geo_terms):
                print(f"❌ [Rule I: Geo Term] {word}")
                continue
# [新增] Rule J: 過濾單字中文機構 (除非是非常常見的簡稱如 "中電", "港鐵" - 這裡只過濾單字)
        if label == 'ORG':
            # 如果是純中文，且只有 1 個字 (例如 "微", "國") -> 踢走
            if len(word) == 1 and re.search(r'[\u4e00-\u9fff]', word):
                continue
            
            # 過濾常見誤判詞彙
            if word in ["國際", "有限公司", "集團", "分行"]:
                continue
        final_cleaned.append(ent)
# ... (在 Phase 2 loop 完結後，Phase 3 之前加入)
# ... (Phase 2 loop 完結後，Phase 3 之前) ...

    # ================= NEW CODE START =================
    # [新增/更新] 主動掃描漏網的「銀行戶口」同「電話號碼」
    # 原理：建立一個 set 記錄已被 AI 捉到的位置，然後用 Regex 掃描剩下的數字
    
    existing_ranges = set()
    for ent in final_cleaned:
        for i in range(ent['start'], ent['end']):
            existing_ranges.add(i)

    # 定義補漏規則 (Regex Patterns)
    fallback_patterns = [
        # 1. 香港電話 (8位數字，2-9開頭)
        {"name": "PHONE", "pattern": r'\b[23569]\d{7}\b'},
        
        # 2. 銀行戶口 (10-12位數字)
        {"name": "ACCOUNT", "pattern": r'\b\d{10,12}\b'}
    ]

    for rule in fallback_patterns:
        for match in re.finditer(rule["pattern"], text):
            start, end = match.span()
            
            # 檢查重疊：如果這串數字已經被 AI (或之前的 Regex) 捉過，就跳過
            # 例如 AI 捉咗 ID "R98272829"，Regex 就唔好當佢係電話
            if any(i in existing_ranges for i in range(start, end)):
                continue
            
            # 成功補漏！加入結果
            final_cleaned.append({
                "entity_group": rule["name"],
                "word": match.group(),
                "start": start,
                "end": end,
                "score": 1.0,      # Regex 信心係 100%
                "score_sum": 1.0,
                "token_count": 1
            })
            
            # 更新 existing_ranges，防止同一個數字被捉兩次
            for i in range(start, end):
                existing_ranges.add(i)
    # ================= NEW CODE END =================

    # --- Phase 3: Numbering & Formatting ---
    # ... (接住原本嘅代碼)
    # ... (接 Phase 3: Numbering)
    # --- Phase 3: Numbering & Formatting ---
    final_output = []
    counters = defaultdict(int)
    entity_registry = {} 
    final_cleaned.sort(key=lambda x: x['start'])

    for entity in final_cleaned:
        label = entity['entity_group']
        dict_key = (label, entity['word'])
        if dict_key in entity_registry:
            seq_num = entity_registry[dict_key]
        else:
            counters[label] += 1
            seq_num = counters[label]
            entity_registry[dict_key] = seq_num
        entity['numbered_tag'] = f"{label}-{seq_num}"
        final_output.append(entity)
        
    return final_output

def mask_text(text, entities):
    masked_text = text
    for entity in sorted(entities, key=lambda x: x['start'], reverse=True):
        start, end = entity['start'], entity['end']
        tag = f"[{entity['numbered_tag']}]"
        masked_text = masked_text[:start] + tag + masked_text[end:]
    return masked_text

def load_test_inputs(filepath="train/test_data.json"):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                print(f"📂 Loaded test data from {filepath}")
                return json.load(f)
        except Exception: pass
    return ["你好，我係 Sammi。我的電話係 9123 4567。"]

# Run
test_inputs = load_test_inputs("train/test_data.json")

print("=" * 60)
for text in test_inputs:
    print(f"\nOriginal Input: {text}")
    
    raw_results = nlp(text)
    processed_entities = clean_and_process_entities(raw_results, text)
    masked_result = mask_text(text, processed_entities)
    
    print("-" * 30)
    print(f"Masked Result: {masked_result}")
    print("Detected Entities:")
    for e in processed_entities:
        print(f" - {e['word']} | {e['numbered_tag']} ({e['score']:.1%})")
    print("=" * 60)