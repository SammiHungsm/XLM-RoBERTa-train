# src/utils/templates.py

def get_standard_templates():
    return [
        ["已知 ", "{name}", " 現居於 ", "{addr}", "，年齡 ", "{age}", " 歲。"],
        ["", "{name}", " 的住址是 ", "{addr}", "。"],
        ["確認資料：姓名 ", "{name}", "，地址 ", "{addr}", "。"],
        ["", "{name}", " is currently living at ", "{addr}", "."],
        ["請將包裹送至 ", "{addr}", "，收件人 ", "{name}", "。"],
        ["收件人：", "{name}", "，電話：", "{phone}", "，地址：", "{addr}", "。"],
        ["請轉帳到 ", "{account}", "，戶名 ", "{name}", "。"],
        ["", "{name}", " 的銀行戶口是 ", "{account}", " (開戶行: ", "{org}", ")。"],
        ["客戶 ", "{name}", " (會員編號 ", "{id_num}", ") 剛剛在 ", "{org}", " 點了餐。"],
        ["身分證號碼 ", "{id_num}", " 屬於 ", "{name}", "。"],
        ["", "{name}", " 現任職於 ", "{org}", "，辦公室位於 ", "{addr}", "。"],
        ["車牌號碼 ", "{plate}", " 的車主是 ", "{name}", "。"],
        ["", "{name}", " 係一個好人，電話係 ", "{phone}", "。"],
        ["如有查詢，請打 ", "{phone}", " 搵 ", "{name}", "。"],
        ["", "{name}", " (Tel: ", "{phone}", ") request a callback."],
        # --- 針對譯名 (已修正：改為變量防止標籤出錯) ---
        ["這本書的作者是", "{name}", "。"],
        ["", "{name}", "是這間公司的CEO。"],
        ["", "{name}", "拍過好多套戲。"],
        ["關於", "{name}", "的傳記。"],
        ["", "{name}", "主演了這部電影。"],
        ["出生地：", "{addr}", "，國籍：", "{addr}", "。"] # 強化國家/地區作為地址
    ]

def get_hard_negative_templates():
    return [
        ["我", "爹", "今天去了街市買菜。"],
        ["我的", "娘", "親手做了一件衣服。"],
        ["那個", "男人", "站在路邊吸煙。"],
        ["有一位", "女人", "牽著", "狗", "在散步。"],
        ["", "爸爸", "和", "媽媽", "說今晚回家吃飯。"],
        ["", "醫生", "說我要多休息。"],
        ["", "經理", "叫我明天早點上班。"],
        ["", "老師", "派發了成績表。"],
        ["", "主席", "發表了演講。"]
    ]

def get_boundary_templates():
    return [
        ["轉數快", "{account}", "唔該"],
        ["FPS:", "{account}", "確認"],
        ["Account:", "{account}", "Pending"],
        ["我的戶口係", "{account}", "現任", "{org}", "管理層。"],
        ["收件人帳號", "{account}", " (渣打銀行)"],
        ["Call", "{phone}", "ASAP"],
        ["Tel:", "{phone}", "Office"],
        ["送貨司機電話", "{phone}", "。"],
        ["ID:", "{id_num}", " (副本)"], # 已修正：防止括號重複
        ["HKID:", "{id_num}", "已驗證"],
        ["", "{name}", "先生"],
        ["", "{name}", "小姐"],
        ["", "{name}", "總經理過目。"]
    ]

def get_anti_hallucination_templates():
    return [
        ["詳情請瀏覽", "https://www.google.com", "。"],
        ["UUID:", "550e8400-e29b-41d4-a716-446655440000", "。"], # 增加 UUID 防止誤認 Account
        ["訂單編號:", "ORDER-2024-XA-9988", "。"],
        ["身高", "180cm", "，體重", "75kg", "。"],
        ["今年是", "2026年", "，明年是", "2027年", "。"],
        ["原文網址：", "https://news.mingpao.com/article/20260104", "。"],
        ["價格", "$100", "，折扣", "10%", "。"]
    ]

def get_all_templates():
    return (get_standard_templates() + 
            get_hard_negative_templates() + 
            get_boundary_templates() + 
            get_anti_hallucination_templates())