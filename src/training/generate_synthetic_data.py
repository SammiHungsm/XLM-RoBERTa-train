import json
import os
import random
import sys
from tqdm import tqdm # 加個進度條比較好看
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
# 🛡️ 禁止名單設定 (保留您的設定)
# ===========================
CRITICAL_FORBIDDEN = [
    "中國", "國鐵", "港鐵", "MTR", "鐵路", "集團", "有限公司", 
    "十四五", "十五五", "建設", "發展", "高鐵", "銀行", "分行" # 加入銀行相關
]

NAME_FORBIDDEN = [
    "先生", "老闆", "小姐", "女士"
]

def generate_synthetic(target_count=20000):
    # ===========================
    # 1. 載入原始資源
    # ===========================
    print("📂 正在載入基礎語料庫...")
    
    # 載入名字
    raw_names_data = load_names("./data/raw/Chinese-Names-Corpus-master")
    
    # 載入地址 (GeoJSON)
    # 💡 註：銀行地址 (Excel) 已經整合在 generators.py 內部，這裡載入的是隨機路名
    raw_addresses = load_addresses("./data/raw/geojson_files")
    
    # 載入真實負樣本
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

    standard_clean = [
        n for n in raw_names_data["standard"] 
        if not any(word in n for word in CRITICAL_FORBIDDEN + NAME_FORBIDDEN)
    ]
    
    transliterated_clean = [
        n for n in raw_names_data["transliterated"] 
        if not any(word in n for word in CRITICAL_FORBIDDEN + NAME_FORBIDDEN)
    ]
    
    names_data = {
        "standard": standard_clean,
        "transliterated": transliterated_clean
    }
    
    addresses = [a for a in raw_addresses if not any(word in a for word in CRITICAL_FORBIDDEN)]
    
    # ===========================
    # 3. 開始生成循環
    # ===========================
    # 這裡會自動包含 Excel 載入的銀行相關 Templates
    templates = get_all_templates() 
    
    data = []
    print(f"🚀 正在生成「分源處理」合成數據... 目標: {target_count}")

    # 使用 tqdm 顯示進度
    with tqdm(total=target_count) as pbar:
        while len(data) < target_count:
            # 85% 正樣本 (有實體)，15% 負樣本 (全 O)
            is_positive = random.random() < 0.85
            tokens_list = []
            tags_list = []
            is_contaminated = False

            if is_positive:
                # --- 正樣本生成 (Template Based) ---
                template_parts = random.choice(templates)
                
                # 🔥 這裡會自動混合 GeoJSON 地址 和 Excel 銀行地址
                fillers = get_random_fillers(names_data, addresses)
                
                for part in template_parts:
                    entity_type = "O"
                    
                    # 檢查 Template Part 是否需要填充
                    if part in fillers:
                        text_segment = str(fillers[part])
                        
                        # 🏷️ 實體標籤映射
                        if part == "{name}": entity_type = "NAME"
                        elif part == "{addr}": entity_type = "ADDRESS"
                        elif part == "{phone}": entity_type = "PHONE"
                        elif part == "{id_num}": entity_type = "ID"
                        elif part == "{account}": entity_type = "ACCOUNT"
                        elif part == "{plate}": entity_type = "LICENSE_PLATE"
                        elif part == "{org}": entity_type = "ORG"
                        
                        # 🔥 補漏 Keys (包含銀行相關)
                        elif part == "{bank}": entity_type = "ORG"       # 銀行 -> ORG
                        elif part == "{company}": entity_type = "ORG"    # 公司 -> ORG
                        elif part == "{station}": entity_type = "ORG"    # 菜鳥驛站 -> ORG
                        elif part == "{pickup_code}": entity_type = "O" 
                        elif part == "{code}": entity_type = "O"        
                        elif part == "{order_id}": entity_type = "O"    
                        elif part == "{email}": entity_type = "O"        
                        
                    else:
                        text_segment = part

                    tokens = smart_tokenize(text_segment)
                    
                    # 🛡️ 核心安全檢查
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
                            # Fallback
                            tags_list.extend([LABEL2ID["O"]] * len(tokens))
                    else:
                        tags_list.extend([LABEL2ID["O"]] * len(tokens))
            else:
                # --- 負樣本生成 ---
                if real_negative_samples and random.random() < 0.8:
                    raw_sent = random.choice(real_negative_samples)
                else:
                    raw_sent = fake.sentence()

                if any(word in raw_sent for word in CRITICAL_FORBIDDEN):
                    continue
                    
                tokens = smart_tokenize(raw_sent)
                tokens_list = tokens
                tags_list = [LABEL2ID["O"]] * len(tokens)

            # ===========================
            # 4. 最終校對與儲存
            # ===========================
            if not is_contaminated and len(tokens_list) == len(tags_list) and len(tokens_list) > 0:
                data.append({"tokens": tokens_list, "ner_tags": tags_list})
                pbar.update(1) # 更新進度條

    return data

if __name__ == "__main__":
    # 生成目標數量
    # 建議生成多一點，因為使用了真實銀行數據，多樣性很高
    target = 20000 
    results = generate_synthetic(target_count=target)
    
    # 注意：這裡直接輸出 train_data_lora.json，因為我們已經包含了 tags
    # 這樣就可以跳過 prepare_data.py 的標註步驟，直接進入 clean/train
    output_path = "train_data_lora.json"
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
        
    print(f"✅ 合成數據生成完成！(已包含 BIO 標籤)")
    print(f"📁 檔案已儲存至: {output_path}")
    print("🚀 您可以跳過 prepare_data.py，直接執行 'clean_and_augment.py'！")