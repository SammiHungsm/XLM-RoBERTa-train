# src/training/prepare_data.py
import json
import os
import random
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(project_root)

# ✅ 1. 從 Config 導入 BASE_FORBIDDEN，保持代碼整潔
from src.config import LABEL2ID, ID2LABEL, BASE_FORBIDDEN
# ✅ 2. 導入機構名單，自動同步
from src.utils.templates import ALL_HK_ORGS 

# O 的 ID
O_ID = LABEL2ID.get("O", 0)

# 🔥 核心邏輯：動態合併「基礎禁止詞」與「所有已知機構名」
STRICT_FORBIDDEN = set(BASE_FORBIDDEN) | set(ALL_HK_ORGS)

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
    """
    🔥 [已升級] 動態提取實體
    解析 BIO 標籤，還原出完整的實體詞（例如從 "B-ORG, I-ORG" 還原出 "港鐵"）。
    """
    gold_words = set()
    for item in data_list:
        tokens = item.get("tokens", [])
        tags = item.get("ner_tags", [])
        
        current_word = ""
        for i, tag in enumerate(tags):
            if tag != O_ID:
                current_word += tokens[i]
            else:
                if len(current_word) >= 2:
                    gold_words.add(current_word.lower())
                current_word = ""
        
        if len(current_word) >= 2:
            gold_words.add(current_word.lower())
            
    return gold_words

def is_clean(item, forbidden_set):
    """
    🔥 [已升級] 過濾邏輯
    將 O-tag 的部分重組為字串後再檢查，解決 Tokenizer 將「港鐵」切分後無法過濾的問題。
    """
    tokens = item.get("tokens", [])
    tags = item.get("ner_tags", [])
    
    if len(tokens) != len(tags): return False

    # 1. 構建「純 O 內容字串」
    o_content_segments = []
    current_segment = ""
    
    for i, t in enumerate(tokens):
        if tags[i] == O_ID:
            current_segment += t
        else:
            if current_segment:
                o_content_segments.append(current_segment)
                current_segment = ""
    
    if current_segment:
        o_content_segments.append(current_segment)
    
    # 2. 檢查每個 O 片段是否含有禁止詞
    for segment in o_content_segments:
        seg_lower = segment.lower()
        for forbidden in forbidden_set:
            if forbidden.lower() in seg_lower:
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
    dynamic_forbidden = extract_gold_entities(news + mtr)
    full_forbidden_set = STRICT_FORBIDDEN | dynamic_forbidden
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
    
    # 合成數據 (x1)
    all_training_data.extend(synthetic_cleaned)
    
    # 新聞數據 (x10)
    if news: all_training_data.extend(news * 10)
    
    # 小說數據 (x1)
    if novel: 
        print(f"📉 小說數據權重降至 x1 (防止引入過多負樣本)")
        all_training_data.extend(novel * 1)
    
    # 港鐵數據 (x10)
    if mtr: all_training_data.extend(mtr * 10)

    # 5. 強制平衡機制 (Balancing)
    print("⚖️ 正在執行數據平衡 (Target: 負樣本佔總數 ~25%)...")
    
    pos_samples = [d for d in all_training_data if any(t != O_ID for t in d['ner_tags'])]
    neg_samples = [d for d in all_training_data if all(t == O_ID for t in d['ner_tags'])]
    
    print(f"   - 原始分佈 -> 正樣本: {len(pos_samples)} | 負樣本: {len(neg_samples)}")

    target_neg_count = int(len(pos_samples) * 0.35) 
    
    if len(neg_samples) > target_neg_count:
        print(f"   - ✂️ 削減負樣本: {len(neg_samples)} -> {target_neg_count}")
        neg_samples = random.sample(neg_samples, target_neg_count)
    else:
        print(f"   - ✅ 負樣本數量健康，無需削減。")
        
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