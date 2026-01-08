# data_utils/generators.py
import random
from faker import Faker

fake = Faker(['en_US', 'zh_TW'])

def generate_phone():
    prefix = random.choice(['2', '3', '5', '6', '9'])
    rest = "".join([str(random.randint(0, 9)) for _ in range(7)])
    number = prefix + rest
    formats = [
        lambda: f"+852 {number[:4]} {number[4:]}",
        lambda: f"{number}",
        lambda: f"{number[:4]} {number[4:]}"
    ]
    return random.choice(formats)()

def generate_id():
    prefix = random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    digits = "".join([str(random.randint(0, 9)) for _ in range(6)])
    suffix = random.choice("0123456789A")
    return random.choice([f"{prefix}{digits}({suffix})", f"{prefix}{digits}{suffix}"])

def generate_account():
    # 模擬恆生/匯豐等格式
    return f"{random.randint(100,999)}-{random.randint(100000,999999)}-{random.randint(0,999)}"

def generate_license_plate():
    prefix = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=2))
    return f"{prefix} {random.randint(100, 9999)}"

def generate_company():
    real_companies = ["HSBC", "MTR", "KMB", "HKTVmall", "Deliveroo", "Foodpanda", "7-Eleven"]
    return random.choice(real_companies + [fake.company()])

def generate_transliterated_name():
    # 常見音譯字庫
    first_names = [
        "伊隆", "華特", "安柏", "約翰", "大衛", "米高", "傑克", "湯姆", 
        "愛麗絲", "瑪麗", "露西", "凱特", "羅拔", "史提芬", "基努", 
        "列奥那多", "克里斯", "泰勒", "珍妮花"
    ]
    
    last_names = [
        "馬斯克", "艾薩克森", "赫德", "史密夫", "佐敦", "占士", "里夫斯", 
        "狄卡比奧", "漢斯", "斯威夫特", "勞倫斯", "波特", "華盛頓", 
        "林肯", "甘迺迪", "特朗普", "拜登", "奧巴馬"
    ]
    
    # 隨機組合：有時有中間名，有時有點，有時無點
    f = random.choice(first_names)
    l = random.choice(last_names)
    
    formats = [
        f"{f}．{l}",      # 華特．艾薩克森 (標準全形點)
        f"{f}·{l}",       # 華特·艾薩克森 (半形點)
        f"{f}{l}",        # 華特艾薩克森 (無點)
        f"{l}",           # 馬斯克 (單姓)
        f"{f}",           # 安柏 (單名)
        f"{f}．{l}．{random.choice(last_names)}" # 長名字：查理斯．威廉．王子
    ]
    
    return random.choice(formats)

# ✅ 修改：get_random_fillers
def get_random_fillers(names, addresses):
    safe_names = names if names else ["陳大文"]
    safe_addresses = addresses if addresses else ["香港"]

    # 決定這次用「華人名」定係「外國人名」
    # 30% 機會生成外國長名，70% 機會生成華人名
    if random.random() < 0.3:
        target_name = generate_transliterated_name()
    else:
        target_name = random.choice(safe_names)

    return {
        "{name}": target_name,  # 這裡會隨機變成 "華特．艾薩克森"
        "{addr}": random.choice(safe_addresses),
        "{phone}": generate_phone(),
        "{id_num}": generate_id(),
        "{account}": generate_account(),
        "{plate}": generate_license_plate(),
        "{org}": generate_company(),
        "{age}": str(random.randint(18, 80))
    }