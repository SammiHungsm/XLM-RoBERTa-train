# src/utils/templates.py

def get_standard_templates():
    """涵蓋正式與日常對話的標準範本"""
    return [
        # --- 繁體中文 / 廣東話 ---
        ["已知 ", "{name}", " 現居於 ", "{addr}", "，年齡 ", "{age}", " 歲。"],
        ["收件人：", "{name}", "，地址：", "{addr}", "，電話：", "{phone}", "。"],
        ["請轉帳到 ", "{account}", "，戶名 ", "{name}", " (", "{org}", ")。"],
        ["身分證號碼 ", "{id_num}", " 屬於 ", "{name}", "。"],
        ["車牌 ", "{plate}", " 的車主是 ", "{name}", "。"],
        ["喂，", "{name}", " 呀，你個電話係咪 ", "{phone}", " 呀？"],
        ["個 Package 寄咗去 ", "{addr}", " 俾 ", "{name}", " 喇。"],
        ["如有查詢，請致電 ", "{phone}", " 聯絡 ", "{name}", "。"],
        ["", "{name}", " 拍過好多套戲，佢住喺 ", "{addr}", "。"],
        ["關於 ", "{name}", " 的傳記。"],
        ["", "{name}", "主演了這部電影。"],
        
        # --- 英文 / 國際化 ---
        ["Receiver: ", "{name}", ", Address: ", "{addr}", ", Tel: ", "{phone}", "."],
        ["Please transfer to ", "{account}", " (Acc Name: ", "{name}", ")."],
        ["Attention of: ", "{name}", ", Location: ", "{addr}", "."],
        ["Employee ", "{name}", " is currently working at ", "{org}", "."],
        ["Invoice sent to ", "{name}", " at ", "{addr}", "."],
        ["", "{name}", " (Mobile: ", "{phone}", ") is requesting support."],
        ["The ID ", "{id_num}", " is assigned to ", "{name}", "."],
        
        # --- 譯名 / 外國名字 ---
        ["這本書的作者是 ", "{name}", "。"],
        ["The author of this book is ", "{name}", "."],
        ["CEO ", "{name}", " lives in ", "{addr}", "."]
    ]

def get_hard_negative_templates():
    """困難負樣本：包含職位、稱呼，但「不」包含具體隱私，防止模型見到職稱就 Mask"""
    return [
        ["經理", "說明天早點上班。"],
        ["", "主席", "發表了演講。"],
        ["這間公司的", "CEO", "非常年輕。"],
        ["", "爸爸", "和", "媽媽", "說今晚回家吃飯。"],
        ["有一位", "女人", "牽著", "狗", "在散步。"],
        ["", "經理", "叫我明天早點上班。"],
        ["Admin", " requested a system restart."],
        ["The ", "doctor", " advised me to rest more."],
        ["", "主任", "已經審批了申請。"],
        ["", "老師", "派發了成績表。"],
        ["", "司機", "已經到達目的地。"]
    ]

def get_boundary_templates():
    """極短或格式化的樣本，強化模型對「起始」和「結束」位置的敏感度"""
    return [
        # --- 支付與金融 ---
        ["PayMe to ", "{name}", " (", "{phone}", ")"],
        ["FPS:", "{account}", " (", "{org}", ")"],
        ["Alipay Account: ", "{account}"],
        ["戶口：", "{account}", " (", "{name}", ")"],
        
        # --- 通訊錄與標籤 ---
        ["Tel: ", "{phone}", " (Office)"],
        ["Contact: ", "{name}", " @ ", "{phone}"],
        ["WhatsApp: ", "{phone}"],
        ["Add: ", "{addr}"],
        
        # --- 香港身分證特殊格式 ---
        ["HKID:", "{id_num}", " (Verified)"],
        ["ID No.: ", "{id_num}"],
        
        # --- 稱呼與後綴 ---
        ["", "{name}", " 先生 (Mr.)"],
        ["", "{name}", " 小姐 (Ms.)"],
        ["Attention: ", "{name}", " (Senior Manager)"]
    ]

def get_anti_hallucination_templates():
    """抗幻覺樣本：提供長數字、網址、時間，但「標記為 O」，防止模型亂 Mask 數字"""
    return [
        # --- 網址與日期 (最容易誤認為 Phone/Account) ---
        ["原文網址：", "https://news.mingpao.com/article/20260104/s00004"],
        ["日期:", "2026-01-04 14:30:00"],
        ["Timestamp:", "1736412345678"],
        ["今年是", "2026年", "，明年是", "2027年", "。"],
        
        # --- 各種編號 (非隱私) ---
        ["UUID:", "550e8400-e29b-41d4-a716-446655440000"],
        ["訂單號：", "ORDER_2024_0104_9999"],
        ["Stock Code:", "00700.HK", " (Tencent)"],
        
        # --- 物理量與單位 ---
        ["身高 ", "180cm", "，體重 ", "75kg", "。"],
        ["距離 ", "12.5 km", "，溫度 ", "25.5 C", "。"],
        ["Price:", "$1,200.00", " (Discount 10%)"],
        ["電力消耗：", "500 kWh"],
        
        # --- 隨機雜訊 ---
        ["The quick brown fox jumps over the lazy dog."],
        ["據報導，今日氣溫顯著下降。"]
    ]

def get_mixed_language_templates():
    """港式英語 / 混合語言範本"""
    return [
        ["Please call ", "{name}", " at ", "{phone}", " to confirm the ", "{org}", " meeting."],
        ["你幫我 Check 下 ", "{name}", " 個 Account ", "{account}", " 仲有無錢。"],
        ["Confirm 咗喇，個 Address 係 ", "{addr}", "，搵 ", "{name}", " 就得。"],
        ["", "{name}", " is our ", "{org}", " representative, contact: ", "{phone}", "."],
        ["送貨去 ", "{addr}", " 唔該，收件人係 ", "{name}", "。"]
    ]
# src/utils/templates.py

def get_commercial_finance_templates():
    """強化商用金融與支付場景：涵蓋支票、電匯、FPS、自動轉帳"""
    return [
        ["支付通知：已轉帳 HKD ", "{money}", " 至帳戶 ", "{account}", " (", "{name}", ")。"],
        ["入數紙證明：收款人 ", "{name}", "，銀行代碼 ", "{org}", "，帳號 ", "{account}", "。"],
        ["請提供您的 ", "{org}", " 帳號 (Account No.: ", "{account}", ") 以便退款。"],
        ["FPS 識別碼：", "{phone}", " 或 ", "{account}", " (受款人: ", "{name}", ")。"],
        ["自動轉帳授權：本人 ", "{name}", " 授權公司扣劃帳戶 ", "{account}", "。"],
        ["Cheque payable to: ", "{name}", " (A/C No: ", "{account}", ")."],
        ["Wire Transfer Info: Beneficiary ", "{name}", ", IBAN: ", "{account}", "."],
        ["TT Payment to ", "{org}", " A/C ", "{account}", " for invoice ", "{id_num}", "."]
    ]

def get_logistics_and_ecommerce_templates():
    """強化物流與電商場景：這是隱私洩漏的高發區"""
    return [
        ["SF Express: 您的包裹已到達 ", "{addr}", "，請聯絡司機 ", "{phone}", "。"],
        ["【菜鳥驛站】憑碼 6-2-1004 領取包裹，收件人：", "{name}", "，地址：", "{addr}", "。"],
        ["Order Confirmation: Item will be shipped to ", "{addr}", " (Attn: ", "{name}", ")."],
        ["Delivery Note: Courier ", "{name}", " (Tel: ", "{phone}", ") is nearby."],
        ["Foodpanda order: Deliver to ", "{addr}", ", Call ", "{phone}", " if needed."],
        ["淘寶訂單：收貨地址 ", "{addr}", "，收件人 ", "{name}", "，電話 ", "{phone}", "。"],
        ["Uber Trip: Picking up ", "{name}", " at ", "{addr}", "."],
    ]

def get_customer_service_and_hr_templates():
    """強化客戶服務與人力資源場景"""
    return [
        ["CV 篩選：申請人 ", "{name}", "，聯絡電話 ", "{phone}", "，現居 ", "{addr}", "。"],
        ["入職通知：請 ", "{name}", " (ID: ", "{id_num}", ") 於下週報到。"],
        ["客戶投訴記錄：客戶姓名 ", "{name}", "，聯絡方式 ", "{phone}", "。"],
        ["醫療報銷申請：患者 ", "{name}", "，診所地址 ", "{addr}", "。"],
        ["Meeting Invite: Organizer ", "{name}", " from ", "{org}", "."],
        ["Internal Memo: Author ", "{name}", " (Staff ID: ", "{id_num}", ")."],
    ]

def get_extreme_anti_hallucination_templates():
    """強化抗幻覺（商用最怕誤殺）：區分編號與帳號、日期與電話"""
    return [
        # --- 像電話但不是電話 ---
        ["會議 ID：", "852 123 4567", " (Zoom Meeting)"], # 視訊 ID 不應標記為 PHONE
        ["驗證碼：", "912345", " (有效時間 5 分鐘)"],
        ["IP Address: ", "192.168.1.100"],
        ["Port Number: ", "8080", " or ", "3306"],
        
        # --- 像帳號但不是帳號 ---
        ["產品 Serial No: ", "2024010199887766"],
        ["物流單號：", "SF1234567890123"],
        ["Tracking: ", "EB123456789HK"],
        ["Git Commit: ", "a1b2c3d4e5f6g7h8"],
        
        # --- 像身分證但不是身分證 ---
        ["座位編號：", "A29", " 樓層 ", "8/F"],
        ["庫存位：", "Z-123-45"],
        ["航班號：", "CX888", " 從 ", "HKG", " 到 ", "JFK"],
    ]

def get_mixed_slang_templates():
    """極端口語與混雜語境 (港式 WhatsApp 體)"""
    return [
        ["唔該幫我找咗張單先，入落 ", "{account}", " (", "{name}", ") 個度。"],
        ["喂係咪 ", "{name}", "？我係 ", "{org}", " 既保安，你個車牌 ", "{plate}", " 塞住咗。"],
        ["麻煩將 ", "{id_num}", " 副本 Send 俾 ", "{name}", " 睇睇。"],
        ["個地址係 ", "{addr}", "，門口有個 ", "{phone}", " 既牌就係喇。"],
        ["我係 ", "{org}", " 既 ", "{name}", "，想同你 Confirm 返個住址。"]
    ]

def get_all_templates():
    """整合所有範本：商用足量版"""
    return (
        get_standard_templates() + 
        get_hard_negative_templates() + 
        get_boundary_templates() + 
        get_anti_hallucination_templates() +
        get_mixed_language_templates() +
        get_commercial_finance_templates() +
        get_logistics_and_ecommerce_templates() +
        get_customer_service_and_hr_templates() +
        get_extreme_anti_hallucination_templates() +
        get_mixed_slang_templates()
    )