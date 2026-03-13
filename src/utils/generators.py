import random
import re
from typing import List, Dict, Tuple
from faker import Faker

# 🔥 1. 導入我們在 templates.py 定義好的龐大機構名單 & 真實地址
try:
    # 注意這裡新增了 ALL_REAL_ADDRESSES (來自銀行 Excel)
    from src.utils.templates import ALL_HK_ORGS, ALL_REAL_ADDRESSES
except ImportError:
    print("⚠️ 警告：找不到 ALL_HK_ORGS 或 ALL_REAL_ADDRESSES，將使用預設名單。")
    ALL_HK_ORGS = ["HSBC", "MTR", "KMB", "HK Jockey Club"]
    ALL_REAL_ADDRESSES = ["香港中環德輔道中"]

# 基建/交通路線的地點簡稱 (用來配合 "高鐵", "線", "大橋" 等後綴)
INFRA_PREFIXES = [
    "西延", "杭衢", "屯馬", "廣深港", "京滬", "港珠澳", 
    "中九龍", "北環", "東鐵", "南港島", "將軍澳", "東涌",
    "深中", "青馬", "汀九", "昂船洲", "大老山", "西區",
    "瀋白", "長贛", "滬昆", "京港", "京台", "川藏", "成渝",
    "甬台溫", "溫福", "福廈", "廈深", "廣珠", "南廣", "貴廣",
    "蘭新", "寶蘭", "石太", "膠濟", "鄭西", "武廣", "合福",
    "深珠", "港澳", "廣佛", "莞惠", "穗深", "江湛", "梅汕",
    "贛深", "張吉懷", "牡佳", "朝凌", "興泉", "浦梅", "常益"
]

# 🔥 [新增] 基建後綴庫 (讓簡稱變成明確地點，提升 Address Precision)
INFRA_SUFFIXES = ["線", "段", "站", "工程", "大橋", "隧道", "公路", "鐵路", "高鐵"]

# 🔥 [新增] 地名 (GPE) 列表：明確定義這些詞為 ADDRESS
GPE_LIST = [
    "香港", "九龍", "新界", "港島", 
    "中國", "美國", "英國", "日本", "台灣", "澳門", "韓國", "加拿大", "澳洲",
    "廣東省", "上海", "北京", "深圳", "廣州", "東莞", "珠海",
    "東京", "倫敦", "紐約", "巴黎", "新加坡", "曼谷", "台北"
]

class PIIDataGenerator:
    """
    PII 數據生成器 (Logic Driven)
    - 集成 Faker 與自定義生成邏輯 (Enhanced Generators)
    - 區分完整地址 vs 地名碎片 vs 基建名
    - 自動注入邊界噪音 (Noise Injection)
    """
    
    def __init__(self, 
                 full_addresses: List[str], 
                 locations: List[str], 
                 names_dict: Dict[str, List[str]],
                 templates: Dict[str, List[str]]):
        
        self.fake = Faker(['en_US', 'zh_TW'])
        self.full_addresses = full_addresses if full_addresses else ["香港中環"]
        self.locations = locations if locations else ["香港"]
        self.names = names_dict
        self.templates = templates
        
        # 邊界噪音：專門用來訓練模型在數字前停手
        self.boundary_noises = [
            " 31歲", "，31歲", ", 31 years old", 
            ". Age 45", "，今年20", " (1990)", 
            " $500", "，長度100米", " 800呎"
        ]

    # ==========================================
    # 🧩 原子生成器 (Atomic Generators)
    # ==========================================

    def generate_phone(self):
        """生成多種格式的香港電話號碼"""
        prefix = random.choice(['2', '3', '5', '6', '9'])
        rest = "".join([str(random.randint(0, 9)) for _ in range(7)])
        number = prefix + rest
        formats = [
            lambda: f"+852-{number}",
            lambda: f"{number}",
            lambda: f"{number[:4]} {number[4:]}", 
            lambda: f"+852 {number}",
            lambda: f"(852) {number}"
        ]
        return random.choice(formats)()

    def generate_id(self):
        return self.generate_hong_kong_id()

    def generate_hong_kong_id(self):
        """生成香港身分證，包含多種變體"""
        # R字頭出現率 20% (模擬舊式/外籍)
        if random.random() < 0.2:
            letter = "R"
        else:
            letter = random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
            
        nums = "".join([str(random.randint(0, 9)) for _ in range(6)])
        check = random.choice("0123456789A")
        
        rand = random.random()
        if rand < 0.3:
            return f"{letter}{nums}({check})" # 標準
        elif rand < 0.5:
            return f"{letter} {nums}({check})" # 字母有空格
        elif rand < 0.65:
            return f"{letter}{nums}{check}" # 無括號
        elif rand < 0.8:
            return f"{letter}-{nums}({check})" # 帶橫線
        elif rand < 0.9:
            return f"{letter} {nums[:3]} {nums[3:]}({check})" # 雜亂空格
        else:
            # 對抗樣本: 模擬像電話長度的 ID
            extra_digit = str(random.randint(0, 9))
            return f"{letter}{nums}{check}{extra_digit}"

    def generate_account(self):
        """帳號增強"""
        length = random.randint(8, 18)
        acc = "".join([str(random.randint(0, 9)) for _ in range(length)])
        
        rand = random.random()
        if rand < 0.3:
            if length > 6:
                return f"{acc[:3]}-{acc[3:7]}-{acc[7:]}"
            return acc
        elif rand < 0.6:
            if length > 8:
                return f"{acc[:4]} {acc[4:]}"
            return acc
        else:
            return acc

    def generate_license_plate(self):
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

    def generate_company(self):
        # 優先使用真實銀行/機構名單
        candidates = ALL_HK_ORGS if ALL_HK_ORGS else ["HSBC", "MTR", "KMB"]
        if random.random() < 0.1:
            return self.fake.company()
        return random.choice(candidates)

    def generate_transliterated_name(self, corpus_names):
        """處理譯名組合"""
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

    def generate_money(self):
        """生成金額字串"""
        amount = random.randint(100, 1000000)
        return f"{amount:,}" # 1,234,567

    # ==========================================
    # 🎮 核心填充邏輯 (Fillers & Slots)
    # ==========================================

    def _get_random_fillers(self):
        """
        生成一組隨機的實體數據，用於填充模板。
        """
        
        # 1. 地址生成策略
        combined_addresses = (self.full_addresses or []) + ALL_REAL_ADDRESSES
        safe_addresses = combined_addresses if combined_addresses else ["香港中環"]
        
        rand_val = random.random()
        target_addr = ""
        
        if rand_val < 0.3:  # 30% 基建 + 後綴 (e.g. 西延線)
            base = random.choice(INFRA_PREFIXES)
            suffix = random.choice(INFRA_SUFFIXES)
            target_addr = f"{base}{suffix}"
            
        elif rand_val < 0.7: # 40% 真實/隨機組合詳細地址
            if random.random() < 0.5:
                 target_addr = random.choice(safe_addresses)
            else:
                 # 隨機組合地址 (增加多樣性)
                 districts = ["觀塘", "中環", "屯門", "沙田", "旺角", "北角", "灣仔", "銅鑼灣", "深水埗", "元朗"]
                 estates = ["花園", "中心", "大廈", "廣場", "新村", "閣", "工廠大廈", "公館", "臺"]
                 target_addr = f"{random.choice(districts)}{random.choice(estates)}"
                 # 偶爾加層數
                 if random.random() < 0.5:
                     target_addr += f"{random.randint(1, 30)}座{random.randint(1, 90)}樓"
                     
        else: # 30% 🔥 GPE 地名 (滿足 "masked as address" 的需求)
            target_addr = random.choice(GPE_LIST)
        
        # 2. 名字生成策略
        if random.random() < 0.3:
            trans_list = self.names.get("transliterated", [])
            target_name = self.generate_transliterated_name(trans_list) if trans_list else "John Doe"
        else:
            std_list = self.names.get("standard", [])
            target_name = random.choice(std_list) if std_list else "陳大文"

        # 3. 稀有實體增強
        # 車牌
        if random.random() < 0.6: 
            plate = f"{''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=2))} {random.randint(100, 9999)}"
        else:
            plate = self.generate_license_plate()

        # 銀行戶口
        acc_raw = "".join([str(random.randint(0, 9)) for _ in range(random.randint(9, 16))])
        if random.random() < 0.4:
            account = f"{acc_raw[:3]}-{acc_raw[3:9]}-{acc_raw[9:]}"
        elif random.random() < 0.7:
            account = f"{acc_raw[:4]} {acc_raw[4:8]} {acc_raw[8:]}"
        else:
            account = acc_raw

        return {
            "{name}": target_name,
            "{address}": target_addr, # 統一使用 {address} 作為 key
            "{addr}": target_addr,    # 兼容
            "{phone}": self.generate_phone(),
            "{id_num}": self.generate_id(),
            "{id}": self.generate_id(), # 兼容
            "{account}": account,
            "{plate}": plate,
            "{org}": self.generate_company(), 
            "{company}": self.generate_company(), # 兼容
            "{bank}": self.generate_company(),    # 兼容
            "{age}": str(random.randint(18, 80)),
            "{money}": self.generate_money(),
            "{code}": str(random.randint(1000, 9999)),
            "{email}": self.fake.email()
        }

    def _inject_noise(self, text, end_idx):
        """
        在實體結束後插入噪音，但不改變實體標籤。
        這是為了訓練模型在地址/名字後面遇到數字時停止。
        """
        if random.random() < 0.4: # 40% 機率插入噪音
            noise = random.choice(self.boundary_noises)
            # 確保是在句子結尾或合理位置插入
            return text + noise
        return text

    def generate_sample(self, category: str) -> Dict:
        """
        生成單條訓練數據
        """
        template_list = self.templates.get(category, [])
        if not template_list: return None

        template = random.choice(template_list)
        fillers = self._get_random_fillers()
        
        entities = []
        text = template
        
        # 遍歷 fillers 進行替換
        # 注意：這裡使用正則表達式來處理多次出現的情況，並計算 offsets
        
        # 定義我們要追蹤的 PII 類型與對應的 Placeholder
        pii_map = [
            (r'\{address\}|\{addr\}', "ADDRESS", fillers["{address}"]),
            (r'\{name\}', "NAME", fillers["{name}"]),
            (r'\{id_num\}|\{id\}', "ID", fillers["{id_num}"]),
            (r'\{phone\}', "PHONE", fillers["{phone}"]),
            (r'\{account\}', "ACCOUNT", fillers["{account}"]),
            (r'\{plate\}', "LICENSE_PLATE", fillers["{plate}"]),
            (r'\{org\}|\{company\}|\{bank\}', "ORG", fillers["{org}"]),
            (r'\{email\}', "EMAIL", fillers["{email}"])
        ]
        
        # 簡單替換 (Simple Replacement with Offset Tracking)
        # 為了處理多個實體，我們需要動態更新 text 和 entities
        
        for pattern, label, value in pii_map:
            # 查找所有匹配項
            matches = list(re.finditer(pattern, text))
            if not matches: continue
            
            # 從後往前替換，這樣不會影響前面的索引
            for match in reversed(matches):
                start, end = match.span()
                
                # 執行替換
                prefix = text[:start]
                suffix = text[end:]
                text = prefix + value + suffix
                
                # 記錄實體 (新位置)
                entity_start = start
                entity_end = start + len(value)
                
                # 針對 ADDRESS 注入噪音 (只影響 text，不影響 entity end)
                if label == "ADDRESS":
                    text = self._inject_noise(text, entity_end)
                
                entities.append({
                    "start": entity_start,
                    "end": entity_end,
                    "label": label,
                    "word": value
                })
        
        # 因為我們是倒序添加的，最後把 entities 轉正並排序
        entities.sort(key=lambda x: x['start'])
        
        # 處理非 PII 的佔位符 (如 {age}, {money})
        # 這些不需要標記為實體
        misc_map = {
            "{age}": fillers["{age}"],
            "{money}": fillers["{money}"],
            "{code}": fillers["{code}"]
        }
        for k, v in misc_map.items():
            text = text.replace(k, v)

        return {"text": text, "entities": entities}