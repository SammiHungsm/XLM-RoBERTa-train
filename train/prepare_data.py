import os
import json
import random
import re
from pathlib import Path
from faker import Faker  # 記得要 pip install faker

# 初始化 Faker
fake = Faker(['en_US', 'zh_TW'])

# ==========================================
# 1. 讀取人名 (保持不變)
# ==========================================
def load_names(corpus_folder):
    names = []
    folder_path = Path(corpus_folder)
    if not folder_path.exists():
        return ["陳大文", "李嘉誠", "黃小明", "張偉", "Alice", "Bob", "Sammi", "John"]
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
        return ["香港觀塘道 99 號 AIA Tower 八樓", "58 BRIDGES STREET, CENTRAL, HK", "屯門市廣場 10 樓"]

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
                if isinstance(data, dict) and "features" in data:
                    for feature in data["features"]:
                        addresses.extend(parse_geojson_feature(feature.get("properties", {})))
                elif isinstance(data, list):
                     for item in data:
                        props = item.get("properties", item)
                        addresses.extend(parse_geojson_feature(props))
                elif isinstance(data, dict):
                     props = data.get("properties", data)
                     addresses.extend(parse_geojson_feature(props))
        except: pass
    return list(set([a for a in addresses if a])) or ["香港中環"]

# ==========================================
# 3. 增強版生成器 (Updated)
# ==========================================
def generate_phone():
    formats = [
        lambda: f"+852 {random.randint(4, 9)}{random.randint(100, 999)} {random.randint(1000, 9999)}",
        lambda: f"+852{random.randint(4, 9)}{random.randint(1000000, 9999999)}",
        lambda: f"852-{random.randint(4, 9)}{random.randint(1000000, 9999999)}",
        lambda: f"{random.randint(5, 9)}{random.randint(1000000, 9999999)}",
        lambda: f"{random.randint(5, 9)}{random.randint(100, 999)} {random.randint(1000, 9999)}"
    ]
    return random.choice(formats)()

def generate_id():
    prefix = random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    digits = "".join([str(random.randint(0, 9)) for _ in range(6)])
    suffix = random.choice("0123456789A")
    hkid = f"{prefix}{digits}({suffix})"
    explicit_id = f"ID-{random.randint(10000, 99999)}"
    return random.choice([hkid, hkid, hkid, explicit_id]) 

def generate_account():
    formats = [
        lambda: f"{random.randint(100, 999)}-{random.randint(100000, 999999)}-{random.randint(0, 999)}", 
        lambda: f"{random.randint(100, 999)}{random.randint(100000, 999999)}{random.randint(0, 999)}", 
        lambda: f"HK{random.randint(10, 99)}BANK{random.randint(10000000, 99999999)}" 
    ]
    return random.choice(formats)()

def generate_license_plate():
    def hk_plate():
        prefix = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=2))
        nums = str(random.randint(1, 9999))
        return f"{prefix} {nums}"
    
    def cn_plate():
        provinces = "粤京沪津黑吉辽冀豫鲁晋陕内宁甘新青藏鄂皖苏浙闽赣湘桂琼川贵云渝"
        prov = random.choice(provinces)
        city = random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        suffix = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=5))
        return f"{prov}{city} {suffix}"
    
    def tw_plate():
        chars = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=3))
        nums = "".join(random.choices("0123456789", k=4))
        if random.random() > 0.5:
            return f"{chars}-{nums}"
        else:
            return f"{nums}-{chars[:2]}"

    return random.choice([hk_plate, cn_plate, tw_plate])()

# 🔥 新增：生成機構名稱 (ORG)
def generate_company():
    # 混合真實常見大公司 (喚醒 Base Model 記憶) + Faker 生成 (增加多樣性)
    real_companies = [
        "HSBC", "Hang Seng Bank", "Standard Chartered", "Bank of China", "AIA", "Manulife",
        "匯豐銀行", "恒生銀行", "渣打銀行", "中國銀行", "友邦保險", "宏利",
        "PCCW", "HKT", "SmarTone", "China Mobile", "Apple", "Google", "Microsoft", "OpenAI",
        "電訊盈科", "數碼通", "中國移動", "蘋果", "微軟",
        "MTR", "KMB", "CLP", "Sun Hung Kai", "Cheung Kong", "Swire", "HK Jockey Club",
        "港鐵", "九巴", "中電", "新鴻基", "長實", "太古", "香港賽馬會",
        "Deliveroo", "Foodpanda", "Uber", "HKTVmall", "ParknShop", "Wellcome", "7-Eleven"
    ]
    fake_comp = fake.company()
    return random.choice(real_companies + [fake_comp])

# ==========================================
# 4. 合成數據集 (增加 ORG 標籤)
# ==========================================
def create_dataset(names, addresses, target_count=None):
    data = []
    
    # 🔥 升級模板：包含 ORG, 車牌, 銀行情境
    templates = [
        "已知 {name} 現居於 {addr}，年齡 {age} 歲。",
        "{name} 好有錢，住在 {addr}。",
        "{name} 係一個好人，電話係 {phone}。",
        "關於 {name} 的資料：地址 {addr}，ID {id_num}。",
        "聯絡人：{name}，請致電 {phone} 找他。",
        "客戶 {name} (會員編號 {id_num}) 剛剛在 {org} 點了餐。", # ORG
        "請將包裹送至 {addr}，收件人 {name}。",
        "Reference: {id_num}, Name: {name}, Mobile: {phone}.",
        "{name} previously worked at {org}, living in {addr}.", # ORG
        "{name} 的銀行戶口是 {account} (開戶行: {org})。", # ORG
        "請轉帳到 {account}，戶名 {name}。",
        "車牌號碼 {plate} 的車主是 {name}。",
        "發現一輛違泊車輛，車牌 {plate}，停在 {addr}。",
        "{name} 駕駛著 {plate} 經過紅隧。",
        "我的車牌係 {plate}，電話 {phone}。",
        "記住這個車牌 {plate} 和戶口 {account}。",
        "{name} 現任職於 {org}，辦公室位於 {addr}。", # ORG
        "{org} 今日宣布業績，股價大升。", # ORG
        "總部位於 {addr} 的 {org} 宣布裁員。" # ORG
    ]
    
    # 🔥 關鍵修改：加入 B-ORG, I-ORG (總共 15 個標籤)
    label_list = [
        "O", 
        "B-NAME", "I-NAME", 
        "B-ADDRESS", "I-ADDRESS", 
        "B-PHONE", "I-PHONE", 
        "B-ID", "I-ID", 
        "B-ACCOUNT", "I-ACCOUNT", 
        "B-LICENSE_PLATE", "I-LICENSE_PLATE",
        "B-ORG", "I-ORG"  # <--- 加咗呢個
    ]
    label2id = {l: i for i, l in enumerate(label_list)}
    
    if target_count is None: target_count = len(addresses)
    print(f"🚀 生成 {target_count} 條數據 (包含 ORG, 車牌, 銀行戶口)...")
    
    random.shuffle(addresses); random.shuffle(names)
    
    for i in range(target_count):
        temp = random.choice(templates)
        
        c_name = names[i % len(names)]
        c_addr = addresses[i % len(addresses)]
        c_phone = generate_phone()
        c_id = generate_id()
        c_acc = generate_account()
        c_plate = generate_license_plate()
        c_org = generate_company() # 生成公司名
        c_age = str(random.randint(18, 80))
        
        # 格式化文本
        text = temp.format(
            name=c_name, addr=c_addr, age=c_age, 
            phone=c_phone, id_num=c_id, account=c_acc, 
            plate=c_plate, org=c_org
        )
        
        tags = ["O"] * len(text)
        
        # 標記函數
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
        if "{plate}" in temp: mark(text, c_plate, "LICENSE_PLATE", tags)
        if "{org}" in temp: mark(text, c_org, "ORG", tags) # 標記 ORG
        
        data.append({"tokens": list(text), "ner_tags": [label2id[t] for t in tags]})
        
    return data, label2id, label_list

if __name__ == "__main__":
    names_pool = load_names("./Chinese-Names-Corpus-master") 
    addr_pool = load_addresses("./geojson_files")
    
    # 生成數據
    training_data, label2id, _ = create_dataset(names_pool, addr_pool, target_count=50000)

    # 儲存
    output_data = {"data": training_data, "label2id": label2id, "id2label": {str(v): k for k, v in label2id.items()}}
    with open("train_data_lora.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False)
    print("✅ 數據準備完成！train_data_lora.json 已更新 (含 ORG)。")