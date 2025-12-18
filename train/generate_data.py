import json
import glob
import os
import random
from faker import Faker
from transformers import XLMRobertaTokenizerFast

# --- 設定 ---
GEOJSON_FOLDER = './geojson_files'
OUTPUT_FILE = 'pii_dataset_final.json'
NUM_SAMPLES = 20000  # 總共生成的訓練數據量

# 初始化
fake = Faker(['zh_TW', 'en_US'])
tokenizer = XLMRobertaTokenizerFast.from_pretrained("xlm-roberta-base")

# 定義標籤 ID
# O=0, B-NAME=1, I-NAME=2, B-HKID=3, I-HKID=4, B-ADDRESS=5, I-ADDRESS=6
LABEL_MAP = {
    "O": 0,
    "B-NAME": 1, "I-NAME": 2,
    "B-HKID": 3, "I-HKID": 4,
    "B-ADDRESS": 5, "I-ADDRESS": 6
}

# ==========================================
# 1. GeoJSON 地址提取模組
# ==========================================
def parse_single_feature(feature):
    try:
        props = feature.get('properties', {})
        # 嘗試進入深層結構
        address_root = props.get('Address', {}).get('PremisesAddress', {})
        
        # 如果第一層找不到，嘗試直接在 properties 找 (適應不同版本)
        if not address_root:
            if 'EngPremisesAddress' in props: address_root = props
            else: return []

        extracted = []
        
        # 處理英文
        eng_node = address_root.get('EngPremisesAddress')
        if eng_node and isinstance(eng_node, dict):
            region = eng_node.get('Region', '')
            district = eng_node.get('EngDistrict', {}).get('DistrictName', '') if isinstance(eng_node.get('EngDistrict'), dict) else eng_node.get('EngDistrict', '')
            
            # 村屋格式
            if 'EngVillage' in eng_node:
                v_info = eng_node['EngVillage']
                full = f"{v_info.get('BuildingNoFrom','')} {v_info.get('VillageName','')}, {district}, {region}"
                extracted.append(full)
            # 街道格式
            elif 'EngStreet' in eng_node:
                s_info = eng_node['EngStreet']
                full = f"{s_info.get('BuildingNoFrom','')} {s_info.get('StreetName','')}, {district}, {region}"
                extracted.append(full)

        # 處理中文
        chi_node = address_root.get('ChiPremisesAddress')
        if chi_node and isinstance(chi_node, dict):
            region = chi_node.get('Region', '')
            district = chi_node.get('ChiDistrict', {}).get('ChiDistrictName', '') if isinstance(chi_node.get('ChiDistrict'), dict) else chi_node.get('ChiDistrict', '')
            
            if 'ChiVillage' in chi_node:
                v_info = chi_node['ChiVillage']
                full = f"{region}{district}{v_info.get('VillageName','')}{v_info.get('BuildingNoFrom','')}號"
                extracted.append(full)
            elif 'ChiStreet' in chi_node:
                s_info = chi_node['ChiStreet']
                full = f"{region}{district}{s_info.get('StreetName','')}{s_info.get('BuildingNoFrom','')}號"
                extracted.append(full)
                
        return extracted
    except Exception:
        return []

def load_real_addresses():
    print(f"正在掃描 {GEOJSON_FOLDER}...")
    files = glob.glob(os.path.join(GEOJSON_FOLDER, "*.json")) + glob.glob(os.path.join(GEOJSON_FOLDER, "*.geojson"))
    all_addr = []
    for f_path in files:
        try:
            with open(f_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for feat in data.get('features', []):
                    all_addr.extend(parse_single_feature(feat))
        except Exception as e:
            print(f"跳過檔案 {f_path}: {e}")
            
    unique_pool = list(set(all_addr))
    print(f"共提取 {len(unique_pool)} 條真實地址。")
    return unique_pool if unique_pool else ["香港中環皇后大道中100號"] # Fallback

# ==========================================
# 2. 數據集生成模組 (混合 PII)
# ==========================================
def create_dataset():
    address_pool = load_real_addresses()
    dataset = []
    
    templates = [
        ("請確認", "的資料。"), ("客戶", "申請已批准。"), ("Send to ", " immediately."),
        ("地址：", ""), ("Name: ", ", ID: ..."), ("我的電話是...", "，住址是...")
    ]

    print(f"正在生成 {NUM_SAMPLES} 條訓練數據...")

    for _ in range(NUM_SAMPLES):
        # 隨機決定生成哪種 PII
        pii_type = random.choice(['ADDRESS', 'NAME', 'HKID'])
        
        if pii_type == 'ADDRESS':
            target_text = random.choice(address_pool)
            label_b = LABEL_MAP["B-ADDRESS"]
            label_i = LABEL_MAP["I-ADDRESS"]
        elif pii_type == 'NAME':
            target_text = fake.name()
            label_b = LABEL_MAP["B-NAME"]
            label_i = LABEL_MAP["I-NAME"]
        else:
            target_text = f"{random.choice('A-Z')}{random.randint(100000,999999)}({random.randint(0,9)})"
            label_b = LABEL_MAP["B-HKID"]
            label_i = LABEL_MAP["I-HKID"]

        # 隨機選前後文
        prefix, suffix = random.choice(templates)
        
        # Tokenize (核心：對齊 Token 與 Label)
        tokens_prefix = tokenizer.tokenize(prefix)
        tokens_target = tokenizer.tokenize(target_text)
        tokens_suffix = tokenizer.tokenize(suffix)
        
        if not tokens_target: continue

        full_tokens = tokens_prefix + tokens_target + tokens_suffix
        input_ids = tokenizer.convert_tokens_to_ids(full_tokens)
        
        # 構建 Label List
        labels = [0] * len(tokens_prefix)
        labels.append(label_b) # 第一個字是 B
        labels.extend([label_i] * (len(tokens_target) - 1)) # 剩下是 I
        labels.extend([0] * len(tokens_suffix))
        
        dataset.append({
            "input_ids": input_ids,
            "labels": labels,
            "attention_mask": [1] * len(input_ids)
        })

    with open(OUTPUT_FILE, "w") as f:
        json.dump(dataset, f)
    print(f"完成！數據已存至 {OUTPUT_FILE}")

if __name__ == "__main__":
    create_dataset()