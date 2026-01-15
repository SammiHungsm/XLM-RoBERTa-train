# src/utils/templates/__init__.py

from .general import (
    get_standard_templates,
    get_mixed_slang_templates,
    get_phone_variation_templates
)
from .business import (
    get_commercial_finance_templates,
    get_customer_service_and_hr_templates,
    get_hong_kong_business_templates,
    get_long_entity_templates
)
from .logistics import (
    get_logistics_and_ecommerce_templates
)
from .negatives import (
    get_hard_negative_templates,
    get_extreme_anti_hallucination_templates
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
        get_hong_kong_business_templates() 
    )