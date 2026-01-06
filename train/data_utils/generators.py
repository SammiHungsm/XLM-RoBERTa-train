import random
from faker import Faker

fake = Faker(['en_US', 'zh_TW'])

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
    return hk_plate()

def generate_company():
    real_companies = ["HSBC", "Hang Seng Bank", "Standard Chartered", "Bank of China", "AIA", "Manulife", "PCCW", "HKT", "SmarTone", "China Mobile", "MTR", "KMB", "CLP", "Deliveroo", "Foodpanda", "Uber", "HKTVmall", "ParknShop", "Wellcome", "7-Eleven"]
    return random.choice(real_companies + [fake.company()])

def get_random_fillers(names, addresses):
    """一次過獲取所有需要的填充數據"""
    safe_names = names if len(names) > 0 else ["陳大文"]
    safe_addresses = addresses if len(addresses) > 0 else ["香港中環"]
    
    return {
        "{name}": random.choice(safe_names),
        "{addr}": random.choice(safe_addresses),
        "{phone}": generate_phone(),
        "{id_num}": generate_id(),
        "{account}": generate_account(),
        "{plate}": generate_license_plate(),
        "{org}": generate_company(),
        "{age}": str(random.randint(18, 80))
    }