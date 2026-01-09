import random
from faker import Faker

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
    real_companies = ["HSBC", "MTR", "KMB", "HKTVmall", "Deliveroo", "Foodpanda", "7-Eleven"]
    name = random.choice(real_companies + [fake.company()])
    return name[:20] 

def generate_transliterated_name(corpus_names):
    """
    專門處理 English_Cn_Name_Corpus 的組合邏輯
    從列表中抽 2 個名字，用符號連接
    """
    if len(corpus_names) < 2:
        return random.choice(corpus_names)

    f = random.choice(corpus_names)
    l = random.choice(corpus_names)
    
    formats = [
        f"{f}·{l}",   # 間隔號
        f"{f}.{l}",   # 點號 (你要求的)
        f"{f}{l}",    # 無間隔
        f"{f} {l}",   # 空格
    ]
    return random.choice(formats)

def get_random_fillers(names_data, addresses):
    """
    names_data 現在是一個 Dict: {"standard": [...], "transliterated": [...]}
    """
    safe_addresses = addresses if addresses else ["香港中環"]
    
    # 決定使用哪種名字來源
    # 30% 機率使用譯名 (English_Cn_Name)，70% 使用標準名 (Chinese/Ancient/Japanese)
    if random.random() < 0.3:
        # 使用譯名庫 -> 執行組合邏輯 (阿阿哲克.阿阿哲克)
        target_name = generate_transliterated_name(names_data["transliterated"])
    else:
        # 使用標準庫 -> 直接抽取 (陳大文, 李白)
        target_name = random.choice(names_data["standard"])

    return {
        "{name}": target_name,
        "{addr}": random.choice(safe_addresses),
        "{phone}": generate_phone(),
        "{id_num}": generate_id(),
        "{account}": generate_account(),
        "{plate}": generate_license_plate(),
        "{org}": generate_company(),
        "{age}": str(random.randint(18, 80))
    }
    # 確保輸入不為空
    safe_names = names if names else ["陳大文"]
    safe_addresses = addresses if addresses else ["香港中環"]

    # 調整機率：
    # 由於你的 safe_names 現在是英漢譯名庫，我們應該主要使用「組合模式」
    # 讓 generate_transliterated_name 使用 safe_names 來生成 "Name.Name"
    
    if random.random() < 0.6: 
        # 60% 機率：組合兩個名字 (例如：阿阿哲克.阿阿哲克奧盧)
        target_name = generate_transliterated_name(safe_names)
    else:
        # 40% 機率：直接從列表中抽一個單名 (例如：阿阿哲克)
        target_name = random.choice(safe_names)

    return {
        "{name}": target_name,
        "{addr}": random.choice(safe_addresses),
        "{phone}": generate_phone(),
        "{id_num}": generate_id(),
        "{account}": generate_account(),
        "{plate}": generate_license_plate(),
        "{org}": generate_company(),
        "{age}": str(random.randint(18, 80))
    }