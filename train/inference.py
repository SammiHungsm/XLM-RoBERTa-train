import json
import os
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
from peft import PeftModel
import re
from collections import defaultdict

# ==========================================
# 1. Model Setup and Loading
# ==========================================
base_model_name = "Davlan/xlm-roberta-large-ner-hrl"
lora_model_path = "./final_lora_model" 

# Must match prepare_data.py (15 labels)
label_list = [
    "O", 
    "B-NAME", "I-NAME", 
    "B-ADDRESS", "I-ADDRESS", 
    "B-PHONE", "I-PHONE", 
    "B-ID", "I-ID", 
    "B-ACCOUNT", "I-ACCOUNT", 
    "B-LICENSE_PLATE", "I-LICENSE_PLATE",
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
    print("Hint: If Size Mismatch error, check if you deleted the old output folder before retraining.")
    exit()

nlp = pipeline("token-classification", model=model, tokenizer=tokenizer, aggregation_strategy="simple", device=0)

# ==========================================
# 2. Helper Functions
# ==========================================
def analyze_text_composition(text):
    if not text: return "N/A"
    chi_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    eng_chars = len(re.findall(r'[a-zA-Z]', text))
    total = chi_chars + eng_chars
    if total == 0: return "No alphanumeric"
    return f"Chinese: {chi_chars/total*100:.1f}% | English: {eng_chars/total*100:.1f}%"

def clean_and_process_entities(results, text):
    merged_entities = []
    
    # --- Phase 1: Initial Filter & Merge ---
    current_entity = None
    for res in results:
        # [Rule 1] Confidence Threshold
        if res['score'] < 0.60: continue
        
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

    # --- Phase 2: Advanced Cleaning Rules ---
    final_cleaned = []
    blacklist_words = ["健在", "不詳", "未知", "無業", "離異", "單身", "不便", "整合", "處理", "錯誤", "高度", "闊度"]
    cantonese_noise = ["黎", "係", "打", "之前", "主席", "職", "長和", "仲要"] 

    for ent in merged_entities:
        # [Pre-clean]: Strip punctuation like quote marks (Fixes "「慈悲")
        word = ent['word'].strip().strip("「」『』《》()（）")
        # Update word in entity object immediately
        ent['word'] = word 
        
        label = ent['entity_group']
        start = ent['start']
        end = ent['end']
        
        # 1. Basic Filters
        if not word: continue
        if word in blacklist_words or word in cantonese_noise: continue
        if re.match(r'^[\W_]+$', word): continue

        # 2. [Rule A: URL/Path Filter]
        if '%' in word or 'http' in word or 'www' in word or '.com' in word or '/' in word: continue

        # 3. [Rule B: Measurement Filter]
        if label in ['ID', 'ACCOUNT', 'PHONE', 'LICENSE_PLATE']:
            if re.search(r'\d+(cm|kg|km|m|g|ml|L|Hz|GB|MB|KB|ft|in)$', word, re.IGNORECASE): continue

        # 4. [Rule C: Account/Phone Strict Clean]
        if label in ['ACCOUNT', 'PHONE']:
            cleaned_word = re.sub(r'[^\d\+\-\(\)\s]', '', word).strip()
            if len(cleaned_word) < 3: continue
            ent['word'] = cleaned_word

        # 5. [Rule D: ID/Plate Clean Chinese]
        if label in ['ID', 'LICENSE_PLATE']:
            cleaned_word = re.sub(r'[\u4e00-\u9fff]+', '', word).strip()
            if len(cleaned_word) < 2: continue
            ent['word'] = cleaned_word

        # 6. [Rule E: License Plate Left-Extension] (Fixes "1234" missing "AB")
        if label == 'LICENSE_PLATE' and re.match(r'^\d+$', ent['word']):
            pre_start = start - 3 if start >=3 else 0
            prefix_text = text[pre_start:start]
            prefix_match = re.search(r'([A-Z]{1,2})\s?$', prefix_text)
            if prefix_match:
                prefix = prefix_match.group(1)
                ent['start'] = start - len(prefix_match.group(0))
                ent['word'] = prefix + ent['word']

        # 7. [Rule F: Smart Name Length & Logic] (Fixes "Edmond梁" & "華特．艾薩克森")
        if label == 'NAME':
            has_chinese = bool(re.search(r'[\u4e00-\u9fff]', word))
            has_english = bool(re.search(r'[a-zA-Z]', word))
            # Check for transliteration dots (e.g., in "Walter.Isaacson")
            has_separator = bool(re.search(r'[·．]', word))

            if has_chinese:
                # Case 1: Mixed Chinese & English (e.g., Edmond梁) -> Allow up to 12
                if has_english and len(word) > 12: continue
                
                # Case 2: Pure Chinese
                if not has_english:
                    # If it has a separator (Transliterated name), allow longer (up to 15)
                    if has_separator:
                        if len(word) > 15: continue 
                    # Standard Chinese name, strict limit (5)
                    elif len(word) > 5: 
                        continue
                
                # Filter single char Chinese names (unless super confident)
                if len(word) == 1 and ent['score'] < 0.995: continue
            else:
                # Pure English
                if len(word) > 25: continue
                if len(word) < 2: continue

        # 8. [Rule G: ID Bracket Fix]
        if label == 'ID' and end < len(text) and text[end] == ')':
             ent['end'] += 1
             ent['word'] += ')'

        # 9. [Rule H: English Name Right-Completion] (Fixes "Sam" missing "mi")
        if label == 'NAME':
            if re.search(r'[a-zA-Z]$', ent['word']):
                remaining_text = text[ent['end']:]
                suffix_match = re.match(r'^([a-z]+)', remaining_text)
                if suffix_match:
                    suffix = suffix_match.group(1)
                    ent['end'] += len(suffix)
                    ent['word'] += suffix

        final_cleaned.append(ent)

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
    # Replace in reverse order to preserve indices
    for entity in sorted(entities, key=lambda x: x['start'], reverse=True):
        start, end = entity['start'], entity['end']
        tag = f"[{entity['numbered_tag']}]"
        masked_text = masked_text[:start] + tag + masked_text[end:]
    return masked_text

# ==========================================
# 3. Load Test Data
# ==========================================
def load_test_inputs(filepath="train/test_data.json"):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                print(f"📂 Loaded test data from {filepath}")
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Error loading JSON: {e}")
    
    # Fallback default
    print("⚠️ test_data.json not found, using default sample.")
    return ["你好，我係 Sammi。我的電話係 9123 4567。"]

# ==========================================
# 4. Execution
# ==========================================
# Load test data
test_inputs = load_test_inputs("train/test_data.json")

print("=" * 60)
for text in test_inputs:
    print(f"\nOriginal Input: {text}")
    print(f"📊 {analyze_text_composition(text)}")
    
    raw_results = nlp(text)
    processed_entities = clean_and_process_entities(raw_results, text)
    masked_result = mask_text(text, processed_entities)
    
    print("-" * 30)
    print(f"Masked Result: {masked_result}")
    print("Detected Entities:")
    for e in processed_entities:
        print(f" - {e['word']} | {e['numbered_tag']} ({e['score']:.1%})")
    print("=" * 60)