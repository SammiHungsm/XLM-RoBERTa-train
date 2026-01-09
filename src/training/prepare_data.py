# src/training/prepare_data.py
import json
import os
import random
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(project_root)

from src.config import LABEL2ID, ID2LABEL

# O 的 ID
O_ID = LABEL2ID.get("O", 0)

# 1. 靜態禁止名單
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
        if isinstance(data, dict) and "data" in data:
            return data["data"]
        return data

def extract_gold_entities(data_list):
    """動態提取實體"""
    gold_words = set()
    for item in data_list:
        tokens = item.get("tokens", [])
        tags = item.get("ner_tags", [])
        for i, tag in enumerate(tags):
            if tag != O_ID: 
                word = tokens[i].lower()
                if len(word) >= 2:
                    gold_words.add(word)
    return gold_words

def is_clean(item, forbidden_set):
    """過濾邏輯"""
    tokens = item.get("tokens", [])
    tags = item.get("ner_tags", [])
    if len(tokens) != len(tags): return False
    for i, t in enumerate(tokens):
        if tags[i] == O_ID:
            token_low = t.lower()
            if token_low in forbidden_set:
                return False 
    return True

if __name__ == "__main__":
    # 1. 讀取數據
    print("📂 讀取原始數據...")
    news = load_json("./data/raw/news_data.json")
    novel = load_json("./data/raw/novel_data.json")
    mtr = load_json("./data/raw/mtr_news_data.json")
    synthetic_raw = load_json("./data/raw/synthetic_data.json")

    # 2. 執行前置動態提取
    # 注意：如果這裡結果是 0，代表 news/mtr 可能有問題，但我們下面的平衡機制會防止它破壞數據集
    dynamic_forbidden = extract_gold_entities(news + mtr)
    full_forbidden_set = set(w.lower() for w in STRICT_FORBIDDEN) | dynamic_forbidden
    print(f"✅ 禁止名單構建完成 (靜態: {len(STRICT_FORBIDDEN)} + 動態: {len(dynamic_forbidden)})")

    # 3. 過濾合成數據
    if synthetic_raw:
        print(f"🛡️ 正在執行合成數據最終清洗 (原始: {len(synthetic_raw)})...")
        synthetic_cleaned = [d for d in synthetic_raw if is_clean(d, full_forbidden_set)]
        removed_count = len(synthetic_raw) - len(synthetic_cleaned)
        if removed_count > 0:
            print(f"🚫 已剔除 {removed_count} 條潛在標籤衝突的合成樣本。")
    else:
        synthetic_cleaned = []

    # 4. 按權重合併
    all_training_data = []
    
    # 合成數據 (x1) - 這是我們的主力
    all_training_data.extend(synthetic_cleaned)
    
    # 新聞數據 (x10) - 如果裡面全是負樣本，這一步會引入大量負樣本
    if news: all_training_data.extend(news * 10)
    
    # 小說數據 (改為 x1) - 降低權重，因為小說通常負樣本很多
    if novel: 
        print(f"📉 小說數據權重降至 x1 (防止引入過多負樣本)")
        all_training_data.extend(novel * 1)
    
    # 港鐵數據 (x10)
    if mtr: all_training_data.extend(mtr * 10)

    # 5. 🔥 [核心修改] 強制平衡機制 (Balancing)
    print("⚖️ 正在執行數據平衡 (Target: 負樣本佔總數 ~25%)...")
    
    # 分離正負樣本
    pos_samples = [d for d in all_training_data if any(t != O_ID for t in d['ner_tags'])]
    neg_samples = [d for d in all_training_data if all(t == O_ID for t in d['ner_tags'])]
    
    print(f"   - 原始分佈 -> 正樣本: {len(pos_samples)} | 負樣本: {len(neg_samples)}")

    # 計算目標負樣本數量 (正樣本的 1/3，即總數的 25% 左右)
    target_neg_count = int(len(pos_samples) * 0.35) 
    
    if len(neg_samples) > target_neg_count:
        print(f"   - ✂️ 削減負樣本: {len(neg_samples)} -> {target_neg_count}")
        neg_samples = random.sample(neg_samples, target_neg_count)
    else:
        print(f"   - ✅ 負樣本數量健康，無需削減。")
        
    # 合併並洗牌
    final_data = pos_samples + neg_samples
    random.shuffle(final_data)

    # 6. 最終統計
    final_pos = len(pos_samples)
    final_neg = len(neg_samples)
    total = len(final_data)

    print(f"📊 最終數據集摘要：")
    print(f"   - 總數: {total}")
    print(f"   - 含實體樣本: {final_pos} ({final_pos/total:.1%})")
    print(f"   - 純負樣本:   {final_neg} ({final_neg/total:.1%})")

    # 7. 輸出
    output = {"data": final_data, "label2id": LABEL2ID, "id2label": ID2LABEL}
    with open("train_data_lora.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"🚀 train_data_lora.json 已生成！")