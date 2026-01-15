# src/utils/loaders.py
import json
import os
import random
import re
from pathlib import Path

# ✅ 1. 引入中央配置，不再 Hardcode
from src.config import BASE_FORBIDDEN
from src.utils.templates import ALL_HK_ORGS

# ✅ 2. 動態構建終極禁止名單
# 這樣地址載入器 (load_addresses) 和負樣本提取器 (load_negative_samples)
# 就會自動過濾掉 "HSBC", "7-11" 等機構名，防止將它們誤當成普通地址或無實體文本。
STRICT_FORBIDDEN = set(BASE_FORBIDDEN) | set(ALL_HK_ORGS)

def load_names(corpus_folder):
    """
    分類載入名字：
    - transliterated: 來自 English_Cn_Name_Corpus (適合組合)
    - standard: 來自其他 Corpus (適合直接用)
    """
    data = {
        "transliterated": [], # 存放 English_Cn_Name_Corpus
        "standard": []        # 存放其他 (Chinese, Japanese, Ancient...)
    }
    
    folder_path = Path(corpus_folder)
    # 預設值 (防止讀取失敗)
    default_data = {
        "transliterated": ["阿諾", "史泰龍", "伊隆", "馬斯克"],
        "standard": ["陳大文", "李嘉誠", "田中太郎"]
    }
    
    if not folder_path.exists():
        print(f"⚠️ 找不到名字資料夾: {corpus_folder}")
        return default_data
        
    txt_files = list(folder_path.glob("*.txt"))
    if not txt_files:
        return default_data

    print(f"📂 正在分類載入名字 (來源: {len(txt_files)} 個檔案)...")
    
    for file_path in txt_files:
        file_count = 0
        # 判斷是否為「英漢譯名庫」
        is_transliterated = "English_Cn_Name_Corpus" in file_path.name
        target_list = data["transliterated"] if is_transliterated else data["standard"]
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    name = line.strip()
                    if name: 
                        target_list.append(name)
                        file_count += 1
            
            category = "譯名(可組合)" if is_transliterated else "標準名(直接用)"
            print(f"  - {file_path.name} ({category}): 讀取 {file_count} 個")
        except Exception as e:
            print(f"  ❌ 讀取 {file_path.name} 失敗: {e}")
    
    # 去重
    data["transliterated"] = list(set(data["transliterated"]))
    data["standard"] = list(set(data["standard"]))
    
    print(f"✅ 名字載入完成！標準名: {len(data['standard'])}, 譯名: {len(data['transliterated'])}")
    
    # 確保不為空
    if not data["standard"]: data["standard"] = default_data["standard"]
    if not data["transliterated"]: data["transliterated"] = default_data["transliterated"]
    
    return data

def parse_one_feature(feature):
    """
    從 GeoJSON feature 解析出多種地址組合 (中文 & 英文, 完整 & 局部)
    這樣可以確保模型學會 Mask "中西區", "必列者士街", 以及 "中西區必列者士街58號" 等不同粒度的地址。
    """
    props = feature.get("properties", {})
    # 兼容兩種常見 GeoJSON 結構
    if "Address" in props:
        root = props.get("Address", {}).get("PremisesAddress", {})
    else:
        root = props # Fallback

    if not root:
        return []

    combos = set()

    # ===========================
    # 1. 中文地址解析 (Chinese)
    # ===========================
    chi_root = root.get("ChiPremisesAddress", {})
    
    # 提取部件 (Components)
    c_region = chi_root.get("Region", "").strip()
    
    # District (有時是 string, 有時是 object)
    c_dist_val = chi_root.get("ChiDistrict", "")
    c_district = c_dist_val if isinstance(c_dist_val, str) else c_dist_val.get("ChiDistrict", "")
    
    # Street & No
    c_street_obj = chi_root.get("ChiStreet", {})
    c_street_name = c_street_obj.get("StreetName", "").strip()
    c_bldg_no = c_street_obj.get("BuildingNoFrom", "").strip()
    # 組合：街名 + 號碼 (如：必列者士街58號)
    c_street_full = f"{c_street_name}{c_bldg_no}號" if (c_street_name and c_bldg_no) else c_street_name

    # Estate
    c_estate_obj = chi_root.get("ChiEstate", {})
    c_estate = c_estate_obj.get("EstateName", "").strip()

    # Building / Block (Optional)
    c_block_obj = chi_root.get("ChiBlock", {})
    c_block = c_block_obj.get("BlockNo", "").strip()
    c_bldg_obj = chi_root.get("ChiBuilding", {})
    c_bldg = c_bldg_obj.get("BuildingName", "").strip()
    
    # --- 生成中文組合 (Combinations) ---
    parts_list = [c_region, c_district, c_street_full, c_estate, c_bldg, c_block]
    valid_parts = [p for p in parts_list if p]
    
    # 1. 單個部件 (Parts) - 讓模型學會單獨 Mask 街名或屋苑名
    for p in valid_parts:
        combos.add(p)
        
    # 2. 地區組合 (Region + District)
    if c_region and c_district:
        combos.add(f"{c_region}{c_district}")
        
    # 3. 街道組合 (District + Street / Region + District + Street)
    if c_street_full:
        if c_district: combos.add(f"{c_district}{c_street_full}")
        if c_region and c_district: combos.add(f"{c_region}{c_district}{c_street_full}")
        
    # 4. 屋苑組合 (Street + Estate / District + Estate)
    if c_estate:
        if c_street_full: combos.add(f"{c_street_full}{c_estate}")
        if c_district: combos.add(f"{c_district}{c_estate}")
        if c_region and c_district: combos.add(f"{c_region}{c_district}{c_estate}")
        
    # 5. 完整地址 (Full Address) - 最長的一串
    full_chi = "".join(valid_parts) 
    if len(full_chi) > 4:
        combos.add(full_chi)


    # ===========================
    # 2. 英文地址解析 (English)
    # ===========================
    eng_root = root.get("EngPremisesAddress", {})
    
    e_region = eng_root.get("Region", "").strip()
    
    e_dist_val = eng_root.get("EngDistrict", "")
    e_district = e_dist_val if isinstance(e_dist_val, str) else e_dist_val.get("EngDistrict", "")
    
    e_street_obj = eng_root.get("EngStreet", {})
    e_street_name = e_street_obj.get("StreetName", "").strip()
    e_bldg_no = e_street_obj.get("BuildingNoFrom", "").strip()
    
    # English Street: "58 Bridges Street"
    if e_street_name and e_bldg_no:
        e_street_full = f"{e_bldg_no} {e_street_name}"
    else:
        e_street_full = e_street_name

    e_estate_obj = eng_root.get("EngEstate", {})
    e_estate = e_estate_obj.get("EstateName", "").strip()
    
    e_block_obj = eng_root.get("EngBlock", {})
    e_block = e_block_obj.get("BlockNo", "").strip()
    e_bldg_obj = eng_root.get("EngBuilding", {})
    e_bldg = e_bldg_obj.get("BuildingName", "").strip()

    # --- 生成英文組合 (Combinations) ---
    e_parts = [e_estate, e_block, e_bldg, e_street_full, e_district, e_region]
    e_valid_parts = [p for p in e_parts if p]

    # 1. Parts
    for p in e_valid_parts:
        combos.add(p)
        
    # 2. Pairs (Street, District)
    if e_street_full and e_district:
        combos.add(f"{e_street_full}, {e_district}")
        
    # 3. Estate + Street
    if e_estate and e_street_full:
        combos.add(f"{e_estate}, {e_street_full}")
        
    # 4. Full Address (Standard Format)
    if len(e_valid_parts) > 1:
        combos.add(", ".join(e_valid_parts))

    return list(combos)

def load_addresses(geojson_folder):
    raw_addresses = []
    folder_path = Path(geojson_folder)
    
    if not folder_path.exists():
        print(f"⚠️ 找不到地址資料夾: {geojson_folder}")
        return ["香港中環", "九龍塘", "屯門市廣場"] # Fallback
    
    files = list(folder_path.glob("*.json")) + list(folder_path.glob("*.geojson"))
    print(f"📂 正在載入地址 (來源: {len(files)} 個 GeoJSON)...")
    
    for file_path in files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                features = data.get("features", [])
                
                # 從每個 feature 提取多個地址組合
                count = 0
                for feat in features:
                    variations = parse_one_feature(feat)
                    raw_addresses.extend(variations)
                    count += 1
                    
        except Exception as e:
            print(f"  ❌ 讀取 {file_path.name} 失敗: {e}")
            
    # 過濾與清洗
    cleaned_addresses = []
    unique_check = set()
    
    print(f"🔍 正在清洗 {len(raw_addresses)} 條原始地址變體...")
    
    for addr in raw_addresses:
        addr = addr.strip()
        # 1. 長度過濾 (太短通常不是有效地址)
        if len(addr) < 3: continue
        
        # 2. 禁止名單過濾 (完全匹配)
        # 🔥 這裡現在會自動過濾掉 "HSBC", "MTR" 等機構名
        if any(f == addr for f in STRICT_FORBIDDEN): continue
        
        # 3. 去重
        if addr not in unique_check:
            unique_check.add(addr)
            cleaned_addresses.append(addr)
            
    print(f"✅ 地址載入完成！共 {len(cleaned_addresses)} 條可用地址組合")
    return cleaned_addresses if cleaned_addresses else ["香港中環", "九龍塘"]

def load_negative_samples(json_paths, max_samples=10000):
    samples = []
    print(f"🛡️ 正在從現有數據庫提取「天然負樣本」...")
    
    for path_str in json_paths:
        path = Path(path_str)
        if not path.exists():
            print(f"  ⚠️ 跳過 (找不到檔案): {path}")
            continue
            
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
                # 兼容不同格式
                data_list = raw["data"] if isinstance(raw, dict) and "data" in raw else raw
                
                count = 0
                for item in data_list:
                    tokens = item.get("tokens", [])
                    tags = item.get("ner_tags", [])
                    
                    # 1. 確保長度一致
                    if len(tokens) != len(tags): continue
                    
                    # 2. 核心邏輯：只有當整句都是 'O' (0) 時，才算負樣本
                    # (假設 O 的 ID 是 0，這通常是慣例)
                    if all(t == 0 for t in tags):
                        # 還原成字串
                        sent = "".join(tokens)
                        
                        # 3. 再次檢查禁止詞 (雙重保險)
                        # 🔥 這裡現在會確保負樣本不包含 "支付寶" 或 "順豐" 等詞
                        if 5 < len(sent) < 150:
                            if not any(word in sent for word in STRICT_FORBIDDEN):
                                samples.append(sent)
                                count += 1
                                
                print(f"  - {path.name}: 提取了 {count} 條純淨句子")
                
        except Exception as e:
            print(f"  ❌ 讀取 {path} 失敗: {e}")

    # 隨機採樣，避免數據失衡
    if len(samples) > max_samples:
        print(f"  ✂️ 樣本過多，隨機選取 {max_samples} 條...")
        samples = random.sample(samples, max_samples)
        
    print(f"✅ 負樣本準備完成！共 {len(samples)} 條")
    return samples