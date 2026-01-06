import os
import json
import random
import re
from pathlib import Path

def load_names(corpus_folder):
    names = []
    folder_path = Path(corpus_folder)
    default_names = ["陳大文", "李嘉誠", "黃小明", "張偉", "Alice", "Bob", "Sammi", "John", "Peter", "Mary"]
    blacklist = {"先生", "小姐", "女士", "經理", "主任", "老師", "醫生", "未知", "測試", "用戶", "客戶", "家屬"}

    if not folder_path.exists(): return default_names
        
    for file_path in folder_path.glob("*.txt"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    name = line.strip()
                    if not (1 < len(name) <= 4): continue
                    if not re.match(r'^[\u4e00-\u9fff]+$', name): continue
                    if name in blacklist: continue
                    names.append(name)
        except Exception: pass
    
    names = list(set(names))
    random.shuffle(names)
    print(f"✅ 已載入 {len(names)} 個有效人名")
    return names if names else default_names

def load_addresses(geojson_folder):
    addresses = []
    folder_path = Path(geojson_folder)
    default_addr = ["香港觀塘道 99 號 AIA Tower 八樓", "58 BRIDGES STREET, CENTRAL, HK"]
    
    if not folder_path.exists(): return default_addr

    def parse_geojson_feature(props):
        extracted = []
        try:
            address_root = props.get('Address', {}).get('PremisesAddress', {})
            if not address_root and isinstance(props.get('Address'), dict): address_root = props.get('Address')
            
            # Chi
            chi_node = address_root.get('ChiPremisesAddress')
            if chi_node and isinstance(chi_node, dict):
                region = chi_node.get('Region', '')
                district = chi_node.get('ChiDistrict', {}).get('ChiDistrictName', '') if isinstance(chi_node.get('ChiDistrict'), dict) else chi_node.get('ChiDistrict', '')
                estate = chi_node.get('ChiEstate', {}).get('EstateName', '') if 'ChiEstate' in chi_node else ""
                full_chi = ""
                if 'ChiVillage' in chi_node:
                    v_info = chi_node['ChiVillage']
                    full_chi = f"{region}{district}{v_info.get('VillageName','')}{v_info.get('BuildingNoFrom','')}號{estate}"
                elif 'ChiStreet' in chi_node:
                    s_info = chi_node['ChiStreet']
                    full_chi = f"{region}{district}{s_info.get('StreetName','')}{s_info.get('BuildingNoFrom','')}號{estate}"
                if full_chi: extracted.append(full_chi)

            # Eng
            eng_node = address_root.get('EngPremisesAddress')
            if eng_node and isinstance(eng_node, dict):
                region = eng_node.get('Region', '')
                district = eng_node.get('EngDistrict', {}).get('DistrictName', '') if isinstance(eng_node.get('EngDistrict'), dict) else eng_node.get('EngDistrict', '')
                estate = eng_node.get('EngEstate', {}).get('EstateName', '') if 'EngEstate' in eng_node else ""
                parts = []
                if 'EngVillage' in eng_node:
                    v_info = eng_node['EngVillage']
                    parts = [f"{v_info.get('BuildingNoFrom','')} {v_info.get('VillageName','')}", estate, district, region]
                elif 'EngStreet' in eng_node:
                    s_info = eng_node['EngStreet']
                    parts = [f"{s_info.get('BuildingNoFrom','')} {s_info.get('StreetName','')}", estate, district, region]
                full_eng = ", ".join([p for p in parts if p and p.strip()])
                if full_eng: extracted.append(full_eng)
            
            if not extracted:
                for key in ["ChiAddress", "Address", "name", "Name"]:
                    val = props.get(key)
                    if val and isinstance(val, str): extracted.append(val); break
        except: pass
        return extracted

    print(f"📂 正在讀取地址: {folder_path}")
    files = list(folder_path.glob("*.json")) + list(folder_path.glob("*.geojson"))
    for file_path in files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "features" in data:
                    for feature in data["features"]: addresses.extend(parse_geojson_feature(feature.get("properties", {})))
                elif isinstance(data, list):
                     for item in data: addresses.extend(parse_geojson_feature(item.get("properties", item)))
                elif isinstance(data, dict):
                     addresses.extend(parse_geojson_feature(data.get("properties", data)))
        except: pass

    cleaned_addresses = []
    for addr in set(addresses):
        if len(addr) < 6: continue
        if not re.search(r'[0-9零一二三四五六七八九十]', addr): continue
        cleaned_addresses.append(addr)
    
    print(f"✅ 已載入 {len(cleaned_addresses)} 個有效地址")
    return cleaned_addresses or default_addr

def load_negative_samples(folder_path, max_samples=5000):
    samples = []
    path = Path(folder_path)
    if not path.exists(): return []
    print(f"📂 正在讀取負樣本: {folder_path} ...")
    for file_path in path.glob("*.txt"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
                sentences = re.split(r'[。！？\n]', text)
                for sent in sentences:
                    sent = sent.strip()
                    if 10 < len(sent) < 150: samples.append(sent)
        except: pass
    if len(samples) > max_samples: samples = random.sample(samples, max_samples)
    return samples

def load_pre_annotated_data(filename):
    if Path(filename).exists():
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"📂 成功載入預處理數據: {filename} ({len(data)} 條)")
                return data
        except: return []
    return []