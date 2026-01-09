import json
import sys
import os

# ===========================
# 0. 環境設定 & 導入 Config (已強化)
# ===========================
# 自動獲取當前腳本所在的目錄 (src/training)
current_dir = os.path.dirname(os.path.abspath(__file__))
# 獲取專案根目錄 (即 src 的上一層)
project_root = os.path.dirname(os.path.dirname(current_dir))

# 將根目錄加入系統路徑，確保可以 import src
if project_root not in sys.path:
    sys.path.append(project_root)

try:
    from src.config import LABEL2ID, ID2LABEL, LABEL_LIST
except ImportError:
    print("❌ 錯誤：找不到 src.config。請確保你的專案結構正確 (src/config.py 存在)。")
    exit()

print(f"✅ 成功載入 Config。標籤總數: {len(LABEL_LIST)}")

# ===========================
# 1. 設定：負面樣本 (Negative Samples)
# ===========================
# 這些樣本用來教導模型「分辨邊界」，避免將長職銜誤判為 ORG
NEGATIVE_SAMPLES_RAW = [
    {
        "tokens": ["香", "港", "警", "務", "處", "前", "網", "絡", "安", "全", "及", "科", "技", "罪", "案", "調", "查", "科", "總", "警", "司", "陳", "先", "生"],
        "ner_tags": [
            "B-ORG", "I-ORG", "I-ORG", "I-ORG", "I-ORG", # 香港警務處 (ORG)
            "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", # 前網絡...科 (描述/部門)
            "O", "O", "O", # 總警司 (職位 -> O)
            "B-NAME", "I-NAME", "I-NAME" # 陳先生 (NAME - 必須跟 config 用 NAME 而非 PER)
        ]
    },
    {
        "tokens": ["資", "深", "網", "絡", "安", "全", "顧", "問", "及", "前", "任", "技", "術", "總", "監", "李", "大", "文", "表", "示"],
        "ner_tags": ["O"] * 20 
    },
    {
        "tokens": ["國", "立", "台", "灣", "大", "學", "生", "物", "資", "源", "暨", "農", "學", "院", "院", "長", "發", "言"],
        "ner_tags": [
            "B-ORG", "I-ORG", "I-ORG", "I-ORG", "I-ORG", "I-ORG", "I-ORG", "I-ORG", "I-ORG", "I-ORG", "I-ORG", "I-ORG", "I-ORG", "I-ORG", # 長機構名
            "O", "O", # 院長 (O)
            "O", "O"
        ]
    }
]

# 輔助函數：將文字標籤轉為 ID
def convert_samples_to_ids(samples):
    converted = []
    for item in samples:
        try:
            # 將 list 裡面的每個 tag string 轉成 int ID
            tag_ids = [LABEL2ID[t] for t in item["ner_tags"]]
            converted.append({"tokens": item["tokens"], "ner_tags": tag_ids})
        except KeyError as e:
            print(f"⚠️ 警告：負面樣本中有未知的標籤 {e}，請檢查 config.py。跳過此樣本。")
    return converted

# ===========================
# 2. 功能：檢查並修復過長 ORG (使用 ID 操作)
# ===========================
def fix_long_orgs(data_list):
    cleaned_count = 0
    clean_data = []
    
    # 職位關鍵字 (如果長 ORG 包含這些字，通常係標錯)
    JOB_TITLES = ["總警司", "總監", "經理", "主任", "主席", "會長", "專員", "代表", "發言人"]
    
    # 預先獲取 ORG 相關的 ID，避免迴圈內重複查表
    B_ORG_ID = LABEL2ID.get("B-ORG", -1)
    I_ORG_ID = LABEL2ID.get("I-ORG", -1)
    O_ID = LABEL2ID.get("O", 0)

    if B_ORG_ID == -1:
        print("❌ Config 中找不到 B-ORG，無法執行清洗。")
        return data_list

    for item in data_list:
        tokens = item["tokens"]
        tags = item["ner_tags"] # 這是 ID list [0, 13, 14...]
        
        new_tags = tags.copy()
        current_org_len = 0
        current_org_start = -1
        
        for i, tag_id in enumerate(tags):
            if tag_id == B_ORG_ID:
                current_org_len = 1
                current_org_start = i
            elif tag_id == I_ORG_ID and current_org_len > 0:
                current_org_len += 1
            else:
                # ORG 結束，檢查長度
                if current_org_len > 15: 
                    # 還原回文字來檢查內容
                    org_text = "".join(tokens[current_org_start : current_org_start + current_org_len])
                    
                    hit_title = any(title in org_text for title in JOB_TITLES)
                    
                    if hit_title:
                        # print(f"⚠️ 發現可疑長 ORG (長度 {current_org_len}): {org_text}")
                        # 修復策略：保留前 10 個 Token，後面全部改成 O_ID
                        for k in range(current_org_start + 10, current_org_start + current_org_len):
                            new_tags[k] = O_ID
                        # print(f"   -> 已修復: 後段已標為 O")
                        cleaned_count += 1
                        
                current_org_len = 0
                current_org_start = -1
        
        item["ner_tags"] = new_tags
        clean_data.append(item)
        
    print(f"🧹 清洗完成：共修復了 {cleaned_count} 條過長數據。")
    return clean_data

# ===========================
# 3. 主程式
# ===========================
if __name__ == "__main__":
    input_file = "train_data_lora.json"
    output_file = "train_data_lora_cleaned.json"
    
    print(f"📂 讀取 {input_file}...")
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            raw = json.load(f)
            # 兼容不同格式
            data = raw["data"] if isinstance(raw, dict) and "data" in raw else raw
    except FileNotFoundError:
        print("❌ 錯誤：找不到 train_data_lora.json。請先執行 prepare_data.py！")
        exit()

    # 1. 清洗數據 (Fix Long ORG)
    data = fix_long_orgs(data)
    
    # 2. 轉換並注入負面樣本 (Negative Samples)
    negative_data_ids = convert_samples_to_ids(NEGATIVE_SAMPLES_RAW)
    print(f"💉 注入 {len(negative_data_ids)} 條負面樣本 (已轉為 ID)...")
    data.extend(negative_data_ids)
    
    # 3. 儲存
    # 為了保持一致性，我們也把 id2label 存進去，方便 debug
    final_output = {
        "data": data,
        "label2id": LABEL2ID,
        "id2label": ID2LABEL
    }
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_output, f, ensure_ascii=False, indent=2)
        
    print(f"✅ 搞掂！新數據已儲存至 {output_file}")
    print(f"🚀 下一步：請執行 train_lora.py (確保它讀取 {output_file})")