import random
from faker import Faker

# 🔥 1. 導入我們在 templates.py 定義好的龐大機構名單 & 真實地址
try:
    # 注意這裡新增了 ALL_REAL_ADDRESSES (來自銀行 Excel)
    from src.utils.templates import ALL_HK_ORGS, ALL_REAL_ADDRESSES
except ImportError:
    print("⚠️ 警告：找不到 ALL_HK_ORGS 或 ALL_REAL_ADDRESSES，將使用預設名單。")
    ALL_HK_ORGS = ["HSBC", "MTR", "KMB", "HK Jockey Club"]
    ALL_REAL_ADDRESSES = ["香港中環德輔道中"]

fake = Faker(['en_US', 'zh_TW'])

# 基建/交通路線的地點簡稱 (用來配合 "高鐵", "線", "大橋" 等後綴)
# 🔥 [已擴充] 包含真實與常見的雙字/三字簡稱，訓練模型將其視為單一實體
INFRA_PREFIXES = [
    "西延", "杭衢", "屯馬", "廣深港", "京滬", "港珠澳", 
    "中九龍", "北環", "東鐵", "南港島", "將軍澳", "東涌",
    "深中", "青馬", "汀九", "昂船洲", "大老山", "西區",
    # 新增
    "瀋白", "長贛", "滬昆", "京港", "京台", "川藏", "成渝",
    "甬台溫", "溫福", "福廈", "廈深", "廣珠", "南廣", "貴廣",
    "蘭新", "寶蘭", "石太", "膠濟", "鄭西", "武廣", "合福",
    "深珠", "港澳", "廣佛", "莞惠", "穗深", "江湛", "梅汕",
    "贛深", "張吉懷", "牡佳", "朝凌", "興泉", "浦梅", "常益"
]

def generate_phone():
    """生成多種格式的香港電話號碼"""
    prefix = random.choice(['2', '3', '5', '6', '9'])
    rest = "".join([str(random.randint(0, 9)) for _ in range(7)])
    number = prefix + rest
    formats = [
        lambda: f"+852-{number}",
        lambda: f"{number}",
        lambda: f"{number[:4]} {number[4:]}", # 9123 4567 (訓練模型跨越空格)
        lambda: f"+852 {number}",
        lambda: f"(852) {number}"
    ]
    return random.choice(formats)()

def generate_id():
    return generate_hong_kong_id()

def generate_hong_kong_id():
    """
    生成香港身分證，包含多種變體
    🔥 數據增強：加入空格和符號，解決 Tokenizer 將數字切碎導致識別困難的問題
    """
    # R字頭出現率 20% (模擬舊式/外籍)
    if random.random() < 0.2:
        letter = "R"
    else:
        letter = random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        
    nums = "".join([str(random.randint(0, 9)) for _ in range(6)])
    check = random.choice("0123456789A")
    
    rand = random.random()
    if rand < 0.3:
        # 標準: A123456(7)
        return f"{letter}{nums}({check})"
    elif rand < 0.5:
        # 字母有空格: A 123456(7) (這能訓練模型連接 _A 和 _123)
        return f"{letter} {nums}({check})"
    elif rand < 0.65:
        # 無括號: A1234567
        return f"{letter}{nums}{check}"
    elif rand < 0.8:
        # 帶橫線: A-123456(7)
        return f"{letter}-{nums}({check})"
    elif rand < 0.9:
        # 雜亂空格 (模擬 OCR 錯誤或手殘): A 123 456(7)
        return f"{letter} {nums[:3]} {nums[3:]}({check})"
    else:
        # 🔥 對抗樣本 (Adversarial Case): 模擬像電話長度的 ID (1字母 + 8數字)
        extra_digit = str(random.randint(0, 9))
        return f"{letter}{nums}{check}{extra_digit}"

def generate_account():
    """
    🔥 帳號增強：大幅增加空格和橫線的變體
    """
    length = random.randint(8, 18)
    acc = "".join([str(random.randint(0, 9)) for _ in range(length)])
    
    rand = random.random()
    if rand < 0.3:
        # 加橫線: 123-456-789
        if length > 6:
            return f"{acc[:3]}-{acc[3:7]}-{acc[7:]}"
        return acc
    elif rand < 0.6:
        # 加空格: 123 456 789 (重要！訓練模型跨 Token 識別)
        if length > 8:
            return f"{acc[:4]} {acc[4:]}"
        return acc
    else:
        # 純數字
        return acc

def generate_license_plate():
    """車牌增強"""
    prefix = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=2))
    num = random.randint(100, 9999)
    
    rand = random.random()
    if rand < 0.4:
        return f"{prefix} {num}" # AB 1234 (有空格)
    elif rand < 0.5:
        return f"{prefix}-{num}" # AB-1234
    else:
        return f"{prefix}{num}"  # AB1234

def generate_company():
    # 優先使用真實銀行/機構名單
    candidates = ALL_HK_ORGS if ALL_HK_ORGS else ["HSBC", "MTR", "KMB"]
    
    # 10% 機率用 Faker 生成隨機公司，保持多樣性
    if random.random() < 0.1:
        return fake.company()
    
    return random.choice(candidates)

def generate_transliterated_name(corpus_names):
    """處理譯名組合 (English_Cn_Name)"""
    if not corpus_names or len(corpus_names) < 2:
        return "阿諾·舒華" # Fallback

    f = random.choice(corpus_names)
    l = random.choice(corpus_names)
    
    formats = [
        f"{f}·{l}",   # 間隔號
        f"{f}.{l}",   # 點號
        f"{f}{l}",    # 無間隔
        f"{f} {l}",   # 空格
    ]
    return random.choice(formats)

def generate_money():
    """生成金額字串"""
    amount = random.randint(100, 1000000)
    return f"{amount:,}" # 1,234,567

def get_random_fillers(names_data, addresses):
    """
    names_data: 名字庫
    addresses: 來自 loaders.py 的隨機路名
    """
    
    # 🔥 3. 地址合併策略
    combined_addresses = (addresses or []) + ALL_REAL_ADDRESSES
    safe_addresses = combined_addresses if combined_addresses else ["香港中環"]
    
    # 50% 機率使用基建簡稱
    if random.random() < 0.5:
        target_addr = random.choice(INFRA_PREFIXES)
    else:
        target_addr = random.choice(safe_addresses)
    
    # 名字策略
    if random.random() < 0.3:
        trans_list = names_data.get("transliterated", [])
        if trans_list:
            target_name = generate_transliterated_name(trans_list)
        else:
            target_name = "John Doe"
    else:
        std_list = names_data.get("standard", [])
        if std_list:
            target_name = random.choice(std_list)
        else:
            target_name = "陳大文"

    # 🔥 [關鍵修改] 強制提升稀有實體 (ACCOUNT, LICENSE_PLATE) 的生成機率
    # 1. 車牌 (LICENSE_PLATE) - 之前是 0 分，現在要狂操
    if random.random() < 0.6: # 提高到 60% 機率生成含空格的車牌
        plate = f"{''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=2))} {random.randint(100, 9999)}"
    else:
        plate = generate_license_plate()

    # 2. 銀行戶口 (ACCOUNT) - 增加變體
    acc_raw = "".join([str(random.randint(0, 9)) for _ in range(random.randint(9, 16))])
    if random.random() < 0.4:
        account = f"{acc_raw[:3]}-{acc_raw[3:9]}-{acc_raw[9:]}" # 123-456789-000
    elif random.random() < 0.7:
        account = f"{acc_raw[:4]} {acc_raw[4:8]} {acc_raw[8:]}" # 1234 5678 9000
    else:
        account = acc_raw # 純數字

    return {
        "{name}": target_name,
        "{addr}": target_addr,
        "{phone}": generate_phone(),
        "{id_num}": generate_id(),
        "{account}": account,       # ✅ 使用增強後的 account
        "{plate}": plate,           # ✅ 使用增強後的 plate
        "{org}": generate_company(), 
        "{age}": str(random.randint(18, 80)),
        "{money}": generate_money(),
        
        # 兼容性 Keys
        "{bank}": generate_company(),
        "{station}": generate_company(),
        "{company}": generate_company(),
        
        # 預設空值
        "{code}": str(random.randint(1000, 9999)),
        "{pickup_code}": str(random.randint(100000, 999999)),
        "{order_id}": f"ORD-{random.randint(10000, 99999)}",
        "{email}": fake.email()
    }