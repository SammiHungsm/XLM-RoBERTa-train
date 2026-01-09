import json
import os
import random
import sys

# 加入路徑以引用 src.config
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(project_root)

from src.config import LABEL2ID, ID2LABEL

# 零錯誤過濾名單 (與合成腳本保持一致)
STRICT_FORBIDDEN = ["中國", "國鐵", "港鐵", "MTR", "鐵路", "集團", "有限公司", "十四五", "十五五"]

def load_json(path):
    if not os.path.exists(path):
        print(f"⚠️ 找不到檔案: {path}")
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def is_clean(item):
    """
    零錯誤防線：檢查合成數據中是否有任何禁止詞被標記為 'O' (0)
    """
    tokens = item.get("tokens", [])
    tags = item.get("ner_tags", [])
    
    for i, t in enumerate(tokens):
        # 如果 Token 包含禁止詞，但標籤卻是 0 (O)
        if any(word in t for word in STRICT_FORBIDDEN) and tags[i] == 0:
            return False
    return True

if __name__ == "__main__":
    # 1. 讀取各方來源
    news = load_json("./data/raw/news_data.json")
    novel = load_json("./data/raw/novel_data.json")
    mtr = load_json("./data/raw/mtr_news_data.json")
    synthetic_raw = load_json("./data/raw/synthetic_data.json")

    # 2. 🛡️ 執行零錯誤過濾 (針對合成數據)
    print(f"🛡️ 正在執行合成數據最終清洗 (原始數量: {len(synthetic_raw)})...")
    synthetic_cleaned = [d for d in synthetic_raw if is_clean(d)]
    removed_count = len(synthetic_raw) - len(synthetic_cleaned)
    if removed_count > 0:
        print(f"🚫 已自動剔除 {removed_count} 條標籤污染的合成樣本。")

    all_training_data = []

    # 3. 按權重合併數據
    # 權重分配邏輯說明：
    # - 新聞與 MTR 數據修正後精確度最高且具備鐵路專業知識，需強行增強記憶 (x50)
    # - 小說數據用於學習口語與姓名 (x5)
    # - 合成數據用於學習身分證/電話等格式 (x1)
    
    all_training_data.extend(synthetic_cleaned)   # 基數大，不重複
    all_training_data.extend(news * 50)           # 重要新聞
    all_training_data.extend(novel * 5)           # 小說文本
    all_training_data.extend(mtr * 50)            # 港鐵數據

    # 4. 打散數據
    random.shuffle(all_training_data)

    # 5. 封裝並輸出
    output = {
        "data": all_training_data,
        "label2id": LABEL2ID,
        "id2label": ID2LABEL
    }

    output_path = "train_data_lora.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"🚀 最終訓練集打包完成！")
    print(f"📊 總樣本數: {len(all_training_data)}")
    print(f"📁 檔案已儲存至: {output_path}")