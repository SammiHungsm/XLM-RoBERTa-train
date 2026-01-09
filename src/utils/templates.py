# src/utils/templates.py

def get_standard_templates():
    """涵蓋正式與日常對話的標準範本"""
    return [
        ["已知 ", "{name}", " 現居於 ", "{addr}", "，年齡 ", "{age}", " 歲。"],
        ["收件人：", "{name}", "，地址：", "{addr}", "，電話：", "{phone}", "。"],
        ["請轉帳到 ", "{account}", "，戶名 ", "{name}", " (", "{org}", ")。"],
        ["身分證號碼 ", "{id_num}", " 屬於 ", "{name}", "。"],
        ["車牌 ", "{plate}", " 的車主是 ", "{name}", "。"],
        ["喂，", "{name}", " 呀，你個電話係咪 ", "{phone}", " 呀？"],
        ["個 Package 寄咗去 ", "{addr}", " 俾 ", "{name}", " 喇。"],
        ["如有查詢，請致電 ", "{phone}", " 聯絡 ", "{name}", "。"],
        ["關於 ", "{name}", " 的傳記。"],
        ["", "{name}", "主演了這部電影。"],
        ["Receiver: ", "{name}", ", Address: ", "{addr}", ", Tel: ", "{phone}", "."],
        ["Please transfer to ", "{account}", " (Acc Name: ", "{name}", ")."],
        ["The ID ", "{id_num}", " is assigned to ", "{name}", "."],
        ["這本書的作者是 ", "{name}", "。"],
        ["CEO ", "{name}", " lives in ", "{addr}", "."]
    ]

def get_hard_negative_templates():
    """Point 2 核心：增加困難負樣本，防止誤殺 (標籤全為 O)"""
    return [
        ["經理", "說明天早點上班。"],
        ["", "主席", "發表了演講。"],
        ["這間公司的", "CEO", "非常年輕。"],
        ["有一位", "女人", "牽著", "狗", "在散步。"],
        ["", "爸爸", "和", "媽媽", "說今晚回家吃飯。"],
        ["The quick brown fox jumps over the lazy dog."],
        ["據報導，今日氣溫顯著下降。"],
        ["請參閱附錄 (A) 嘅內容。"],
        ["呢個係 (第一項) 修正案。"],
        ["由於 (有限公司) 嘅法律定義，我哋要重新審視。"],
        ["雖然 ", "國鐵 ", "係大企業，但都要轉型。"],
        ["呢個 ", "集團 ", "規模好大。"]
    ]

def get_commercial_finance_templates():
    """強化商用金融與支付場景"""
    return [
        ["支付通知：已轉帳 HKD ", "{money}", " 至帳戶 ", "{account}", " (", "{name}", ")。"],
        ["入數紙證明：收款人 ", "{name}", "，銀行代碼 ", "{org}", "，帳號 ", "{account}", "。"],
        ["FPS 識別碼：", "{phone}", " 或 ", "{account}", " (受款人: ", "{name}", ")。"],
        ["Cheque payable to: ", "{name}", " (A/C No: ", "{account}", ")."],
        ["Wire Transfer Info: Beneficiary ", "{name}", ", IBAN: ", "{account}", "."],
        ["TT Payment to ", "{org}", " A/C ", "{account}", " for invoice ", "{id_num}", "."],
        ["MPF 強積金供款確認：僱員 ", "{name}", "，帳號 ", "{account}", "。"]
    ]

def get_logistics_and_ecommerce_templates():
    """強化物流與電商場景"""
    return [
        ["SF Express: 您的包裹已到達 ", "{addr}", "，請聯絡司機 ", "{phone}", "。"],
        ["【菜鳥驛站】憑碼 6-2-1004 領取包裹，收件人：", "{name}", "，地址：", "{addr}", "。"],
        ["Order Confirmation: Item will be shipped to ", "{addr}", " (Attn: ", "{name}", ")."],
        ["淘寶訂單：收貨地址 ", "{addr}", "，收件人 ", "{name}", "，電話 ", "{phone}", "。"],
        ["Foodpanda order: Deliver to ", "{addr}", ", Call ", "{phone}", " if needed."]
    ]

def get_customer_service_and_hr_templates():
    """強化客戶服務與人力資源場景"""
    return [
        ["CV 篩選：申請人 ", "{name}", "，聯絡電話 ", "{phone}", "，現居 ", "{addr}", "。"],
        ["入職通知：請 ", "{name}", " (ID: ", "{id_num}", ") 於下週報到。"],
        ["客戶投訴記錄：客戶姓名 ", "{name}", "，聯絡方式 ", "{phone}", "。"],
        ["Internal Memo: Author ", "{name}", " (Staff ID: ", "{id_num}", ")."]
    ]

def get_extreme_anti_hallucination_templates():
    """極端抗幻覺：防止誤認日期、網址、編號 (標籤全為 O)"""
    return [
        ["會議 ID：", "852 123 4567", " (Zoom Meeting)"], 
        ["驗證碼：", "912345", " (有效時間 5 分鐘)"],
        ["IP Address: ", "192.168.1.100"],
        ["原文網址：", "https://news.mingpao.com/article/20260104/s00004"],
        ["Source: www.gov.hk/news/91234567/index.html"],
        ["Timestamp:", "1736412345678"],
        ["產品 Serial No: ", "2024010199887766"],
        ["物流單號：", "SF1234567890123"],
        ["Tracking: ", "EB123456789HK"],
        ["Git Commit: ", "a1b2c3d4e5f6g7h8"],
        ["今年是", "2026年", "，明年是", "2027年", "。"],
        ["Price:", "$1,200.00", " (Discount 10%)"],
        ["航班號：", "CX888", " 從 ", "HKG", " 到 ", "JFK"]
    ]

def get_mixed_slang_templates():
    """港式口語與混合語境"""
    return [
        ["唔該幫我找咗張單先，入落 ", "{account}", " (", "{name}", ") 個度。"],
        ["喂係咪 ", "{name}", "？我係 ", "{org}", " 既保安，你個車牌 ", "{plate}", " 塞住咗。"],
        ["麻煩將 ", "{id_num}", " 副本 Send 俾 ", "{name}", " 睇睇。"],
        ["個地址係 ", "{addr}", "，門口有個 ", "{phone}", " 既牌就係喇。"]
    ]

def get_long_entity_templates():
    """Point 2 核心：強化長實體認知 (確保模型能認出完整的 ORG 和 ADDRESS)"""
    return [
        ["據 ", "{org}", " 今日披露，該項目已完工。"],
        ["", "{org}", " 分行地址位於 ", "{addr}", "。"],
        ["受款人為 ", "{org}", "，請於三日內過數。"],
        ["", "{org}", " 係全港最大嘅公共運輸機構之一。"],
        ["由 ", "{org}", " 簽發的證明文件。"]
    ]

def get_phone_variation_templates():
    """針對 A/C 點：增加各種格式的電話範例"""
    return [
        ["Call me at ", "{phone}", " now."],
        ["WhatsApp me +852 ", "{phone}", "."],
        ["聯絡人：", "{name}", "，電話：", "{phone}", "。"],
        ["Tel: (852) ", "{phone}", " (Office)"]
    ]

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
        get_phone_variation_templates()
    )