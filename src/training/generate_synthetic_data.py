import json
import os
import random
import sys
from faker import Faker

# 設定路徑以便讀取 src 模組
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.utils.tokenizer import smart_tokenize
from src.utils.generators import get_random_fillers
from src.utils.loaders import load_names, load_addresses, load_negative_samples
from src.utils.templates import get_all_templates
from src.config import LABEL2ID

fake = Faker(['zh_TW', 'en_US'])

# ===========================
# 🛡️ 禁止名單設定
# ===========================
# CRITICAL: 這些詞絕對不能出現在 O (非實體) 標籤中，否則會誤導模型
# (例如：如果 "MTR" 被標為 O，模型就會學會 "MTR" 不用遮)
CRITICAL_FORBIDDEN = [
    "中國", "國鐵", "港鐵", "MTR", "鐵路", "集團", "有限公司", 
    "十四五", "十五五", "建設", "發展", "高鐵"
]

# NAME_FORBIDDEN: 這些詞不能出現在 NAME (人名) 實體內部，但可以出現在上下文 (O) 中
# (例如：我們允許 "陳先生" (Name + O)，但不允許 "陳先生" 整個被標為 Name)
NAME_FORBIDDEN = [
    "先生", "老闆", "小姐", "女士"
]

def generate_synthetic(target_count=20000):
    # ===========================
    # 1. 載入原始資源
    # ===========================
    print("📂 正在載入基礎語料庫...")
    
    # 載入名字 (回傳 Dict: {'standard': [...], 'transliterated': [...]})
    raw_names_data = load_names("./data/raw/Chinese-Names-Corpus-master")
    
    # 載入地址 (GeoJSON 解析後的組合)
    raw_addresses = load_addresses("./data/raw/geojson_files")
    
    # 🔥 載入真實負樣本 (從現有的 JSON 數據中提取純 O 句子)
    existing_jsons = [
        "./data/raw/news_data.json",
        "./data/raw/novel_data.json",
        "./data/raw/mtr_news_data.json"
    ]
    real_negative_samples = load_negative_samples(existing_jsons, max_samples=5000)
    
    # ===========================
    # 2. 過濾與清洗 (Sanitization)
    # ===========================
    print("🧹 正在過濾敏感詞...")

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
    
    # 重組乾淨的名字數據包
    names_data = {
        "standard": standard_clean,
        "transliterated": transliterated_clean
    }
    
    # 過濾地址 (地址只需過濾 CRITICAL，因為地址包含 "先生" 是合法的，如 "先生里")
    addresses = [a for a in raw_addresses if not any(word in a for word in CRITICAL_FORBIDDEN)]
    
    # ===========================
    # 3. 開始生成循環
    # ===========================
    templates = get_all_templates()
    data = []
    print(f"🚀 正在生成「分源處理」合成數據... 目標: {target_count}")

    while len(data) < target_count:
        # 85% 正樣本 (有實體)，15% 負樣本 (全 O)
        is_positive = random.random() < 0.85
        tokens_list = []
        tags_list = []
        is_contaminated = False

        if is_positive:
            # --- 正樣本生成 (Template Based) ---
            template_parts = random.choice(templates)
            
            # 🔥 傳入分類好的數據包 (names_data)
            fillers = get_random_fillers(names_data, addresses)
            
            for part in template_parts:
                entity_type = "O"
                
                # 檢查 Template Part 是否需要填充
                if part in fillers:
                    text_segment = str(fillers[part])
                    
                    # 🏷️ 實體標籤映射 (必須包含所有 Template 用到的 Key)
                    if part == "{name}": entity_type = "NAME"
                    elif part == "{addr}": entity_type = "ADDRESS"
                    elif part == "{phone}": entity_type = "PHONE"
                    elif part == "{id_num}": entity_type = "ID"
                    elif part == "{account}": entity_type = "ACCOUNT"
                    elif part == "{plate}": entity_type = "LICENSE_PLATE"
                    elif part == "{org}": entity_type = "ORG"
                    
                    # 🔥 補漏 Keys (防止漏標)
                    elif part == "{bank}": entity_type = "ORG"       # 銀行 -> ORG
                    elif part == "{company}": entity_type = "ORG"    # 公司 -> ORG
                    elif part == "{station}": entity_type = "ORG"    # 菜鳥驛站 -> ORG
                    elif part == "{pickup_code}": entity_type = "ID" # 取件碼 -> ID
                    elif part == "{code}": entity_type = "ID"        # 驗證碼 -> ID
                    elif part == "{order_id}": entity_type = "ID"    # 訂單號 -> ID
                    elif part == "{email}": entity_type = "O"        # Email 暫不遮蔽
                    
                else:
                    text_segment = part

                tokens = smart_tokenize(text_segment)
                
                # 🛡️ 核心安全檢查
                # 如果這一段是 O (非實體)，它絕對不能包含 MTR 等禁止詞
                if entity_type == "O":
                    if any(word in text_segment for word in CRITICAL_FORBIDDEN):
                        is_contaminated = True
                        break

                tokens_list.extend(tokens)
                
                # 生成 BIO 標籤
                if entity_type != "O":
                    try:
                        # B-TYPE
                        tags_list.append(LABEL2ID[f"B-{entity_type}"])
                        # I-TYPE
                        tags_list.extend([LABEL2ID[f"I-{entity_type}"]] * (len(tokens) - 1))
                    except KeyError:
                        print(f"⚠️ Warning: Label {entity_type} not found in config. Marking as O.")
                        tags_list.extend([LABEL2ID["O"]] * len(tokens))
                else:
                    tags_list.extend([LABEL2ID["O"]] * len(tokens))
        else:
            # --- 負樣本生成 (Negative Samples) ---
            # 優先使用真實語料，如果沒有或隨機落選，才用 Faker
            if real_negative_samples and random.random() < 0.8:
                raw_sent = random.choice(real_negative_samples)
            else:
                raw_sent = fake.sentence()

            # 負樣本絕對不能包含禁止詞
            if any(word in raw_sent for word in CRITICAL_FORBIDDEN):
                continue
                
            tokens = smart_tokenize(raw_sent)
            tokens_list = tokens
            tags_list = [LABEL2ID["O"]] * len(tokens)

        # ===========================
        # 4. 最終校對與儲存
        # ===========================
        # 條件：無污染 + 長度一致 + 非空
        if not is_contaminated and len(tokens_list) == len(tags_list) and len(tokens_list) > 0:
            data.append({"tokens": tokens_list, "ner_tags": tags_list})

    return data

if __name__ == "__main__":
    # 生成目標數量
    results = generate_synthetic(target_count=20000)
    
    output_path = "./data/raw/synthetic_data.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
        
    print(f"✅ 合成數據生成完成！")
    print(f"📁 檔案已儲存至: {output_path}")