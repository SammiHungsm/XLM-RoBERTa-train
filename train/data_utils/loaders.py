import os
import json
import random
import re
from pathlib import Path

def load_names(corpus_folder):
    """
    載入人名列表，支援 .txt 檔案
    """
    names = []
    folder_path = Path(corpus_folder)
    # 預設名單 (當找不到檔案時使用)
    default_names = ["陳大文", "李嘉誠", "黃小明", "張偉", "Alice", "Bob", "Sammi", "John", "Peter", "Mary", "Anson Lo", "姜濤"]
    
    # 過濾不適合作為人名的詞彙
    blacklist = {"先生", "小姐", "女士", "經理", "主任", "老師", "醫生", "未知", "測試", "用戶", "客戶", "家屬", "本人"}

    if not folder_path.exists():
        print(f"⚠️ 警告: 找不到人名資料夾 {corpus_folder}，使用預設名單。")
        return default_names
        
    print(f"📂 正在讀取人名: {folder_path} ...")
    for file_path in folder_path.glob("*.txt"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    name = line.strip()
                    # 簡單過濾：長度 2-4，純中文 (英文名通常在 Template 處理，或者你可以放寬這裡)
                    if not (1 < len(name) <= 5): continue 
                    if name in blacklist: continue
                    names.append(name)
        except Exception as e:
            print(f"❌ 讀取 {file_path.name} 失敗: {e}")
    
    names = list(set(names)) # 去重
    random.shuffle(names)
    
    if len(names) == 0:
        return default_names
        
    print(f"✅ 已載入 {len(names)} 個有效人名")
    return names

def parse_one_feature(props):
    """
    專門解析香港 OGCIO GeoJSON 格式
    """
    extracted = []
    try:
        # 嘗試導航到 PremisesAddress
        address_root = props.get('Address', {}).get('PremisesAddress', {})
        # 兼容性處理：有時結構可能不同
        if not address_root and isinstance(props.get('Address'), dict): 
            address_root = props.get('Address')
        
        # 1. 處理中文地址 (ChiPremisesAddress)
        chi_node = address_root.get('ChiPremisesAddress')
        if chi_node:
            region = chi_node.get('Region', '')
            district = chi_node.get('ChiDistrict', '')
            # 有時 District 是字典，有時是字串
            if isinstance(district, dict): district = district.get('ChiDistrictName', '')
            
            estate = chi_node.get('ChiEstate', {}).get('EstateName', '')
            
            full_chi = f"{region}{district}"
            
            # 街道優先
            street_info = chi_node.get('ChiStreet', {})
            if street_info:
                street_name = street_info.get('StreetName', '')
                build_no = street_info.get('BuildingNoFrom', '')
                full_chi += f"{street_name}"
                if build_no: full_chi += f"{build_no}號"
            
            # 村落 (Village) - 備用
            elif 'ChiVillage' in chi_node:
                v_info = chi_node['ChiVillage']
                full_chi += f"{v_info.get('VillageName', '')}{v_info.get('BuildingNoFrom', '')}號"

            # 最後加屋苑/大廈名
            if estate: full_chi += f"{estate}"
            
            if full_chi.strip(): extracted.append(full_chi)

        # 2. 處理英文地址 (EngPremisesAddress)
        eng_node = address_root.get('EngPremisesAddress')
        if eng_node:
            parts = []
            
            # 街道/門牌
            street_info = eng_node.get('EngStreet', {})
            if street_info:
                no = street_info.get('BuildingNoFrom', '')
                st = street_info.get('StreetName', '')
                if no and st: parts.append(f"{no} {st}")
                elif st: parts.append(st)
            
            # 屋苑
            estate = eng_node.get('EngEstate', {}).get('EstateName', '')
            if estate: parts.append(estate)
            
            # 地區
            district = eng_node.get('EngDistrict', '')
            if isinstance(district, dict): district = district.get('DistrictName', '')
            if district: parts.append(district)
            
            # 大區 (HK/KLN/NT)
            region = eng_node.get('Region', '')
            if region: parts.append(region)
            
            full_eng = ", ".join([p for p in parts if p])
            if full_eng: extracted.append(full_eng)
            
    except Exception:
        pass # 忽略解析錯誤的單條數據
        
    return extracted

def load_addresses(geojson_folder):
    addresses = []
    folder_path = Path(geojson_folder)
    default_addr = ["香港觀塘道 99 號 AIA Tower 八樓", "58 BRIDGES STREET, CENTRAL, HK"]
    
    if not folder_path.exists():
        print(f"⚠️ 警告: 找不到地址資料夾 {geojson_folder}，使用預設地址。")
        return default_addr

    print(f"📂 正在讀取地址: {folder_path} ...")
    files = list(folder_path.glob("*.json")) + list(folder_path.glob("*.geojson"))
    
    for file_path in files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
                # 處理 FeatureCollection
                if isinstance(data, dict) and "features" in data:
                    for feature in data["features"]:
                        addresses.extend(parse_one_feature(feature.get("properties", {})))
                # 處理單個 Object 或 List (防禦性編程)
                elif isinstance(data, list):
                     for item in data:
                         addresses.extend(parse_one_feature(item.get("properties", item)))
        except Exception as e:
            print(f"❌ 讀取 {file_path.name} 出錯: {e}")

    # 數據清洗
    cleaned_addresses = []
    seen = set()
    for addr in addresses:
        if addr in seen: continue
        # 過濾太短的地址
        if len(addr) < 5: continue
        # 確保地址包含數字 (對於訓練提取 'ADDRESS' 中的數字很有幫助)
        # 如果你想保留純中文地址(如"置地廣場")，可以註釋掉下面這行
        if not re.search(r'[0-9]|[零一二三四五六七八九十]', addr): continue
        
        cleaned_addresses.append(addr)
        seen.add(addr)
    
    if not cleaned_addresses:
        return default_addr
        
    print(f"✅ 已載入 {len(cleaned_addresses)} 個有效地址")
    return cleaned_addresses

def load_negative_samples(folder_path, max_samples=5000):
    samples = []
    path = Path(folder_path)
    if not path.exists(): return []
    
    print(f"📂 正在讀取負樣本: {folder_path} ...")
    for file_path in path.glob("*.txt"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
                # 簡單分句
                sentences = re.split(r'[。！？\n]', text)
                for sent in sentences:
                    sent = sent.strip()
                    # 保留長度適中的句子
                    if 10 < len(sent) < 150:
                        samples.append(sent)
        except: pass
        
    # 隨機抽取，避免數據過大
    if len(samples) > max_samples:
        samples = random.sample(samples, max_samples)
        
    print(f"✅ 已載入 {len(samples)} 條負樣本")
    return samples

def load_pre_annotated_data(filename):
    if Path(filename).exists():
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 兼容格式：有些 JSON 可能是 {"data": [...]}，有些直接是 [...]
                if isinstance(data, dict) and "data" in data:
                    data = data["data"]
                print(f"📂 成功載入預處理數據: {filename} ({len(data)} 條)")
                return data
        except Exception as e:
            print(f"⚠️ 載入 {filename} 失敗: {e}")
            return []
    return []