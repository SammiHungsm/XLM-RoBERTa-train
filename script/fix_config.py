import json
import os

# 模型路徑
model_path = "./my_merged_presidio_model"
config_path = os.path.join(model_path, "config.json")

# 1. 讀取現有的 Config
with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)

print(f"當前模型標籤數量: {len(config.get('id2label', {}))}")

# 2. 定義正確的標籤對應 (根據你的 Log 推算)
# 邏輯：Model 捉到的 LABEL_1 是 Sam (B-NAME), LABEL_2 是 mi (I-NAME)
# LABEL_4 是 Address 後半, LABEL_6 是 Phone 後半... 推導出以下順序：
correct_id2label = {
    "0": "O",
    "1": "B-NAME",
    "2": "I-NAME",
    "3": "B-ADDRESS",
    "4": "I-ADDRESS",
    "5": "B-PHONE",
    "6": "I-PHONE",
    "7": "B-ID",
    "8": "I-ID",
    "9": "B-ACCOUNT",
    "10": "I-ACCOUNT"
}

correct_label2id = {v: int(k) for k, v in correct_id2label.items()}

# 3. 寫入 Config
config["id2label"] = correct_id2label
config["label2id"] = correct_label2id

# 4. 儲存
with open(config_path, "w", encoding="utf-8") as f:
    json.dump(config, f, indent=2, ensure_ascii=False)

print("✅ Config 修復完成！標籤名稱已寫入。")
print(f"請重新執行: python script/run_presidio_custom.py")