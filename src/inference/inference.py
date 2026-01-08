import json
import os
import torch
import re
from collections import defaultdict
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
from peft import PeftModel

# ==========================================
# 1. 配置與模型載入
# ==========================================
BASE_MODEL_NAME = "Davlan/xlm-roberta-large-ner-hrl"
LORA_MODEL_PATH = "./final_lora_model" 

LABEL_LIST = [
    "O", "B-NAME", "I-NAME", "B-ADDRESS", "I-ADDRESS", "B-PHONE", "I-PHONE", 
    "B-ID", "I-ID", "B-ACCOUNT", "I-ACCOUNT", "B-LICENSE_PLATE", "I-LICENSE_PLATE",
    "B-ORG", "I-ORG"
]

label2id = {l: i for i, l in enumerate(LABEL_LIST)}
id2label = {i: l for l, i in label2id.items()}

print("🚀 [Step 1] Loading Model...")

if torch.cuda.is_available():
    device_id = 0
    print(f"✅ Using Device: GPU (CUDA: {torch.cuda.get_device_name(0)})")
elif torch.backends.mps.is_available():
    device_id = "mps"
    print("🍎 Using Device: Mac GPU (MPS)")
else:
    device_id = -1
    print("🐢 Using Device: CPU")

try:
    tokenizer = AutoTokenizer.from_pretrained(LORA_MODEL_PATH)
    base_model = AutoModelForTokenClassification.from_pretrained(
        BASE_MODEL_NAME, 
        num_labels=len(label2id), 
        id2label=id2label, 
        label2id=label2id, 
        ignore_mismatched_sizes=True
    )
    model = PeftModel.from_pretrained(base_model, LORA_MODEL_PATH)
    model.eval()
    
    nlp = pipeline(
        "token-classification", 
        model=model, 
        tokenizer=tokenizer, 
        aggregation_strategy="simple",
        device=device_id
    )
    print("✅ Model Loaded Successfully!")
except Exception as e:
    print(f"❌ Model loading failed: {e}")
    exit()

# ==========================================
# 2. 核心清理與邏輯
# ==========================================
def clean_and_process_entities(results, text):
    
    # --- Phase 0: 去重疊 (De-overlap) ---
    merged_entities = sorted(results, key=lambda x: (x['start'], -x['end']))
    no_overlap = []
    if merged_entities:
        last = merged_entities[0]
        for curr in merged_entities[1:]:
            if curr['start'] < last['end']:
                if (curr['end'] - curr['start']) > (last['end'] - last['start']):
                    last = curr
                elif (curr['end'] - curr['start']) == (last['end'] - last['start']):
                    if curr['score'] > last['score']: last = curr
            else:
                no_overlap.append(last)
                last = curr
        no_overlap.append(last)
    merged_entities = no_overlap

    # --- Phase 1: 規則過濾 (Rule-based Filter) ---
    final_cleaned = []
    blacklist = ["健在", "不詳", "未知", "無業", "離異", "單身", "不便", "整合", "處理", "錯誤", "高度", "闊度"]
    cantonese_noise = ["黎", "係", "打", "之前", "主席", "職", "仲要", "搵"]
    
    for ent in merged_entities:
        word = ent['word'].strip().strip("「」『』《》()（）。，、！？：；")
        ent['word'] = word
        label = ent['entity_group']
        
        # 1. 基本過濾
        if not word or ent['score'] < 0.45: continue
        if word in blacklist or word in cantonese_noise: continue
        if re.match(r'^[\W_]+$', word): continue

        # 2. URL 保護 (絕對不要捉 URL 裡的字)
        if any(x in word.lower() for x in ['http', 'www.', '.com', '.html', 'mingpao']): continue

        # 3. 單位過濾 (只針對 Phone/Account)
        if label in ['PHONE', 'ACCOUNT']:
            if re.search(r'\d+(cm|kg|km|m|g|ml|L|Hz|GB|MB|KB|ft|in)$', word, re.IGNORECASE): continue

        # 4. 符號清理 (Account/Phone 只能有數字和符號)
        if label in ['PHONE', 'ACCOUNT']:
            cleaned = re.sub(r'[^\d\+\-\(\)\s]', '', word).strip()
            if len(cleaned) < 3: continue
            ent['word'] = cleaned

        # 5. ID/Plate 清理中文
        if label in ['ID', 'LICENSE_PLATE']:
            cleaned = re.sub(r'[\u4e00-\u9fff]+', '', word).strip()
            if len(cleaned) < 2: continue
            ent['word'] = cleaned

        # 6. [Rule H] 英文名自動補全 (修復 "Sam" -> "Sammi")
        if label == 'NAME':
            # 如果結尾是英文字母
            if re.search(r'[a-zA-Z]$', ent['word']):
                remaining_text = text[ent['end']:]
                # 檢查後面是否緊接英文字母
                suffix_match = re.match(r'^([a-z]+)', remaining_text)
                if suffix_match:
                    suffix = suffix_match.group(1)
                    ent['end'] += len(suffix)
                    ent['word'] += suffix
                    # print(f"🔧 Auto-completed name: {word} -> {ent['word']}")

        # 7. ID 括號補全
        if label == 'ID' and ent['end'] < len(text) and text[ent['end']] == ')':
             ent['end'] += 1; ent['word'] += ')'

        final_cleaned.append(ent)

    # --- Phase 2: 正則補漏 (Regex Fallback) ---
    existing_ranges = set()
    for ent in final_cleaned:
        for i in range(ent['start'], ent['end']): existing_ranges.add(i)

    # [Helper] 檢查是否在 URL 內
    def is_url_part(start, end, full_text):
        surroundings = ['/', '-', '.', '=', '?', '_']
        # 檢查前面
        if start > 0 and full_text[start-1] in surroundings: return True
        # 檢查後面
        if end < len(full_text) and full_text[end] in surroundings: return True
        return False

    fallback_patterns = [
        # 1. 香港身份證 (優先級最高！防止被 Phone/Account 搶走)
        # 支援括號 A123456(7) 或 A1234567
        {"name": "ID", "pattern": r'\b[A-Z]{1,2}\d{6}\(?[0-9A]\)?\b'},
        
        # 2. 香港電話 (8位)
        {"name": "PHONE", "pattern": r'\b[23569]\d{7}\b'},
        
        # 3. 銀行戶口 (10-12位)
        {"name": "ACCOUNT", "pattern": r'\b\d{10,12}\b'}
    ]

    for rule in fallback_patterns:
        for match in re.finditer(rule["pattern"], text):
            start, end = match.span()
            
            # [Fix 1] 檢查重疊 (如果 AI 已經捉了這個位置，跳過)
            if any(i in existing_ranges for i in range(start, end)):
                # 特例：如果是 ID，且 AI 捉得不完整 (例如只捉了數字)，我們用 Regex 覆蓋它！
                if rule["name"] in ["ID", "ACCOUNT"]:
                    # 移除舊的 AI 結果，改用 Regex (更準確)
                    final_cleaned = [e for e in final_cleaned if not (e['start'] >= start and e['end'] <= end)]
                    # 清除舊 Range
                    # (這裡簡化處理：直接加入新 ID，後面編號會自動處理)
                else:
                    continue
            
            # [Fix 2] URL 保護 (針對 Phone/Account)
            if rule["name"] in ["PHONE", "ACCOUNT"]:
                if is_url_part(start, end, text):
                    # print(f"🛡️ Ignored URL part: {match.group()}")
                    continue

            final_cleaned.append({
                "entity_group": rule["name"], "word": match.group(),
                "start": start, "end": end, "score": 1.0, "numbered_tag": ""
            })
            for i in range(start, end): existing_ranges.add(i)

    # --- Phase 3: 編號 ---
    final_output = []
    counters = defaultdict(int)
    registry = {}
    
    final_cleaned.sort(key=lambda x: x['start'])
    
    for ent in final_cleaned:
        label = ent['entity_group']
        key = (label, ent['word'])
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
    masked = text
    # 從後往前替換，避免索引偏移
    for ent in sorted(entities, key=lambda x: x['start'], reverse=True):
        tag = f"[{ent['numbered_tag']}]"
        masked = masked[:ent['start']] + tag + masked[ent['end']:]
    return masked

# ==========================================
# 3. 執行測試
# ==========================================
if __name__ == "__main__":
    # 強制測試一些 Edge Case
    test_inputs = [
        "據中國國家鐵路集團有限公司今（4日）披露，原文網址：https://news.mingpao.com/ins/article/20260104/s00004",
        "李嘉誠住在香港中環，電話 9123 4567。",
        "我的 ID 是 A123456(7)，戶口 123-456-789。",
        "Sammi 之前打過黎。",
        "Bank Account = 274542182882"
    ]
    
    if os.path.exists("train/test_data.json"):
        with open("train/test_data.json", "r", encoding="utf-8") as f:
            file_inputs = json.load(f)
            # 將文件內容加到測試列表後面
            test_inputs.extend(file_inputs)

    print("="*60)
    # 去重
    test_inputs = list(dict.fromkeys(test_inputs)) 
    
    for text in test_inputs:
        print(f"\n📝 Input: {text}")
        results = nlp(text)
        processed = clean_and_process_entities(results, text)
        masked = mask_text(text, processed)
        print(f"🎭 Masked: {masked}")
        for e in processed:
            print(f"   - [{e['numbered_tag']}] {e['word']} ({e['score']:.1%})")
    print("="*60)