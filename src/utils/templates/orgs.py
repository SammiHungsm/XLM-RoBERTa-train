# src/utils/templates/orgs.py

# ==========================================
# 🇭🇰 香港生活化機構名單 (Supplementary ORGs)
# ==========================================

BANKS = [
    "匯豐銀行", "恒生銀行", "渣打銀行", "中銀香港", "東亞銀行", "星展銀行", 
    "大新銀行", "花旗銀行", "Mox Bank", "Livi Bank", "ZA Bank"
]

RETAIL = [
    "7-Eleven", "7-11", "Circle K", "OK便利店", "惠康", "百佳", "屈臣氏", "萬寧", 
    "HKTVmall", "Don Don Donki", "無印良品", "Aeon", "Sogo", "豐澤", "百老匯", 
    "實惠", "日本城", "優品360"
]

LOGISTICS = [
    "順豐速運", "SF Express", "菜鳥驛站", "菜鳥", "DHL", "FedEx", "UPS", 
    "Lalamove", "Gogovan", "智能櫃", "順豐站", "4PX", "集運倉"
]

FOOD = [
    "麥當勞", "KFC", "肯德基", "譚仔雲南米線", "譚仔三哥", "大家樂", "大快活", 
    "美心MX", "吉野家", "壽司郎", "元氣壽司", "Starbucks", "Pacific Coffee", 
    "Foodpanda", "Deliveroo"
]

UTILITIES = [
    "中電", "港燈", "煤氣公司", "水務署", "香港寬頻", "PCCW", "HKT", 
    "Smartone", "CSL", "中國移動香港", "3HK"
]

TRANSPORT = [
    "港鐵", "九巴", "城巴", "新渡輪", "Uber", "的士台"
]

SCHOOLS = [
    "香港大學", "中文大學", "科技大學", "理工大學", "城市大學", "浸會大學", 
    "英皇書院", "拔萃男書院", "喇沙書院"
]

# 合併所有機構，方便生成器調用
ALL_HK_ORGS = BANKS + RETAIL + LOGISTICS + FOOD + UTILITIES + TRANSPORT + SCHOOLS

# ==========================================
# 📝 機構專用模板
# ==========================================
SUPPLEMENTARY_ORG_TEMPLATES = [
    "我去{org}買嘢", "收到{org}嘅短訊", "去{org}攞錢", "用{org}個App", 
    "經過{org}門口", "{org}做緊優惠", "投訴{org}服務差", "喺{org}做野",
    "{org}個股價跌咗", "約咗人喺{org}等", "由{org}送過黎", "俾錢{org}"
]

def get_supplementary_data():
    """回傳所有機構名單和模板"""
    return ALL_HK_ORGS, SUPPLEMENTARY_ORG_TEMPLATES