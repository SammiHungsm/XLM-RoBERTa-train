# src/utils/templates/logistics.py

def get_logistics_and_ecommerce_templates():
    """
    強化物流與電商場景
    包含：快遞通知、訂單確認、外賣平台、列表分隔測試
    """
    
    raw_templates = [
        # --- 1. 快遞與取件通知 ---
        ["SF Express: 您的包裹已到達 ", "{addr}", "，請聯絡司機 ", "{phone}", "。"],
        ["【菜鳥驛站】憑碼 6-2-1004 領取包裹，收件人：", "{name}", "，地址：", "{addr}", "。"],
        ["順豐速運：運單號 ", "{code}", " 已派送至 ", "{addr}", "。"],
        ["Lalamove 司機正前往 ", "{addr}", "，聯絡電話：", "{phone}", "。"],
        ["您的 HKTVmall 訂單已抵達 ", "{addr}", " 門市。"],
        
        # --- 2. 電商訂單 ---
        ["Order Confirmation: Item will be shipped to ", "{addr}", " (Attn: ", "{name}", ")."],
        ["淘寶訂單：收貨地址 ", "{addr}", "，收件人 ", "{name}", "，電話 ", "{phone}", "。"],
        ["Amazon: Your package is out for delivery to ", "{addr}", "."],
        ["發票已寄出至：", "{addr}", "，抬頭：", "{org}", "。"],
        
        # --- 3. 外賣平台 ---
        ["Foodpanda order: Deliver to ", "{addr}", ", Call ", "{phone}", " if needed."],
        ["Deliveroo: 你的外賣員已到達 ", "{addr}", " 大堂。"],
        ["Keeta: ", "{name}", " 您好，訂單已送達 ", "{addr}", "。"],
        
        # --- 4. 列表與多地址測試 (List Separation) ---
        # 🔥 核心修復：防止模型將多個地址合併為一個
        ["分店地址包括：", "{addr}", "、", "{addr}", "及", "{addr}", "。"],
        ["送貨路線：先去 ", "{addr}", "，再去 ", "{addr}", "。"],
        ["服務範圍覆蓋 ", "{addr}", " 和 ", "{addr}", " 地區。"],
        ["路線途經", "{addr}", " -> ", "{addr}", " -> ", "{addr}", "。"]
    ]
    
    return ["".join(parts) for parts in raw_templates]