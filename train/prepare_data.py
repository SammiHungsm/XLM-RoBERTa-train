import os
import json
import random
import re
from pathlib import Path
from faker import Faker

# 初始化 Faker
fake = Faker(['en_US', 'zh_TW'])

# ==========================================
# 1. 讀取人名 (保持不變)
# ==========================================
def load_names(corpus_folder):
    names = []
    folder_path = Path(corpus_folder)
    # Fallback 數據，以防讀取失敗
    default_names = ["陳大文", "李嘉誠", "黃小明", "張偉", "Alice", "Bob", "Sammi", "John", "Peter", "Mary"]
    
    if not folder_path.exists():
        return default_names
        
    for file_path in folder_path.glob("*.txt"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f.readlines() if len(line.strip()) > 1]
                names.extend(lines)
        except Exception:
            pass
    return list(set(names)) if names else default_names

# ==========================================
# 2. 讀取地址 (保持不變)
# ==========================================
def load_addresses(geojson_folder):
    addresses = []
    folder_path = Path(geojson_folder)
    # Fallback 數據
    default_addr = ["香港觀塘道 99 號 AIA Tower 八樓", "58 BRIDGES STREET, CENTRAL, HK", "屯門市廣場 10 樓", "沙田第一城 12 座"]
    
    if not folder_path.exists():
        return default_addr

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
    return list(set([a for a in addresses if a])) or default_addr

# ==========================================
# 3. 增強版生成器
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

def generate_company():
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
# 4. 100+ Templates (分類整理)
# ==========================================
def get_templates():
    # 注意：這是一個 List of Lists。每個子 List 代表一句話的結構。
    # 這種結構是為了配合 "Builder Pattern" 安全生成法。
    return [
        # --- 類別 1: 個人資料 & 居住地 (Personal & Address) ---
        ["已知 ", "{name}", " 現居於 ", "{addr}", "，年齡 ", "{age}", " 歲。"],
        ["", "{name}", " 的住址是 ", "{addr}", "。"],
        ["請更新 ", "{name}", " 的通訊地址為 ", "{addr}", "。"],
        ["居住在 ", "{addr}", " 的 ", "{name}", " 先生/女士。"],
        ["", "{name}", " 剛剛搬到了 ", "{addr}", "。"],
        ["確認資料：姓名 ", "{name}", "，地址 ", "{addr}", "。"],
        ["住戶 ", "{name}", " 投訴 ", "{addr}", " 附近有噪音。"],
        ["登記人 ", "{name}", " 報稱居住於 ", "{addr}", "。"],
        ["", "{name}", " is currently living at ", "{addr}", "."],
        ["Address for ", "{name}", ": ", "{addr}", "."],
        ["", "{name}", " 住在 ", "{addr}", " 已經好多年了。"],
        ["", "{addr}", " 是 ", "{name}", " 的舊居。"],
        ["業主 ", "{name}", " 放售位於 ", "{addr}", " 的單位。"],
        ["", "{name}", " 剛買入 ", "{addr}", " 的豪宅。"],
        ["請問 ", "{name}", " 是否住在 ", "{addr}", "？"],

        # --- 類別 2: 物流 & 送貨 (Logistics) ---
        ["請將包裹送至 ", "{addr}", "，收件人 ", "{name}", "。"],
        ["收件人：", "{name}", "，電話：", "{phone}", "，地址：", "{addr}", "。"],
        ["速遞單號 12345，送往 ", "{addr}", "，聯絡 ", "{name}", "。"],
        ["送餐到 ", "{addr}", "，客人係 ", "{name}", "。"],
        ["司機已經到達 ", "{addr}", " 等緊 ", "{name}", "。"],
        ["", "{name}", " 訂購的貨物已送達 ", "{addr}", "。"],
        ["緊急件！請送 ", "{addr}", " 给 ", "{name}", "，電話 ", "{phone}", "。"],
        ["Please deliver to ", "{name}", " at ", "{addr}", "."],
        ["Shipment for ", "{name}", ", destination: ", "{addr}", "."],
        ["", "{name}", " 拒收了送到 ", "{addr}", " 的郵件。"],
        ["派送員正前往 ", "{addr}", " 尋找 ", "{name}", "。"],
        ["訂單備註：到達 ", "{addr}", " 後請致電 ", "{phone}", " 找 ", "{name}", "。"],
        
        # --- 類別 3: 銀行 & 金融 (Banking) ---
        ["請轉帳到 ", "{account}", "，戶名 ", "{name}", "。"],
        ["", "{name}", " 的銀行戶口是 ", "{account}", " (開戶行: ", "{org}", ")。"],
        ["付款給 ", "{org}", "，帳號 ", "{account}", "，備註 ", "{name}", "。"],
        ["", "{name}", " 在 ", "{org}", " 開立了新戶口 ", "{account}", "。"],
        ["檢測到異常交易：帳戶 ", "{account}", "，持有人 ", "{name}", "。"],
        ["記住這個戶口 ", "{account}", "，係 ", "{name}", " 嘅。"],
        ["", "{org}", " 通知客戶 ", "{name}", " 關於帳戶 ", "{account}", " 的變動。"],
        ["Transfer to ", "{name}", ", Account No: ", "{account}", ", Bank: ", "{org}", "."],
        ["", "{name}", " has an account ", "{account}", " with ", "{org}", "."],
        ["", "{name}", " 欠款存入 ", "{account}", "。"],
        ["", "{org}", " rejected the transaction for ", "{name}", " (Acc: ", "{account}", ")."],
        ["", "{name}", " 的 ", "{org}", " 信用卡號碼與帳戶 ", "{account}", " 連結。"],

        # --- 類別 4: 身份 & 會員 (ID & Membership) ---
        ["客戶 ", "{name}", " (會員編號 ", "{id_num}", ") 剛剛在 ", "{org}", " 點了餐。"],
        ["關於 ", "{name}", " 的資料：地址 ", "{addr}", "，ID ", "{id_num}", "。"],
        ["身分證號碼 ", "{id_num}", " 屬於 ", "{name}", "。"],
        ["", "{name}", " 的員工證編號是 ", "{id_num}", "，任職於 ", "{org}", "。"],
        ["請核對資料：姓名 ", "{name}", "，證件 ", "{id_num}", "。"],
        ["", "{org}", " 登記訪客：", "{name}", " (ID: ", "{id_num}", ")。"],
        ["Reference: ", "{id_num}", ", Name: ", "{name}", ", Mobile: ", "{phone}", "."],
        ["Employee ", "{name}", " (ID ", "{id_num}", ") works at ", "{org}", "."],
        ["", "{name}", " 遺失了身分證 ", "{id_num}", "。"],
        ["系統查詢：", "{id_num}", " 對應的用戶是 ", "{name}", " 嗎？"],
        ["會員 ", "{name}", " 使用 ID ", "{id_num}", " 登入失敗。"],
        
        # --- 類別 5: 公司 & 職場 (Corporate) ---
        ["", "{name}", " 現任職於 ", "{org}", "，辦公室位於 ", "{addr}", "。"],
        ["", "{org}", " 今日宣布業績，股價大升。"],
        ["總部位於 ", "{addr}", " 的 ", "{org}", " 宣布裁員。"],
        ["", "{name}", " previously worked at ", "{org}", ", living in ", "{addr}", "."],
        ["", "{name}", " 已經離開了 ", "{org}", "。"],
        ["", "{org}", " 的 CEO 是 ", "{name}", "。"],
        ["", "{org}", " 在 ", "{addr}", " 舉辦發布會。"],
        ["請聯絡 ", "{org}", " 的負責人 ", "{name}", "，電話 ", "{phone}", "。"],
        ["", "{name}", " joined ", "{org}", " as a manager."],
        ["", "{org}", " is located at ", "{addr}", "."],
        ["", "{name}", " 代表 ", "{org}", " 簽署合約。"],
        ["", "{org}", " 位於 ", "{addr}", " 的分店已結業。"],

        # --- 類別 6: 車輛 & 交通 (Vehicle) ---
        ["車牌號碼 ", "{plate}", " 的車主是 ", "{name}", "。"],
        ["發現一輛違泊車輛，車牌 ", "{plate}", "，停在 ", "{addr}", "。"],
        ["", "{name}", " 駕駛著 ", "{plate}", " 經過紅隧。"],
        ["我的車牌係 ", "{plate}", "，電話 ", "{phone}", "。"],
        ["", "{plate}", " 發生意外，司機 ", "{name}", " 受傷。"],
        ["", "{name}", " 的私家車 ", "{plate}", " 登記地址為 ", "{addr}", "。"],
        ["Car plate ", "{plate}", " belongs to ", "{name}", "."],
        ["Vehicle ", "{plate}", " was seen at ", "{addr}", "."],
        ["", "{org}", " 的公司車 ", "{plate}", " 由 ", "{name}", " 駕駛。"],
        ["請攔截車牌 ", "{plate}", "。"],
        ["", "{name}", " 剛買了新車，車牌 ", "{plate}", "。"],

        # --- 類別 7: 聯絡方式 & 混合 (Contact & Misc) ---
        ["", "{name}", " 係一個好人，電話係 ", "{phone}", "。"],
        ["聯絡人：", "{name}", "，請致電 ", "{phone}", " 找他。"],
        ["如有查詢，請打 ", "{phone}", " 搵 ", "{name}", "。"],
        ["", "{name}", " 的手機號碼改了，新號碼係 ", "{phone}", "。"],
        ["Call ", "{name}", " at ", "{phone}", " ASAP."],
        ["", "{phone}", " 是 ", "{name}", " 的辦公室電話。"],
        ["遺失手機，號碼 ", "{phone}", "，物主 ", "{name}", "。"],
        ["", "{name}", " (Tel: ", "{phone}", ") request a callback."],
        ["面試安排：", "{name}", "，時間明天，地點 ", "{addr}", "。"],
        ["", "{name}", " 欠債不還，電話 ", "{phone}", "，地址 ", "{addr}", "。"], # 追債 Tone
        ["恭喜 ", "{name}", " 抽中大獎，請帶 ID ", "{id_num}", " 領獎。"],
        ["", "{name}", " 和 ", "{org}", " 發生勞資糾紛。"],
        ["", "{org}", " 的客戶服務熱線是 ", "{phone}", "。"],
        ["請將 ", "{account}", " 的結單寄給 ", "{name}", "，地址 ", "{addr}", "。"],
        ["", "{name}", " 駕駛 ", "{plate}", " 到 ", "{addr}", " 接送老闆。"],
        ["", "{org}", " 員工 ", "{name}", " (ID: ", "{id_num}", ") 表現優秀。"],
        ["誰是 ", "{name}", "？為什麼他的電話是 ", "{phone}", "？"],
        ["", "{name}", " 在 ", "{addr}", " 開了一間叫 ", "{org}", " 的店。"]
    ]

# ==========================================
# 5. 合成數據集 (使用安全拼接法)
# ==========================================
def create_dataset_safe(names, addresses, label2id, target_count=None):
    data = []
    templates = get_templates()
    
    if target_count is None: target_count = len(addresses)
    print(f"🚀 安全模式生成 {target_count} 條數據 (使用 100+ Templates 拼接法)...")
    
    # 確保數據庫不為空，防止 Index Error
    safe_names = names if len(names) > 0 else ["陳大文"]
    safe_addresses = addresses if len(addresses) > 0 else ["香港中環"]

    for _ in range(target_count):
        # 1. 隨機選一個 Template 結構
        template_parts = random.choice(templates)
        
        # 2. 準備該次生成的數據 (Fillers)
        fillers = {
            "{name}": random.choice(safe_names),
            "{addr}": random.choice(safe_addresses),
            "{phone}": generate_phone(),
            "{id_num}": generate_id(),
            "{account}": generate_account(),
            "{plate}": generate_license_plate(),
            "{org}": generate_company(),
            "{age}": str(random.randint(18, 80))
        }
        
        full_tokens = []
        full_tags = []
        
        # 3. 逐個部分拼接 (Builder Pattern)
        for part in template_parts:
            # 檢查這個 part 是否是變數 (例如 "{name}")
            if part in fillers:
                entity_text = fillers[part]
                entity_type = "O"
                
                # 判斷實體類型
                if part == "{name}": entity_type = "NAME"
                elif part == "{addr}": entity_type = "ADDRESS"
                elif part == "{phone}": entity_type = "PHONE"
                elif part == "{id_num}": entity_type = "ID"
                elif part == "{account}": entity_type = "ACCOUNT"
                elif part == "{plate}": entity_type = "LICENSE_PLATE"
                elif part == "{org}": entity_type = "ORG"
                
                # 處理實體標籤 (Character-level)
                chars = list(entity_text)
                if not chars: continue # 防止空字串
                
                full_tokens.extend(chars)
                # BIO 標註：第一個字 B-XXX，之後 I-XXX
                if entity_type != "O":
                    full_tags.append(label2id[f"B-{entity_type}"])
                    full_tags.extend([label2id[f"I-{entity_type}"]] * (len(chars) - 1))
                else:
                    full_tags.extend([label2id["O"]] * len(chars))
                
            else:
                # 普通文字 (Template 的固定部分)
                chars = list(part)
                if not chars: continue
                full_tokens.extend(chars)
                full_tags.extend([label2id["O"]] * len(chars))
        
        # 4. 存入數據
        data.append({"tokens": full_tokens, "ner_tags": full_tags})
        
    return data

# ==========================================
# 主程式
# ==========================================
if __name__ == "__main__":
    # 定義標籤
    label_list = [
        "O", 
        "B-NAME", "I-NAME", 
        "B-ADDRESS", "I-ADDRESS", 
        "B-PHONE", "I-PHONE", 
        "B-ID", "I-ID", 
        "B-ACCOUNT", "I-ACCOUNT", 
        "B-LICENSE_PLATE", "I-LICENSE_PLATE",
        "B-ORG", "I-ORG" 
    ]
    label2id = {l: i for i, l in enumerate(label_list)}

    # 讀取外部數據
    # 這裡假設你的資料夾結構沒變
    names_pool = load_names("./Chinese-Names-Corpus-master") 
    addr_pool = load_addresses("./geojson_files")
    
    # 檢查數據量
    print(f"📊 人名庫數量: {len(names_pool)}")
    print(f"📊 地址庫數量: {len(addr_pool)}")

    # 生成數據 (建議先生成 1000 條測試，正式訓練用 50000)
    training_data = create_dataset_safe(names_pool, addr_pool, label2id, target_count=50000)

    # 儲存
    output_data = {
        "data": training_data, 
        "label2id": label2id, 
        "id2label": {str(v): k for k, v in label2id.items()}
    }
    
    with open("train_data_lora.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False)
        
    print("✅ 數據準備完成！train_data_lora.json 已更新 (包含安全標註邏輯及 100+ Templates)。")