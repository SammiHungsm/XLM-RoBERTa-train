import random
from faker import Faker

# 🔥 1. 導入我們在 templates.py 定義好的龐大機構名單
# 確保 src/utils/templates/__init__.py 裡面已經正確 export 了 ALL_HK_ORGS
try:
    from src.utils.templates import ALL_HK_ORGS
except ImportError:
    print("⚠️ 警告：找不到 ALL_HK_ORGS，將使用預設名單。")
    ALL_HK_ORGS = ["HSBC", "MTR", "KMB", "HK Jockey Club"]

fake = Faker(['en_US', 'zh_TW'])

def generate_phone():
    """生成多種格式的香港電話號碼"""
    prefix = random.choice(['2', '3', '5', '6', '9'])
    rest = "".join([str(random.randint(0, 9)) for _ in range(7)])
    number = prefix + rest
    formats = [
        lambda: f"+852-{number}",
        lambda: f"{number}",
        lambda: f"{number[:4]} {number[4:]}", # 增加空格格式 9123 4567
        lambda: f"+852 {number}"
    ]
    return random.choice(formats)()

def generate_id():
    return generate_hong_kong_id()

def generate_hong_kong_id():
    """
    生成香港身分證，包含多種變體以解決 inference #11 的問題
    """
    # 🔥 針對 #11 失敗案例 (R開頭)，我們刻意提高 R 的出現率 (20%)
    if random.random() < 0.2:
        letter = "R"
    else:
        letter = random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        
    nums = "".join([str(random.randint(0, 9)) for _ in range(6)])
    check = random.choice("0123456789A")
    
    rand = random.random()
    if rand < 0.4:
        # 標準格式: A123456(7)
        return f"{letter}{nums}({check})"
    elif rand < 0.7:
        # 無括號: A1234567 (針對 #8 失敗案例)
        return f"{letter}{nums}{check}"
    else:
        # 字母有空格: A 123456(7) (增加難度，針對英文語境)
        return f"{letter} {nums}({check})"

def generate_account():
    """
    🔥 針對 #10 失敗案例 (數字斷裂)
    讓帳號長度變化更大，並隨機加入符號，訓練模型跨 Token 識別
    """
    length = random.randint(8, 18)
    acc = "".join([str(random.randint(0, 9)) for _ in range(length)])
    
    rand = random.random()
    if rand < 0.2:
        # 加橫線: 123-456-789
        if length > 6:
            return f"{acc[:3]}-{acc[3:7]}-{acc[7:]}"
        return acc
    elif rand < 0.4:
        # 加空格: 123 456 789
        if length > 8:
            return f"{acc[:4]} {acc[4:]}"
        return acc
    else:
        # 純數字
        return acc

def generate_license_plate():
    # 增加變體：有的車牌可能會有空格，例如 "AB 1234"
    prefix = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=2))
    num = random.randint(100, 9999)
    if random.random() < 0.3:
        return f"{prefix} {num}" # 加空格
    return f"{prefix}{num}"

def generate_company():
    # 🔥 2. 使用導入的 ALL_HK_ORGS
    # 如果 ALL_HK_ORGS 沒東西 (防呆)，就用 fallback
    
    candidates = ALL_HK_ORGS if ALL_HK_ORGS else ["HSBC", "MTR", "KMB"]
    
    # 偶爾 (10%) 還是會用 Faker 生成一些隨機公司名，增加多樣性
    if random.random() < 0.1:
        return fake.company()
    
    return random.choice(candidates)

def generate_transliterated_name(corpus_names):
    """
    專門處理 English_Cn_Name_Corpus 的組合邏輯
    從列表中抽 2 個名字，用符號連接
    """
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

def get_random_fillers(names_data, addresses):
    """
    names_data: {"standard": [...], "transliterated": [...]}
    addresses: 從 loaders.py 載入的真實地址列表
    """
    # 確保地址不為空
    safe_addresses = addresses if addresses else ["香港中環"]
    
    # 決定使用哪種名字來源
    # 30% 機率使用譯名 (English_Cn_Name)，70% 使用標準名
    if random.random() < 0.3:
        # 使用譯名庫 -> 執行組合邏輯
        trans_list = names_data.get("transliterated", [])
        if trans_list:
            target_name = generate_transliterated_name(trans_list)
        else:
            target_name = "John Doe"
    else:
        # 使用標準庫 -> 直接抽取
        std_list = names_data.get("standard", [])
        if std_list:
            target_name = random.choice(std_list)
        else:
            target_name = "陳大文"

    # 🔥 3. 確保這裡的 {addr} 只從真實地址 (safe_addresses) 選取
    # 我們不再這裡混入「基建名稱」，因為基建應該在 negatives.py 處理 (標記為 O)
    
    return {
        "{name}": target_name,
        "{addr}": random.choice(safe_addresses),
        "{phone}": generate_phone(),
        "{id_num}": generate_id(),
        "{account}": generate_account(),
        "{plate}": generate_license_plate(),
        "{org}": generate_company(), 
        "{age}": str(random.randint(18, 80)),
        "{bank}": generate_company(),
        "{station}": generate_company(),
        "{company}": generate_company()
    }