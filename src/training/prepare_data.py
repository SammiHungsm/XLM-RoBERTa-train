# src/training/prepare_data.py
import json
import os
import random
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(project_root)

from src.config import LABEL2ID, ID2LABEL

# O 的 ID (通常是 0，但從 config 拿最穩陣)
O_ID = LABEL2ID.get("O", 0)

# 1. 靜態禁止名單 (這些詞如果在合成數據中標為 O，99% 是錯的，必須刪除)
STRICT_FORBIDDEN = {
    "中國", "國鐵", "港鐵", "MTR", "鐵路", "集團", "有限公司", "十四五", "十五五", "建設", "發展", "高鐵",
    "銀行", "HSBC", "匯豐", "渣打", "中銀", "恒生", "支付寶", "Alipay", "PayMe", "FPS", "轉數快",
    "順豐", "SF Express", "DHL", "淘寶", "Foodpanda", "Deliveroo",
    "香港", "九龍", "新界", "中心", "大廈", "廣場", "街道", "Road", "Street", "Building", "Tower",
    "http", "https", ".com", ".org", ".net", "www", "原文網址"
}

def load_json(path):
    if not os.path.exists(path):
        print(f"⚠️ 找不到檔案: {path}，將跳過。")
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        # 兼容性處理：如果 json 結構是 {"data": [...]}
        if isinstance(data, dict) and "data" in data:
            return data["data"]
        return data

def extract_gold_entities(data_list):
    """動態提取：從新聞同 MTR 數據中提取實體，但過濾掉太短的詞"""
    gold_words = set()
    for item in data_list:
        tokens = item.get("tokens", [])
        tags = item.get("ner_tags", [])
        
        for i, tag in enumerate(tags):
            # 如果是實體 (不是 O)
            if tag != O_ID: 
                word = tokens[i].lower()
                # 商業邏輯：只提取長度 >= 2 的詞進入黑名單
                # 因為單字 (如 "中", "美", "行") 在普通語境太常見，不應禁止其作為 O 出現
                if len(word) >= 2:
                    gold_words.add(word)
    return gold_words

def is_clean(item, forbidden_set):
    """
    修正版過濾邏輯：
    1. 使用 Set 進行 O(1) 快速查找
    2. 使用 token_low in forbidden_set (精確匹配)，而非 substring
    """
    tokens = item.get("tokens", [])
    tags = item.get("ner_tags", [])
    
    # 如果長度不一致，直接丟棄 (壞數據)
    if len(tokens) != len(tags):
        return False

    for i, t in enumerate(tokens):
        # 邏輯：如果這個 Token 被標記為 O (即非實體)
        # 但它出現在我們的「高危名單」中 -> 代表合成數據可能標漏了 (False Negative)
        # 所以我們要丟棄這條數據，以免誤導模型
        if tags[i] == O_ID:
            token_low = t.lower()
            if token_low in forbidden_set:
                # 這裡原本是 return False
                # 但為了保留「負面樣本」(例如：我住在[中環]) vs (中環係一個地方)，我們只對 STRICT 名單嚴格
                # 對於動態名單，我們放寬一點，或者你可以選擇 return False (視乎你對合成數據質量的信心)
                return False 
                
    return True

if __name__ == "__main__":
    # 1. 讀取數據
    print("📂 讀取原始數據...")
    news = load_json("./data/raw/news_data.json")
    novel = load_json("./data/raw/novel_data.json")
    mtr = load_json("./data/raw/mtr_news_data.json")
    # 這裡假設你有生成好的合成數據 (如無，則為空 list)
    synthetic_raw = load_json("./data/raw/synthetic_data.json")

    # 2. ⚡ 執行前置動態提取
    print("🔍 正在從金標數據中提取動態禁止名單...")
    dynamic_forbidden = extract_gold_entities(news + mtr)
    
    # 合併靜態與動態名單，並轉為小寫 set 以加速
    full_forbidden_set = set(w.lower() for w in STRICT_FORBIDDEN) | dynamic_forbidden
    print(f"✅ 禁止名單構建完成 (靜態: {len(STRICT_FORBIDDEN)} + 動態: {len(dynamic_forbidden)})")

    # 3. 🛡️ 過濾合成數據
    if synthetic_raw:
        print(f"🛡️ 正在執行合成數據最終清洗 (原始: {len(synthetic_raw)})...")
        synthetic_cleaned = [d for d in synthetic_raw if is_clean(d, full_forbidden_set)]
        
        removed_count = len(synthetic_raw) - len(synthetic_cleaned)
        if removed_count > 0:
            print(f"🚫 已剔除 {removed_count} 條潛在標籤衝突的合成樣本。")
    else:
        synthetic_cleaned = []
        print("⚠️ 無合成數據，跳過過濾步驟。")

    # 4. 按權重合併 (數據增強策略)
    all_training_data = []
    
    # 合成數據 (x1) - 用作基礎泛化
    all_training_data.extend(synthetic_cleaned)
    
    # 新聞數據 (x10) - 極其重要，包含高頻 PII，加重權重
    if news:
        print(f"📈 新聞數據倍增 x10")
        all_training_data.extend(news * 10)
    
    # 小說數據 (x3) - 增加上下文多樣性，防止 Overfitting
    if novel:
        print(f"📈 小說數據倍增 x3")
        all_training_data.extend(novel * 3)
    
    # 港鐵數據 (x10) - 針對性領域知識
    if mtr:
        print(f"📈 港鐵數據倍增 x10")
        all_training_data.extend(mtr * 10)

    # 5. 洗牌
    random.shuffle(all_training_data)

    # 6. 數據集成分分析
    pos_count = sum(1 for d in all_training_data if any(t > 0 for t in d['ner_tags']))
    neg_count = len(all_training_data) - pos_count

    print(f"📊 最終數據集摘要：")
    print(f"   - 總數: {len(all_training_data)}")
    print(f"   - 含實體樣本: {pos_count}")
    print(f"   - 純負樣本 (Negative Samples): {neg_count} (佔 {neg_count/len(all_training_data):.1%})")

    # 7. 輸出
    output = {"data": all_training_data, "label2id": LABEL2ID, "id2label": ID2LABEL}
    with open("train_data_lora.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"🚀 train_data_lora.json 已生成！")