# src/training/prepare_data.py
import json
import os
import random
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(project_root)

from src.config import LABEL2ID, ID2LABEL

# 1. 靜態禁止名單 (針對常用詞同 URL)
STRICT_FORBIDDEN = [
    "中國", "國鐵", "港鐵", "MTR", "鐵路", "集團", "有限公司", "十四五", "十五五", "建設", "發展", "高鐵",
    "銀行", "HSBC", "匯豐", "渣打", "中銀", "恒生", "支付寶", "Alipay", "PayMe", "FPS", "轉數快",
    "順豐", "SF Express", "DHL", "淘寶", "Foodpanda", "Deliveroo",
    "香港", "九龍", "新界", "中心", "大廈", "廣場", "街道", "Road", "Street", "Building", "Tower",
    "http", "https", ".com", ".org", ".net", "www", "原文網址"
]

def load_json(path):
    if not os.path.exists(path):
        print(f"⚠️ 找不到檔案: {path}")
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def extract_gold_entities(data_list):
    """動態提取：從新聞同 MTR 數據中提取所有真實標註過的實體字"""
    gold_words = set()
    for item in data_list:
        tokens = item["tokens"]
        tags = item["ner_tags"]
        for i, tag in enumerate(tags):
            if tag != 0: 
                gold_words.add(tokens[i].lower())
    return list(gold_words)

def is_clean(item, dynamic_forbidden):
    """最強過濾邏輯：靜態名單 + 動態金標"""
    tokens = item.get("tokens", [])
    tags = item.get("ner_tags", [])
    
    # 建立一個大名單
    full_forbidden_list = STRICT_FORBIDDEN + dynamic_forbidden

    for i, t in enumerate(tokens):
        # 如果 Token 標記係 O，但佢喺禁止名單入面
        if tags[i] == 0:
            token_low = t.lower()
            if any(forbidden_word.lower() in token_low for forbidden_word in full_forbidden_list):
                return False
    return True

if __name__ == "__main__":
    # 1. 讀取數據
    news = load_json("./data/raw/news_data.json")
    novel = load_json("./data/raw/novel_data.json")
    mtr = load_json("./data/raw/mtr_news_data.json")
    synthetic_raw = load_json("./data/raw/synthetic_data.json")

    # 2. ⚡ 執行前置動態提取
    print("🔍 正在從金標數據中提取動態禁止名單...")
    dynamic_forbidden = extract_gold_entities(news + mtr)
    print(f"✅ 提取完成，新增 {len(dynamic_forbidden)} 個動態保護詞。")

    # 3. 🛡️ 過濾合成數據
    print(f"🛡️ 正在執行合成數據最終清洗 (原始數量: {len(synthetic_raw)})...")
    # 傳入動態名單進行過濾
    synthetic_cleaned = [d for d in synthetic_raw if is_clean(d, dynamic_forbidden)]
    
    removed_count = len(synthetic_raw) - len(synthetic_cleaned)
    if removed_count > 0:
        print(f"🚫 已自動剔除 {removed_count} 條可能導致標籤競爭的合成樣本。")

    # 4. 按權重合併 (商用優化版權重)
    all_training_data = []
    all_training_data.extend(synthetic_cleaned)   # x1
    all_training_data.extend(news * 10)           # x10
    all_training_data.extend(novel * 2)            # x2
    all_training_data.extend(mtr * 10)            # x10

    # 5. 洗牌
    random.shuffle(all_training_data)

    # 6. 數據集成分分析
    pos_count = sum(1 for d in all_training_data if any(t > 0 for t in d['ner_tags']))
    neg_count = len(all_training_data) - pos_count

    print(f"📊 數據分佈摘要：")
    print(f"   - 正樣本: {pos_count}")
    print(f"   - 負樣本: {neg_count} (約 {neg_count/len(all_training_data):.1%})")

    # 7. 輸出
    output = {"data": all_training_data, "label2id": LABEL2ID, "id2label": ID2LABEL}
    with open("train_data_lora.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"🚀 最終訓練集打包完成！總樣本數: {len(all_training_data)}")