# src/utils/templates/logistics.py

def get_logistics_and_ecommerce_templates():
    """強化物流與電商場景"""
    return [
        ["SF Express: 您的包裹已到達 ", "{addr}", "，請聯絡司機 ", "{phone}", "。"],
        ["【菜鳥驛站】憑碼 6-2-1004 領取包裹，收件人：", "{name}", "，地址：", "{addr}", "。"],
        ["Order Confirmation: Item will be shipped to ", "{addr}", " (Attn: ", "{name}", ")."],
        ["淘寶訂單：收貨地址 ", "{addr}", "，收件人 ", "{name}", "，電話 ", "{phone}", "。"],
        ["Foodpanda order: Deliver to ", "{addr}", ", Call ", "{phone}", " if needed."]
    ]