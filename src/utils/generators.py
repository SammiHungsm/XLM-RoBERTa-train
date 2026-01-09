import random
from faker import Faker

fake = Faker(['en_US', 'zh_TW'])

def generate_phone():
    prefix = random.choice(['2', '3', '5', '6', '9'])
    rest = "".join([str(random.randint(0, 9)) for _ in range(7)])
    number = prefix + rest
    # 為了零錯誤，我們減少極端複雜的格式，確保 Tokenizer 容易處理
    formats = [
        lambda: f"+852-{number}",   # 使用連字符防止被切成多個 O
        lambda: f"{number}",
        lambda: f"{number[:4]}{number[4:]}"
    ]
    return random.choice(formats)()

def generate_id():
    # 統一調用你要求的「一體化」邏輯
    return generate_hong_kong_id()

def generate_hong_kong_id():
    """確保回傳一個完整的 string，沒有空格，括號緊貼"""
    letter = random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    nums = "".join([str(random.randint(0, 9)) for _ in range(6)])
    check = random.choice("0123456789A")
    # ✅ 零錯誤關鍵：不加空格，確保 Tokenizer 將其視為一個整體或連續實體
    return f"{letter}{nums}({check})"

def generate_account():
    # 銀行帳號
    return f"{random.randint(100,999)}-{random.randint(100000,999999)}-{random.randint(0,999)}"

def generate_license_plate():
    prefix = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=2))
    return f"{prefix}{random.randint(100, 9999)}"

def generate_company():
    real_companies = ["HSBC", "MTR", "KMB", "HKTVmall", "Deliveroo", "Foodpanda", "7-Eleven"]
    # 避免生成的公司名太長或包含奇怪符號
    name = random.choice(real_companies + [fake.company()])
    return name[:20] 

def generate_transliterated_name():
    first_names = ["伊隆", "華特", "安柏", "約翰", "愛麗絲", "凱特", "羅拔", "史提芬"]
    last_names = ["馬斯克", "艾薩克森", "赫德", "史密夫", "佐敦", "里夫斯", "拜登"]
    
    f = random.choice(first_names)
    l = random.choice(last_names)
    
    # 注意：這裡的點號會被 tokenizer 切開，但在 generate_synthetic.py 的 
    # tags_list.extend([LABEL2ID[f"I-{entity_type}"]] * (len(tokens) - 1)) 
    # 邏輯下，點號會自動被標為 I-NAME，這是正確的。
    formats = [
        f"{f}·{l}", 
        f"{f}{l}", 
        f"{l}"
    ]
    return random.choice(formats)

def get_random_fillers(names, addresses):
    # 確保輸入不為空
    safe_names = names if names else ["陳大文"]
    safe_addresses = addresses if addresses else ["香港中環"]

    # 30% 外國音譯名, 70% 華人名
    if random.random() < 0.3:
        target_name = generate_transliterated_name()
    else:
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