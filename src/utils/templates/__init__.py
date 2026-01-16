# src/utils/templates/__init__.py

# 🔥 1. 導入新的智能分離範本
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
    ALL_HK_ORGS,
    get_supplementary_data,
    SUPPLEMENTARY_ORG_TEMPLATES
)

# 為了方便外部調用，確保 ALL_HK_ORGS 可被訪問
# (有些模組可能會直接 from src.utils.templates import ALL_HK_ORGS)

def get_all_templates():
    """整合所有範本：商用足量完美版"""
    return (
        get_standard_templates() + 
        get_hard_negative_templates() + 
        get_commercial_finance_templates() + 
        get_logistics_and_ecommerce_templates() +
        get_customer_service_and_hr_templates() +
        get_extreme_anti_hallucination_templates() +
        get_mixed_slang_templates() +
        get_long_entity_templates() +
        get_phone_variation_templates() +
        get_hong_kong_business_templates() +
        get_org_position_separation_templates() +
        
        # 機構補充數據
        get_supplementary_data() +

        # 🔥 2. 使用負樣本 (Negative Samples)
        # 這裡只包含沒有具體地名的描述 (如 "大型基建")，標記為 O
        get_infrastructure_negatives() +
        
        # 🔥 3. 加入分割訓練範本 (Split Templates)
        # 這裡會生成 "西延[ADDRESS] 高鐵[O]"，教導模型精確切割
        get_infrastructure_split_templates()
    )