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
from src.utils.loaders import load_names, load_addresses, load_negative_samples
from src.utils.templates import get_all_templates
from src.config import LABEL2ID

fake = Faker(['zh_TW', 'en_US'])

# 🔥 終極「零錯誤」禁止名單：任何標記為 "O" 的 Token 如果包含這些字，該條數據即刻廢棄
STRICT_FORBIDDEN = [
    "中國", "國鐵", "港鐵", "MTR", "鐵路", "集團", "有限公司", 
    "十四五", "十五五", "建設", "發展", "高鐵", "先生", "老闆", "小姐", "女士"
]

def generate_synthetic(target_count=20000):
    # 1. 載入原始資源
    raw_names = load_names("./Chinese-Names-Corpus-master")
    raw_addresses = load_addresses("./geojson_files")
    
    # 🛡️ 檢查 get_random_fillers 的輸入：確保傳入的名單不包含禁止詞
    # 這樣可以防止例如「中國人」被當成 NAME 標記，或者「中國」被當成地址傳入後因規則衝突被廢棄
    names = [n for n in raw_names if not any(word in n for word in STRICT_FORBIDDEN)]
    addresses = [a for a in raw_addresses if not any(word in a for word in STRICT_FORBIDDEN)]
    
    # 🔥 斷絕危險來源：強制變空，不讀取任何可能含有實體但標記為 0 的原文檔案
    neg_texts = [] 
    
    templates = get_all_templates()

    data = []
    print(f"🚀 正在生成「零污染」合成數據... 目標: {target_count}")

    while len(data) < target_count:
        is_positive = random.random() < 0.85
        tokens_list = []
        tags_list = []
        is_contaminated = False

        if is_positive:
            template_parts = random.choice(templates)
            fillers = get_random_fillers(names, addresses)
            
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
                else:
                    text_segment = part

                tokens = smart_tokenize(text_segment)
                
                # 🔥 核心安全檢查：如果是 O (固定文本)，內容絕對不能包含禁止詞
                if entity_type == "O":
                    if any(word in text_segment for word in STRICT_FORBIDDEN):
                        is_contaminated = True
                        break

                tokens_list.extend(tokens)
                if entity_type != "O":
                    tags_list.append(LABEL2ID[f"B-{entity_type}"])
                    tags_list.extend([LABEL2ID[f"I-{entity_type}"]] * (len(tokens) - 1))
                else:
                    tags_list.extend([LABEL2ID["O"]] * len(tokens))
        else:
            # 🛡️ 負樣本生成：由於 neg_texts 為空，這裡只會行 fake.sentence()
            # Faker 生成的英文/中文句子同樣要過濾禁止詞，確保 100% 安全
            raw_sent = fake.sentence()
            if any(word in raw_sent for word in STRICT_FORBIDDEN):
                continue
                
            tokens = smart_tokenize(raw_sent)
            tokens_list = tokens
            tags_list = [LABEL2ID["O"]] * len(tokens)

        # 最終校對：只有完全沒被污染且長度匹配的數據才被採納
        if not is_contaminated and len(tokens_list) == len(tags_list) and len(tokens_list) > 0:
            data.append({"tokens": tokens_list, "ner_tags": tags_list})

    return data

if __name__ == "__main__":
    # 生成 2 萬條純淨數據
    results = generate_synthetic(target_count=20000)
    
    output_path = "./data/raw/synthetic_data.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
        
    print(f"✅ 「零錯誤」合成數據生成完成。")
    print(f"📁 檔案已儲存至: {output_path}")