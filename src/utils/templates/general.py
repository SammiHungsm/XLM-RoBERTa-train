# src/utils/templates/general.py

def get_standard_templates():
    """
    涵蓋正式與日常對話的標準範本
    重點修復：地址邊界、英文 PII 漏抓、短句忽略
    """
    
    raw_templates = [
        # ===========================
        # 1. 基礎生活場景 (Base)
        # ===========================
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
        ["這本書的作者是 ", "{name}", "。"],
        ["作者 ", "{name}", " (", "{name}", ") 寫得好好。"], 

        # ===========================
        # 2. 地址邊界強化 (Address Boundary Reinforcement)
        # 🔥 核心修復：強制「地址」緊接「標點」再緊接「數字/年齡」
        # ===========================
        ["已知 ", "{name}", " 居住於 ", "{addr}", "，", "{age}", " 歲。"], 
        ["居住於 ", "{addr}", "，", "{age}", " 歲。"],
        ["住址：", "{addr}", " (", "{age}", "歲/未婚)。"],
        ["住址：", "{addr}", " (", "{age}", "歲)。"],
        ["送往 ", "{addr}", "，聯絡 ", "{phone}", "。"],
        ["送貨到 ", "{addr}", "，聯絡 ", "{phone}", "。"],
        ["", "{addr}", "，", "業主", "是 ", "{name}", "。"],
        ["", "{name}", " 住係 ", "{addr}", "，佢今年 ", "{age}", " 歲。"],
        ["公司位於", "{addr}", "，成立於", "{code}", "年。"],
        ["送貨到", "{addr}", "，貨到付款", "{money}", "。"],
        ["登記地址：", "{addr}", "。聯絡電話：", "{phone}", "。"],

        # ===========================
        # 3. 英文 PII 盲點修復 (English PII Fixes)
        # ===========================
        ["Receiver: ", "{name}", ", Address: ", "{addr}", ", Tel: ", "{phone}", "."],
        ["Please transfer to ", "{account}", " (Acc Name: ", "{name}", ")."],
        ["The ID ", "{id_num}", " is assigned to ", "{name}", "."],
        ["CEO ", "{name}", " lives in ", "{addr}", "."],
        ["My HKID is ", "{id_num}", "."],
        ["My HKID is ", "{id_num}", ", please check."],
        ["Please note down my ID: ", "{id_num}", " for reference."],
        ["ID number: ", "{id_num}", "."],
        ["My car license number is ", "{plate}", "."],
        ["My car license plate is ", "{plate}", "."],
        ["Plate number: ", "{plate}", "."],
        ["Driver with plate ", "{plate}", " please move your car."],
        ["Transfer the money to account ", "{account}", "."],
        ["Transfer to ", "{account}", " now."],
        ["My bank account number is ", "{account}", "."],
        ["Account: ", "{account}", " / Name: ", "{name}", "."],
        ["HKID: ", "{id_num}", " / Phone: ", "{phone}", "."],

        # ===========================
        # 4. 短句與破碎格式 (Short & Special)
        # ===========================
        ["身分證 ", "{id_num}", "。"],
        ["ID ", "{id_num}", "。"],
        ["我的證件號係 ", "{id_num}", "。"],
        ["ID: ", "R", "{id_num}", "(", "A", ")"], 
        ["My ID starts with ", "R", ": ", "{id_num}", "."],
        ["Account number is ", "123", " ", "{account}", "."],

        # ===========================
        # 5. 常見 APP 與 縮寫
        # ===========================
        ["去 ", "A&E", " 睇醫生。"],
        ["加我 ", "line", " 傾。"], 
        ["用 ", "whatsapp", " send 比你。"]
    ]
    
    return ["".join(parts) for parts in raw_templates]

def get_mixed_slang_templates():
    """港式口語與混合語境"""
    raw_templates = [
        ["唔該幫我找咗張單先，入落 ", "{account}", " (", "{name}", ") 個度。"],
        ["喂係咪 ", "{name}", "？我係 ", "{org}", " 既保安，你個車牌 ", "{plate}", " 塞住咗。"],
        ["麻煩將 ", "{id_num}", " 副本 Send 俾 ", "{name}", " 睇睇。"],
        ["個地址係 ", "{addr}", "，門口有個 ", "{phone}", " 既牌就係喇。"]
    ]
    return ["".join(parts) for parts in raw_templates]

def get_phone_variation_templates():
    """增加各種格式的電話範例"""
    raw_templates = [
        ["Call me at ", "{phone}", " now."],
        ["WhatsApp me +852 ", "{phone}", "."],
        ["聯絡人：", "{name}", "，電話：", "{phone}", "。"],
        ["Tel: (852) ", "{phone}", " (Office)"]
    ]
    return ["".join(parts) for parts in raw_templates]