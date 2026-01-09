# src/training/generate_synthetic_data.py
import json
import os
import random
import sys
from faker import Faker

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(project_root)

from src.utils.tokenizer import smart_tokenize
from src.utils.generators import get_random_fillers
from src.utils.loaders import load_names, load_addresses
from src.utils.templates import get_all_templates
from src.config import LABEL2ID

fake = Faker(['zh_TW', 'en_US'])

# 禁止名單
CRITICAL_FORBIDDEN = ["中國", "國鐵", "港鐵", "MTR", "鐵路", "集團", "有限公司", "十四五", "十五五", "建設", "發展", "高鐵"]
NAME_FORBIDDEN = ["先生", "老闆", "小姐", "女士"]

def generate_synthetic(target_count=20000):
    # 1. 載入原始資源 (現在 raw_names 是一個 Dict)
    raw_names_data = load_names("./data/raw/Chinese-Names-Corpus-master")
    raw_addresses = load_addresses("./data/raw/geojson_files") # 注意路徑可能要調整，視乎你執行位置
    
    # 🛡️ 分別過濾兩個名單
    # 過濾標準名 (Chinese/Ancient...)
    standard_clean = [
        n for n in raw_names_data["standard"] 
        if not any(word in n for word in CRITICAL_FORBIDDEN + NAME_FORBIDDEN)
    ]
    # 過濾譯名 (English_Cn...)
    transliterated_clean = [
        n for n in raw_names_data["transliterated"] 
        if not any(word in n for word in CRITICAL_FORBIDDEN + NAME_FORBIDDEN)
    ]
    
    # 重組乾淨的數據包
    names_data = {
        "standard": standard_clean,
        "transliterated": transliterated_clean
    }
    
    # 過濾地址
    addresses = [a for a in raw_addresses if not any(word in a for word in CRITICAL_FORBIDDEN)]
    
    templates = get_all_templates()
    data = []
    print(f"🚀 正在生成「分源處理」合成數據... 目標: {target_count}")

    while len(data) < target_count:
        is_positive = random.random() < 0.85
        tokens_list = []
        tags_list = []
        is_contaminated = False

        if is_positive:
            template_parts = random.choice(templates)
            
            # 🔥 傳入分類好的數據包
            fillers = get_random_fillers(names_data, addresses)
            
            for part in template_parts:
                entity_type = "O"
                if part in fillers:
                    text_segment = str(fillers[part])
                    
                    if part == "{name}": entity_type = "NAME"
                    elif part == "{addr}": entity_type = "ADDRESS"
                    elif part == "{phone}": entity_type = "PHONE"
                    elif part == "{id_num}": entity_type = "ID"
                    elif part == "{account}": entity_type = "ACCOUNT"
                    elif part == "{plate}": entity_type = "LICENSE_PLATE"
                    elif part == "{org}": entity_type = "ORG"
                    # 補漏 keys
                    elif part == "{bank}": entity_type = "ORG"
                    elif part == "{company}": entity_type = "ORG"
                    elif part == "{station}": entity_type = "ORG"
                    elif part == "{pickup_code}": entity_type = "ID"
                    elif part == "{code}": entity_type = "ID"
                    elif part == "{order_id}": entity_type = "ID"
                    elif part == "{email}": entity_type = "O"
                else:
                    text_segment = part

                tokens = smart_tokenize(text_segment)
                
                # 核心安全檢查
                if entity_type == "O":
                    if any(word in text_segment for word in CRITICAL_FORBIDDEN):
                        is_contaminated = True
                        break

                tokens_list.extend(tokens)
                if entity_type != "O":
                    try:
                        tags_list.append(LABEL2ID[f"B-{entity_type}"])
                        tags_list.extend([LABEL2ID[f"I-{entity_type}"]] * (len(tokens) - 1))
                    except KeyError:
                        tags_list.extend([LABEL2ID["O"]] * len(tokens))
                else:
                    tags_list.extend([LABEL2ID["O"]] * len(tokens))
        else:
            # 負樣本
            raw_sent = fake.sentence()
            if any(word in raw_sent for word in CRITICAL_FORBIDDEN):
                continue
            tokens = smart_tokenize(raw_sent)
            tokens_list = tokens
            tags_list = [LABEL2ID["O"]] * len(tokens)

        if not is_contaminated and len(tokens_list) == len(tags_list) and len(tokens_list) > 0:
            data.append({"tokens": tokens_list, "ner_tags": tags_list})

    return data

if __name__ == "__main__":
    results = generate_synthetic(target_count=20000)
    output_path = "./data/raw/synthetic_data.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"✅ 完成！檔案已儲存至: {output_path}")