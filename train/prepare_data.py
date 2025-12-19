import os
import json
import random
import re
from pathlib import Path
from datasets import Dataset

# ==========================================
# 1. 讀取人名 (保持不變)
# ==========================================
def load_names(corpus_folder):
    names = []
    folder_path = Path(corpus_folder)
    if not folder_path.exists():
        return ["陳大文", "李嘉誠", "黃小明", "張偉", "Alice", "Bob"]
    for file_path in folder_path.glob("*.txt"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f.readlines() if len(line.strip()) > 1]
                names.extend(lines)
        except Exception:
            pass
    return list(set(names)) if names else ["陳大文", "李嘉誠"]

# ==========================================
# 2. 讀取地址 (保持不變)
# ==========================================
def load_addresses(geojson_folder):
    addresses = []
    folder_path = Path(geojson_folder)
    if not folder_path.exists():
        return ["香港觀塘道 99 號 AIA Tower 八樓", "58 BRIDGES STREET, CENTRAL, HK"]

    def parse_geojson_feature(props):
        extracted = []
        try:
            address_root = props.get('Address', {}).get('PremisesAddress', {})
            if not address_root and isinstance(props.get('Address'), dict):
                address_root = props.get('Address')
            
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

    print(f"正在讀取地址: {folder_path}")
    files = list(folder_path.glob("*.json")) + list(folder_path.glob("*.geojson"))
    for file_path in files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "features" in data:
                    for feature in data["features"]:
                        addresses.extend(parse_geojson_feature(feature.get("properties", {})))
        except: pass
    return list(set([a for a in addresses if a])) or ["香港中環"]

# ==========================================
# 3. 增強版生成器 (修正：避免混淆)
# ==========================================
def generate_phone():
    # 確保 +852 與數字之間有時有空格，有時沒有，讓模型習慣
    formats = [
        lambda: f"+852 {random.randint(4, 9)}{random.randint(100, 999)} {random.randint(1000, 9999)}",
        lambda: f"+852{random.randint(4, 9)}{random.randint(1000000, 9999999)}",
        lambda: f"852-{random.randint(4, 9)}{random.randint(1000000, 9999999)}",
        lambda: f"{random.randint(5, 9)}{random.randint(1000000, 9999999)}"
    ]
    return random.choice(formats)()

def generate_id():
    # 修正：移除純長數字生成，避免與電話混淆
    # 只生成 HKID 格式或帶有明確標示的 ID
    prefix = random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    digits = "".join([str(random.randint(0, 9)) for _ in range(6)])
    suffix = random.choice("0123456789A")
    hkid = f"{prefix}{digits}({suffix})"
    
    # 明確的 ID 格式
    explicit_id = f"ID-{random.randint(10000, 99999)}"
    
    return random.choice([hkid, hkid, explicit_id]) # 提高 HKID 權重

def generate_account():
    # 銀行戶口通常有連字符
    return f"{random.randint(100, 999)}-{random.randint(100000, 999999)}-{random.randint(0, 999)}"

# ==========================================
# 4. 合成數據集 (增加敘述性模板)
# ==========================================
def create_dataset(names, addresses, target_count=None):
    data = []
    
    # 增加更多變體，特別是名字後面接形容詞的情況，以及包含無關英文單字的情況
    templates = [
        "已知 {name} 現居於 {addr}，年齡 {age} 歲。",
        "{name} 好有錢，住在 {addr}。",
        "{name} 係一個好人，電話係 {phone}。",
        "關於 {name} 的資料：地址 {addr}，ID {id_num}。",
        "聯絡人：{name}，請致電 {phone} 找他。",
        "客戶 {name} (會員編號 {id_num}) 剛剛在 Deliveroo 點了餐。", # 加入干擾字
        "請將包裹送至 {addr}，收件人 {name}。",
        "Reference: {id_num}, Name: {name}, Mobile: {phone}.",
        "{name} previously worked at Cheung Kong Holdings, living in {addr}.", # 加入干擾字
        "{name} 的銀行戶口是 {account}。"
    ]
    
    label_list = ["O", "B-NAME", "I-NAME", "B-ADDRESS", "I-ADDRESS", "B-PHONE", "I-PHONE", "B-ID", "I-ID", "B-ACCOUNT", "I-ACCOUNT"]
    label2id = {l: i for i, l in enumerate(label_list)}
    
    if target_count is None: target_count = len(addresses)
    print(f"🚀 生成 {target_count} 條數據...")
    
    random.shuffle(addresses); random.shuffle(names)
    
    for i in range(target_count):
        temp = random.choice(templates)
        c_name = names[i % len(names)]
        c_addr = addresses[i % len(addresses)]
        c_phone = generate_phone()
        c_id = generate_id()
        c_acc = generate_account()
        c_age = str(random.randint(18, 80))
        
        text = temp.format(name=c_name, addr=c_addr, age=c_age, phone=c_phone, id_num=c_id, account=c_acc)
        tags = ["O"] * len(text)
        
        def mark(full, sub, type, t_list):
            if sub in full:
                start = full.find(sub)
                end = start + len(sub)
                if all(t_list[k] == "O" for k in range(start, end)):
                    t_list[start] = f"B-{type}"
                    for k in range(start + 1, end): t_list[k] = f"I-{type}"

        if "{name}" in temp: mark(text, c_name, "NAME", tags)
        if "{addr}" in temp: mark(text, c_addr, "ADDRESS", tags)
        if "{phone}" in temp: mark(text, c_phone, "PHONE", tags)
        if "{id_num}" in temp: mark(text, c_id, "ID", tags)
        if "{account}" in temp: mark(text, c_acc, "ACCOUNT", tags)
        
        data.append({"tokens": list(text), "ner_tags": [label2id[t] for t in tags]})
        
    return data, label2id, label_list

if __name__ == "__main__":
    names_pool = load_names("./Chinese-Names-Corpus-master") 
    addr_pool = load_addresses("./geojson_files")
    
    # 這裡我們只生成 50000 條做示範，你可以改回 len(addr_pool)
    training_data, label2id, _ = create_dataset(names_pool, addr_pool, target_count=50000)

    output_data = {"data": training_data, "label2id": label2id, "id2label": {str(v): k for k, v in label2id.items()}}
    with open("train_data_lora.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False)
    print("數據準備完成！")