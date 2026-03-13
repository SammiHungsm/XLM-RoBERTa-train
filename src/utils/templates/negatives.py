# src/utils/templates/negatives.py

def get_hard_negative_templates():
    """
    🔥 [Hard Negatives] 困難負樣本
    包含泛稱、通用名詞、政府機關等，防止誤認為 PII。
    """
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
        ["呢個 ", "集團 ", "規模好大。"],
        ["請參考第二頁。"],
        ["附件有詳細說明。"],
        ["這個計劃進展順利。"],
        ["", "政府", "宣布新政策。"],
        ["", "警方", "正調查案件。"],
        ["", "當局", "表示關注。"],
        ["", "校方", "拒絕回應。"],
        ["", "官方", "尚未證實。"]
    ]

def get_extreme_anti_hallucination_templates():
    """
    🔥 [Anti-Hallucination] 極端抗幻覺
    防止誤認日期、網址、編號、價格為敏感資料。
    """
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

def get_infrastructure_negatives():
    """
    🔥 [News/Description Style] 新聞與描述性語句
    針對 ID 0/12 的問題：地名作為主語或描述對象時，不應標記為 ADDRESS。
    這裡生成的 {addr} 會在 generator 中被視為 O (非 PII)。
    """
    return [
        ["呢個", "基建項目", "耗資數百億。"],
        ["政府大力推動", "大型基建", "發展。"],
        ["這條", "鐵路", "採用最新技術。"],
        ["", "高速鐵路", "網絡日益完善。"],
        ["", "跨海大橋", "工程艱鉅。"],
        # 新聞語氣負樣本 (這些 {addr} 在負樣本生成模式下標籤為 O)
        ["{addr}", "是一個美麗的城市。"],
        ["{addr}", "的人口密度很高。"],
        ["關於", "{addr}", "的歷史發展。"],
        ["{addr}", "的經濟增長迅速。"],
        ["{addr}", "鐵路全長300公里。"],  # 教模型：見到「全長」、「公里」唔好當地址
        ["{addr}", "大橋設計壽命100年。"],
        ["{addr}", "政府今日宣布新政策。"],
        ["據", "{addr}", "媒體報導。"],
        ["來自", "{addr}", "的代表團。"],
        ["{addr}", "股市收市上升。"]
    ]

def get_age_negative_templates():
    """
    🔥 [Address Bleeding Fix] 數字干擾
    針對 ID 2 的問題：防止模型將「年齡數字」誤判為地址或 ID。
    """
    return [
        # 中文語境
        ["他今年", "{age}", "歲。"],
        ["張三今年已經", "{age}", "歲了。"],
        ["死者是一名", "{age}", "歲男子。"],
        ["年齡：", "{age}", "。"],
        ["我個仔今年", "{age}", "歲大。"], 
        ["一位", "{age}", "歲的老伯伯在公園散步。"],
        ["這件商品價值", "{money}", "元。"],
        ["發生於", "{age}", "年前的往事。"],
        ["身高180cm，體重70kg。"],
        
        # 英文語境
        ["At the age of ", "{age}", "."],
        ["She is ", "{age}", " years old."],
        ["He is currently ", "{age}", "."],
        ["A ", "{age}", "-year-old woman was found."], 
        ["Age: ", "{age}", ""],
        ["The patient is aged ", "{age}", "."]
    ]

def get_all_negatives():
    """
    整合所有負樣本並轉換為字符串列表，供 Generator 使用。
    """
    all_lists = []
    all_lists.extend(get_hard_negative_templates())
    all_lists.extend(get_extreme_anti_hallucination_templates())
    all_lists.extend(get_infrastructure_negatives())
    all_lists.extend(get_age_negative_templates())
    
    # 將列表片段拼接成完整字串
    return ["".join(parts) for parts in all_lists]

# 導出供外部使用的常量
COMMON_NEGATIVES = get_all_negatives()