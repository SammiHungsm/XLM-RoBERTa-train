# src/utils/templates/__init__.py

import sys
from pathlib import Path

# 確保可以導入 utils
sys.path.append(str(Path(__file__).resolve().parents[2]))

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
    get_org_position_separation_templates,
    get_job_title_boundary_templates, 
    get_id_confusion_templates,
    get_weak_entity_templates  # Part 17
)
from .logistics import (
    get_logistics_and_ecommerce_templates
)
# 保留你想要的獨立導入方式
from .negatives import (
    get_hard_negative_templates,
    get_extreme_anti_hallucination_templates,
    get_infrastructure_negatives,
    get_age_negative_templates 
)
from .orgs import (
    get_supplementary_data,
    ALL_HK_ORGS as STATIC_ORGS 
)

# ===========================
# 數據整合區 (Data Integration)
# ===========================

print("⏳ 正在初始化銀行數據庫 (讀取 Excel/CSV)...")
try:
    BANK_ORGS, BANK_ADDRS = load_bank_data()
except Exception as e:
    print(f"⚠️ 銀行數據載入失敗: {e}")
    BANK_ORGS, BANK_ADDRS = [], []

# 合併靜態機構名單與動態銀行名單
ALL_HK_ORGS = list(set(STATIC_ORGS + BANK_ORGS))
ALL_REAL_ADDRESSES = BANK_ADDRS

print(f"✅ 機構名單加載完成: 共 {len(ALL_HK_ORGS)} 個")
print(f"✅ 真實地址加載完成: 共 {len(ALL_REAL_ADDRESSES)} 個")

# ===========================
# 🛡️ 核心修復工具 (Safety Helper)
# ===========================
def ensure_string_format(template_list):
    """
    [Critical Fix] 強制將所有模板轉換為 String 格式。
    這是為了解決 Business 模板回傳 List 而非 String 導致的崩潰問題。
    """
    cleaned = []
    for item in template_list:
        if isinstance(item, list):
            # 如果是列表 (e.g. ["支付", "{money}"])，合併為字串
            cleaned.append("".join(item))
        elif isinstance(item, str):
            cleaned.append(item)
    return cleaned

# ===========================
# 範本整合區 (Template Aggregation)
# ===========================

def get_all_templates():
    """
    整合所有範本：商用足量完美版 (18 Parts)
    """
    
    # 1. 一般與對話
    part1 = list(get_standard_templates())
    part2 = list(get_mixed_slang_templates())
    part3 = list(get_phone_variation_templates())
    
    # 2. 商業與金融 (這些通常是 List，必須被 ensure_string_format 清洗)
    part4 = list(get_commercial_finance_templates())
    part5 = list(get_customer_service_and_hr_templates())
    part6 = list(get_hong_kong_business_templates())
    part7 = list(get_long_entity_templates())
    part8 = list(get_org_position_separation_templates())
    
    # 3. 職稱邊界與 ID 混淆修復
    part15 = list(get_job_title_boundary_templates()) 
    part16 = list(get_id_confusion_templates())
    
    # 4. 弱點實體專項修復
    part17 = list(get_weak_entity_templates()) 
    
    # 5. 物流與機構補充
    part9 = list(get_logistics_and_ecommerce_templates())
    part10 = list(get_supplementary_data())
    
    # 6. 負樣本與基建
    part11 = list(get_hard_negative_templates())
    part12 = list(get_extreme_anti_hallucination_templates())
    part13 = list(get_infrastructure_negatives())
    part14 = list(get_infrastructure_split_templates())
    part18 = list(get_age_negative_templates()) 

    # 合併所有列表 (Raw List)
    raw_all = (
        part1 + part2 + part3 + part4 + part5 + 
        part6 + part7 + part8 + part9 + part10 + 
        part11 + part12 + part13 + part14 + 
        part15 + part16 + part17 + part18
    )
    
    # 🔥 關鍵一步：在這裡統一轉成 String，解決報錯！
    final_templates = ensure_string_format(raw_all)
    
    return final_templates