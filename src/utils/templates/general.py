# src/utils/templates/general.py

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

def get_mixed_slang_templates():
    """港式口語與混合語境"""
    return [
        ["唔該幫我找咗張單先，入落 ", "{account}", " (", "{name}", ") 個度。"],
        ["喂係咪 ", "{name}", "？我係 ", "{org}", " 既保安，你個車牌 ", "{plate}", " 塞住咗。"],
        ["麻煩將 ", "{id_num}", " 副本 Send 俾 ", "{name}", " 睇睇。"],
        ["個地址係 ", "{addr}", "，門口有個 ", "{phone}", " 既牌就係喇。"]
    ]

def get_phone_variation_templates():
    """針對 A/C 點：增加各種格式的電話範例"""
    return [
        ["Call me at ", "{phone}", " now."],
        ["WhatsApp me +852 ", "{phone}", "."],
        ["聯絡人：", "{name}", "，電話：", "{phone}", "。"],
        ["Tel: (852) ", "{phone}", " (Office)"]
    ]