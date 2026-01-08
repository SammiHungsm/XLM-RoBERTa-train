from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
from peft import PeftModel
import re
from collections import defaultdict
import torch

# ==========================================
# 1. Model Setup and Loading
# ==========================================
base_model_name = "Davlan/xlm-roberta-large-ner-hrl"
lora_model_path = "./final_lora_model" 

# 必須與 prepare_data.py 一致 (15 個標籤)
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
    print("提示：如果報錯 Size Mismatch，請確認你是否已經刪除舊的 output 資料夾並重新訓練。")
    exit()

# ✅ CPU version: device=-1
nlp = pipeline(
    "token-classification",
    model=model,
    tokenizer=tokenizer,
    aggregation_strategy="simple",
    device=-1
)

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
    cleaned = []
    skip_next = False
    
    blacklist = ["健在", "不詳", "未知", "無業", "離異", "單身", "不便", "整合", "處理", "錯誤"]

    for i in range(len(results)):
        if skip_next:
            skip_next = False
            continue
            
        curr = results[i]
        if curr['end'] > len(text): curr['end'] = len(text)
        
        numeric_labels = ['PHONE', 'ID', 'ACCOUNT', 'HKID', 'LICENSE_PLATE']
        if curr['entity_group'] in numeric_labels:
            while curr['start'] > 0 and text[curr['start'] - 1] in "0123456789()+- ":
                curr['start'] -= 1
            while curr['end'] < len(text) and text[curr['end']] in "0123456789()ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                curr['end'] += 1
            curr['word'] = text[curr['start']:curr['end']]
        
        word = text[curr['start']:curr['end']].strip()
        
        if word in blacklist:
            continue

        if curr['entity_group'] == 'NAME' and len(word) == 1 and not re.match(r'[a-zA-Z]', word):
            if curr['score'] < 0.995:
                continue

        if re.match(r'^[\W_]+$', word):
            continue

        if i < len(results) - 1:
            next_e = results[i+1]
            gap_text = text[curr['end']:next_e['start']]
            
            if re.match(r'^[\s-]*$', gap_text): 
                if curr['entity_group'] == 'PHONE' and next_e['entity_group'] == 'ID':
                    new_entity = curr.copy()
                    new_entity['end'] = next_e['end']
                    new_entity['word'] = text[curr['start']:next_e['end']]
                    new_entity['score'] = (curr['score'] + next_e['score']) / 2
                    cleaned.append(new_entity)
                    skip_next = True
                    continue
                
                if curr['entity_group'] == next_e['entity_group']:
                    new_entity = curr.copy()
                    new_entity['end'] = next_e['end']
                    new_entity['word'] = text[curr['start']:next_e['end']]
                    new_entity['score'] = (curr['score'] + next_e['score']) / 2
                    cleaned.append(new_entity)
                    skip_next = True
                    continue

        cleaned.append(curr)

    cleaned.sort(key=lambda x: x['start'])
    final_output = []
    counters = defaultdict(int)
    entity_registry = {} 
    
    for entity in cleaned:
        label = entity['entity_group']
        word_content = text[entity['start']:entity['end']].strip()
        dict_key = (label, word_content)
        
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

# ==========================================
# 3. Test Inputs
# ==========================================
test_inputs = [
    "李嘉誠好有錢，仲要住係香港中環皇后大道中 33 號萬宜大廈 12 樓，年齡 82 歲。其出生地未有記錄，父母不健在，目前從事兼職工作。聯絡電話為 +852 9123 4567。曾任職於長和主席。",
    "Li Ka-shing is widely recognized as one of the wealthiest individuals in Hong Kong, with a reputation that extends far beyond the city itself. He currently resides at 12/F, Man Yee Building, 33 Queen’s Road Central. At the age of 82.",
    "Li Ka-shing is very wealthy and resides at 12/F, Man Yee Building, 33 Queen’s Road Central, Hong Kong. His contact number is +852 9123 4567. He previously served as Chairman of Cheung Kong Holdings.",
    "已知李嘉誠居住於 Hong Kong Kwun Tong 99 號 AIA Tower 8/F，他今年 31 歲，電話號碼為 +852 9167 8920，曾經擔任過 Deliveroo 外賣員一職，我想知同佢有關嘅人嘅資料",
    "已知 A 君現居於香港觀塘道 99 號 AIA Tower 八樓，年齡 31 歲。聯絡電話為 +852 9167 8920。過往曾任職 Deliveroo 外賣員，具備相關工作經驗。請為我搜尋相關資料",
    "我叫李嘉誠，我嘅身份證號碼係 R1234567(A)，我係12月1號下午嘗試申請強積金整合，但未能成功，並顯示古怪錯誤，請盡快處理。",
    "你好，我係 Sammi。我住係 Tuen Mun 屯門市廣場 10 樓。",
    "我的電話係 9123 4567。身分證 A123456(7)。",
    "Sammi 之前打過黎。",
    "Edmond梁，身高185cm，居住於香港觀塘 AIA Tower 31樓，Bank Account = 274542182882現任Alibaba CEO，電話為 21678080，身份證號為 R98272829。"
]

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
        print(f" - {text[e['start']:e['end']]} | {e['numbered_tag']} ({e['score']:.1%})")
    print("=" * 60)