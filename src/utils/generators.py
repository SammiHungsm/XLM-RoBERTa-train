# src/utils/generators.py
import random
from faker import Faker

# 🔥 1. 導入我們在 templates.py 定義好的龐大機構名單
from src.utils.templates import ALL_HK_ORGS

fake = Faker(['en_US', 'zh_TW'])

def generate_phone():
    prefix = random.choice(['2', '3', '5', '6', '9'])
    rest = "".join([str(random.randint(0, 9)) for _ in range(7)])
    number = prefix + rest
    formats = [
        lambda: f"+852-{number}",
        lambda: f"{number}",
        lambda: f"{number[:4]}{number[4:]}"
    ]
    return random.choice(formats)()

def generate_id():
    return generate_hong_kong_id()

def generate_hong_kong_id():
    """確保回傳一個完整的 string，沒有空格，括號緊貼"""
    letter = random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    nums = "".join([str(random.randint(0, 9)) for _ in range(6)])
    check = random.choice("0123456789A")
    return f"{letter}{nums}({check})"

def generate_account():
    return f"{random.randint(100,999)}-{random.randint(100000,999999)}-{random.randint(0,999)}"

def generate_license_plate():
    prefix = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=2))
    return f"{prefix}{random.randint(100, 9999)}"

def generate_company():
    # 🔥 2. 修改這裡：不再用 hardcoded 列表
    # 直接使用導入的 ALL_HK_ORGS，這樣合成數據就會有 "菜鳥驛站", "譚仔", "匯豐" 等等
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
    """
    # 確保地址不為空
    safe_addresses = addresses if addresses else ["香港中環"]
    
    # 決定使用哪種名字來源
    # 30% 機率使用譯名 (English_Cn_Name)，70% 使用標準名
    if random.random() < 0.3:
        # 使用譯名庫 -> 執行組合邏輯
        # 確保 names_data["transliterated"] 存在
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

    # 🔥 3. 這是你原本代碼的邏輯，這裡正確回傳 Dict
    return {
        "{name}": target_name,
        "{addr}": random.choice(safe_addresses),
        "{phone}": generate_phone(),
        "{id_num}": generate_id(),
        "{account}": generate_account(),
        "{plate}": generate_license_plate(),
        "{org}": generate_company(), # 這裡現在會調用新的 generate_company
        "{age}": str(random.randint(18, 80)),
        
        # 補漏：如果你有些 template 用了這些 key，雖然目前邏輯一樣，但為了安全起見
        "{bank}": generate_company(),
        "{station}": generate_company(),
        "{company}": generate_company()
    }