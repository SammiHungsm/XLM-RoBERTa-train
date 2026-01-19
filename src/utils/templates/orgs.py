# src/utils/templates/orgs.py

# ==========================================
# 🇭🇰 香港生活化機構名單 (Supplementary ORGs)
# ==========================================

BANKS = [
    "匯豐銀行", "恒生銀行", "渣打銀行", "中銀香港", "東亞銀行", "星展銀行", 
    "大新銀行", "花旗銀行", "Mox Bank", "Livi Bank", "ZA Bank",
    "WeChat Pay", "AlipayHK", "PayMe"
]

RETAIL = [
    "7-Eleven", "7-11", "Circle K", "OK便利店", "惠康", "百佳", "屈臣氏", "萬寧", 
    "HKTVmall", "Don Don Donki", "無印良品", "Aeon", "Sogo", "豐澤", "百老匯", 
    "實惠", "日本城", "優品360", "Apple Store", "Uniqlo", "GU", "Decathlon"
]

LOGISTICS = [
    "順豐速運", "SF Express", "菜鳥驛站", "菜鳥", "DHL", "FedEx", "UPS", 
    "Lalamove", "Gogovan", "智能櫃", "順豐站", "4PX", "集運倉", "郵局"
]

FOOD = [
    "麥當勞", "KFC", "肯德基", "譚仔雲南米線", "譚仔三哥", "大家樂", "大快活", 
    "美心MX", "吉野家", "壽司郎", "元氣壽司", "Starbucks", "Pacific Coffee", 
    "Foodpanda", "Deliveroo", "Keeta", "美團"
]

UTILITIES = [
    "中電", "港燈", "煤氣公司", "水務署", "香港寬頻", "PCCW", "HKT", 
    "Smartone", "CSL", "中國移動香港", "3HK", "數碼通", "有線寬頻"
]

TRANSPORT = [
    "港鐵", "九巴", "城巴", "新渡輪", "Uber", "的士台", "八達通"
]

SCHOOLS = [
    "香港大學", "中文大學", "科技大學", "理工大學", "城市大學", "浸會大學", 
    "英皇書院", "拔萃男書院", "喇沙書院", "聖保羅男女中學"
]

# 合併所有機構，並導出給 __init__.py 使用
ALL_HK_ORGS = BANKS + RETAIL + LOGISTICS + FOOD + UTILITIES + TRANSPORT + SCHOOLS

# ==========================================
# 📝 機構專用模板 (已轉換為 List 格式)
# ==========================================
# ⚠️ 關鍵修正：必須將句子拆開，將 {org} 獨立出來，生成器才能識別並替換
SUPPLEMENTARY_ORG_TEMPLATES = [
    # 日常消費
    ["我去", "{org}", "買嘢。"],
    ["去", "{org}", "買左支水。"],
    ["喺", "{org}", "見到有特價。"],
    ["", "{org}", "排隊排好耐。"],
    ["幫我查下", "{org}", "幾點開門。"],
    
    # 銀行/金融
    ["收到", "{org}", "嘅短訊話有交易。"],
    ["去", "{org}", "攞錢。"],
    ["用", "{org}", "個App轉錢俾你。"],
    ["", "{org}", "收唔收手續費？"],
    ["", "{org}", "個股價跌咗。"],
    ["俾錢", "{org}", "交水費。"],
    
    # 物流
    ["由", "{org}", "送過黎。"],
    ["去", "{org}", "攞件。"],
    ["", "{org}", "送貨好慢。"],
    ["查下單", "{org}", "運單號。"],
    
    # 餐飲
    ["今晚食", "{org}", "好唔好？"],
    ["叫", "{org}", "外賣。"],
    ["", "{org}", "啲野好難食。"],
    ["", "{org}", "新出咗個餐。"],
    
    # 其他
    ["經過", "{org}", "門口。"],
    ["投訴", "{org}", "服務差。"],
    ["喺", "{org}", "做野。"],
    ["約咗人喺", "{org}", "等。"],
    ["", "{org}", "個網上唔到。"]
]

def get_supplementary_data():
    """
    🔥 修正：只回傳模板列表 (List of Lists)
    名單 (ALL_HK_ORGS) 由 __init__.py 直接 import 變數獲取
    """
    return SUPPLEMENTARY_ORG_TEMPLATES