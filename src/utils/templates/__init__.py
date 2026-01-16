# src/utils/templates/__init__.py

# 🔥 1. 移除 infrastructure (正樣本)，因為我們不需要 Mask 基建
# from .infrastructure import get_infrastructure_templates 

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
    get_infrastructure_negatives  # 👈 新增：導入基建負樣本
)
from .orgs import (
    ALL_HK_ORGS,
    get_supplementary_data,
    SUPPLEMENTARY_ORG_TEMPLATES
)

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
        
        # 🔥 2. 使用負樣本 (Negative Samples)
        # 這會生成標籤為 O 的基建句子 (如 "屯馬線好方便")，教導模型不要 Mask 它們
        get_infrastructure_negatives()
        
        # ❌ 已移除： + get_infrastructure_templates() 
        # (避免模型將高鐵誤認為私人地址)
    )