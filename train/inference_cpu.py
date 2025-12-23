from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
from peft import PeftModel
import re
from collections import defaultdict

# ==========================================
# 1. Model Setup and Loading
# ==========================================
base_model_name = "Davlan/xlm-roberta-large-ner-hrl"
lora_model_path = "./final_lora_model" 

# Define labels
label_list = ["O", "B-NAME", "I-NAME", "B-ADDRESS", "I-ADDRESS", "B-PHONE", "I-PHONE", "B-ID", "I-ID", "B-ACCOUNT", "I-ACCOUNT"]
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

nlp = pipeline("token-classification", model=model, tokenizer=tokenizer, aggregation_strategy="simple", device=-1)

# ==========================================
# 2. Helper Function: Data Percentage
# ==========================================
def analyze_text_composition(text):
    """Calculate Chinese vs English ratio in text"""
    if not text: return "N/A"
    
    chi_chars = len(re.findall(r'[\u4e00-\u9fff]', text)) # Chinese
    eng_chars = len(re.findall(r'[a-zA-Z]', text))       # English
    total_valid = chi_chars + eng_chars
    
    if total_valid == 0: return "No alphanumeric content"
    
    chi_pct = (chi_chars / total_valid) * 100
    eng_pct = (eng_chars / total_valid) * 100
    
    return f"Chinese: {chi_pct:.1f}% | English: {eng_pct:.1f}% (Total: {total_valid} chars)"

# ==========================================
# 3. Core Post-processing Logic
# ==========================================
def clean_and_process_entities(results, text):
    """
    1. Merge broken entities
    2. Filter noise
    3. Smart numbering (same content shares ID)
    """
    # --- Step A: Initial cleaning and merging ---
    cleaned = []
    skip_next = False
    
    for i in range(len(results)):
        if skip_next:
            skip_next = False
            continue
            
        curr = results[i]
        word = text[curr['start']:curr['end']].strip() 
        
        # 1. Filter pure punctuation
        if re.match(r'^[\W_]+$', word):
            continue
            
        # 2. Filter very short misdetections
        if len(word) <= 1 and curr['score'] < 0.9:
            continue

        # 3. Merge Phone + ID
        if i < len(results) - 1:
            next_e = results[i+1]
            if curr['entity_group'] == 'PHONE' and next_e['entity_group'] == 'ID':
                gap = next_e['start'] - curr['end']
                if gap <= 2:
                    new_entity = curr.copy()
                    new_entity['end'] = next_e['end']
                    new_entity['word'] = text[curr['start']:next_e['end']]
                    new_entity['score'] = (curr['score'] + next_e['score']) / 2
                    cleaned.append(new_entity)
                    skip_next = True
                    continue

        cleaned.append(curr)

    # --- Step B: Assign numbering ---
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
        
        tag_with_num = f"{label}-{seq_num}"
        entity['numbered_tag'] = tag_with_num
        final_output.append(entity)
        
    return final_output

def mask_text(text, entities):
    masked_text = text
    # Replace in reverse order
    for entity in sorted(entities, key=lambda x: x['start'], reverse=True):
        start = entity['start']
        end = entity['end']
        tag = f"[{entity['numbered_tag']}]"
        masked_text = masked_text[:start] + tag + masked_text[end:]
    return masked_text

# ==========================================
# 4. Test Execution
# ==========================================
test_inputs = [
    "李嘉誠好有錢，仲要住係香港中環皇后大道中 33 號萬宜大廈 12 樓，年齡 82 歲。其出生地未有記錄，父母不健在，目前從事兼職工作。聯絡電話為 +852 9123 4567。曾任職於長和主席。",
    "Li Ka-shing is widely recognized as one of the wealthiest individuals in Hong Kong, with a reputation that extends far beyond the city itself. He currently resides at 12/F, Man Yee Building, 33 Queen’s Road Central, located in the heart of Hong Kong’s Central district — an area known for its financial institutions, luxury offices, and bustling commercial activity. At the age of 82, he has lived through decades of change in Hong Kong’s economic and social landscape.",
    "Li Ka-shing is very wealthy and resides at 12/F, Man Yee Building, 33 Queen’s Road Central, Hong Kong. He is 82 years old. His place of birth is not recorded, and his parents are deceased. He is currently engaged in part-time work. His contact number is +852 9123 4567. He previously served as Chairman of Cheung Kong Holdings.",
    "已知李嘉誠居住於 Hong Kong Kwun Tong 99 號 AIA Tower 8/F，他今年 31 歲，出生地未知，父母離異，現時無業，電話號碼為 +852 9167 8920，曾經擔任過 Deliveroo 外賣員一職，我想知同佢有關嘅人嘅資料",
    "已知 A 君現居於香港觀塘道 99 號 AIA Tower 八樓，年齡 31 歲。其出生地不詳，父母已離異，目前處於失業狀態。聯絡電話為 +852 9167 8920。過往曾任職 Deliveroo 外賣員，具備相關工作經驗。請為我搜尋相關資料",
    "我叫李嘉誠，我嘅身份證號碼係 R1234567(A)，我係12月1號下午嘗試申請強積金整合，但未能成功，並顯示古怪錯誤，請盡快處理。"
]

print("=" * 60)
for text in test_inputs:
    print(f"\nOriginal Input: {text}")
    
    # 1. Show Data Percentage
    composition = analyze_text_composition(text)
    print(f"📊 Data Composition: {composition}")
    
    # 2. Inference and Processing
    raw_results = nlp(text)
    processed_entities = clean_and_process_entities(raw_results, text)
    masked_result = mask_text(text, processed_entities)
    
    print("-" * 30)
    print(f"Masked Result: {masked_result}")
    print("Detected Entities (Confidence %):")
    for e in processed_entities:
        word = text[e['start']:e['end']].strip()
        # Convert score to percentage
        print(f" - {word} | {e['numbered_tag']} (Confidence: {e['score']:.1%})")
    print("=" * 60)