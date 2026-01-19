# src/utils/templates/__init__.py

from src.utils.bank_loader import load_bank_data

# 🔥 1. 導入各類範本模組
from .infrastructure import get_infrastructure_split_templates
from .general import (
    get_standard_templates,
    get_mixed_slang_templates,
    get_phone_variation_templates
)
from .business import (
    get_commercial_finance_templates,
    get_customer_service_and_hr_templates,
    get_hong_kong_business_templates,
    get_long_entity_templates,
    get_org_position_separation_templates
)
from .logistics import (
    get_logistics_and_ecommerce_templates
)
from .negatives import (
    get_hard_negative_templates,
    get_extreme_anti_hallucination_templates,
    get_infrastructure_negatives
)
from .orgs import (
    get_supplementary_data,
    # 將 orgs.py 裡定義的豐富名單 (譚仔、Donki...) 導入為 STATIC_ORGS
    ALL_HK_ORGS as STATIC_ORGS 
)

# ===========================
# 數據整合區 (Data Integration)
# ===========================

print("⏳ 正在初始化銀行數據庫 (讀取 Excel/CSV)...")
# 1. 載入動態銀行數據
BANK_ORGS, BANK_ADDRS = load_bank_data()

# 2. 合併機構名單
# 結合「靜態生活名單」與「金管局銀行名單」，提供給 Generator 使用
# 使用 set 去重，再轉回 list
ALL_HK_ORGS = list(set(STATIC_ORGS + BANK_ORGS))

# 3. 導出真實地址
ALL_REAL_ADDRESSES = BANK_ADDRS

# ===========================
# 範本整合區 (Template Aggregation)
# ===========================

def get_all_templates():
    """
    整合所有範本：商用足量完美版
    🔥 關鍵修復：使用 list() 強制轉型，防止 TypeError (tuple + list)
    """
    
    # 一般與對話
    part1 = list(get_standard_templates())
    part2 = list(get_mixed_slang_templates())
    part3 = list(get_phone_variation_templates())
    
    # 商業與金融
    part4 = list(get_commercial_finance_templates())
    part5 = list(get_customer_service_and_hr_templates())
    part6 = list(get_hong_kong_business_templates())
    part7 = list(get_long_entity_templates())
    part8 = list(get_org_position_separation_templates())
    
    # 物流與機構補充
    part9 = list(get_logistics_and_ecommerce_templates())
    part10 = list(get_supplementary_data()) # 這裡之前可能回傳了 tuple，現在強制轉 list
    
    # 負樣本與基建
    part11 = list(get_hard_negative_templates())
    part12 = list(get_extreme_anti_hallucination_templates())
    part13 = list(get_infrastructure_negatives())
    part14 = list(get_infrastructure_split_templates())

    # 合併所有列表
    all_templates = (
        part1 + part2 + part3 + part4 + part5 + 
        part6 + part7 + part8 + part9 + part10 + 
        part11 + part12 + part13 + part14
    )
    
    return all_templates