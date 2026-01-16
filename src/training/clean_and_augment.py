import json
import os
import sys

# ===========================
# 0. 環境設定 & 導入 Config
# ===========================
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))

if project_root not in sys.path:
    sys.path.append(project_root)

try:
    from src.config import LABEL2ID, ID2LABEL, LABEL_LIST
except ImportError:
    print("❌ 錯誤：找不到 src.config。請確保你的專案結構正確 (src/config.py 存在)。")
    exit()

print(f"✅ 成功載入 Config。標籤總數: {len(LABEL_LIST)}")

# ===========================
# 1. 定義關鍵字 (Keywords)
# ===========================

# 職位關鍵字 (如果長 ORG 包含這些字，通常係標錯，需要切斷)
TITLE_KEYWORDS = [
    "總裁", "主席", "經理", "總監", "主任", "特首", "司長", "局長", "處長", 
    "曾任", "前任", "兼任", "現任", "副總", "CEO", "CFO", "COO", 
    "創辦人", "負責人", "發言人", "顧問", "專家", "教授", "博士",
    "先生", "女士", "小姐", "總警司", "警司", "會長", "專員", "代表"
]

# 泛區域關鍵字 (單獨出現時視為 O，避免作為 ADDRESS 或 ORG)
# 這些詞在沒有具體街道/大廈時，通常是噪音
BROAD_REGIONS = {"香港", "九龍", "新界", "澳門", "中國", "大灣區", "中環", "旺角", "尖沙咀", "銅鑼灣"}

# ===========================
# 2. 設定：負面樣本 (Negative Samples)
# ===========================
NEGATIVE_SAMPLES_RAW = [
    {
        "tokens": ["香", "港", "警", "務", "處", "前", "網", "絡", "安", "全", "及", "科", "技", "罪", "案", "調", "查", "科", "總", "警", "司", "陳", "先", "生"],
        "ner_tags": [
            "B-ORG", "I-ORG", "I-ORG", "I-ORG", "I-ORG", # 香港警務處
            "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", # 部門描述 (O)
            "O", "O", "O", # 總警司 (O)
            "B-NAME", "I-NAME", "I-NAME" # 陳先生
        ]
    },
    {
        "tokens": ["資", "深", "網", "絡", "安", "全", "顧", "問", "及", "前", "任", "技", "術", "總", "監", "李", "大", "文", "表", "示"],
        "ner_tags": ["O"] * 20 
    },
    {
        "tokens": ["國", "立", "台", "灣", "大", "學", "生", "物", "資", "源", "暨", "農", "學", "院", "院", "長", "發", "言"],
        "ner_tags": [
            "B-ORG", "I-ORG", "I-ORG", "I-ORG", "I-ORG", "I-ORG", "I-ORG", "I-ORG", "I-ORG", "I-ORG", "I-ORG", "I-ORG", "I-ORG", "I-ORG", # 機構名
            "O", "O", # 院長 (O)
            "O", "O"
        ]
    },
    # 新增：針對項目 vs 機構的負樣本
    {
        "tokens": ["屯", "馬", "線", "係", "一", "條", "好", "方", "便", "既", "鐵", "路", "。"],
        "ner_tags": ["O"] * 13
    }
]

def convert_samples_to_ids(samples):
    converted = []
    for item in samples:
        try:
            tag_ids = [LABEL2ID[t] for t in item["ner_tags"]]
            converted.append({"tokens": item["tokens"], "ner_tags": tag_ids})
        except KeyError as e:
            print(f"⚠️ 警告：負面樣本中有未知的標籤 {e}，請檢查 config.py。跳過此樣本。")
    return converted

# ===========================
# 3. 核心功能：修復錯誤實體
# ===========================
def fix_bad_entities(data_list):
    """
    🔥 綜合修復函數
    1. 移除單獨出現的泛區域 (Broad Regions -> O)
    2. 切斷包含職位的過長實體 (Long Entity with Title -> O)
    """
    fixed_count = 0
    cleaned_data = []

    # 預先獲取 ID，提升效能
    O_ID = LABEL2ID.get("O", 0)

    for item in data_list:
        tokens = item["tokens"]
        tags = item["ner_tags"]
        
        # 1. 提取所有實體片段 (Start, End, TagID)
        # 邏輯：掃描 B-Tag 開頭，直到非 I-Tag
        entities = []
        i = 0
        while i < len(tags):
            tag = tags[i]
            # 假設 ID 結構：單數是 B (e.g., 1, 3, ...)，偶數是 I (2, 4, ...)
            # 或者直接判斷是否不為 O
            if tag != O_ID:
                # 簡單起見，我們將連續的非 O 視為一個實體候選
                # (更嚴謹的做法是檢查 BIO 轉換，但這裡為了捕捉所有潛在長實體，寬鬆一點也無妨)
                start = i
                current_tag_base = tag # 記住開始的 Tag
                i += 1
                while i < len(tags) and tags[i] != O_ID:
                    # 如果遇到另一個 B-Tag (且 ID 不同)，視為新實體，斷開
                    # 這裡簡化：只要不是 O 就繼續連，因為我們要抓的是連錯的情況
                    i += 1
                end = i
                entities.append((start, end))
            else:
                i += 1
        
        new_tags = list(tags)
        modified = False
        
        for start, end in entities:
            entity_tokens = tokens[start:end]
            entity_text = "".join(entity_tokens)
            
            # --- 規則 A: 過濾泛區域 (Broad Regions) ---
            # 條件：文字在泛區域清單中 且 長度很短 (<=3)
            # 例如 "香港" (2字) -> 殺， "香港大學" (4字) -> 留
            is_broad = entity_text in BROAD_REGIONS
            is_too_short = len(entity_text) <= 3 
            
            if is_broad and is_too_short:
                # print(f"  🔪 移除泛區域噪音: {entity_text}")
                for k in range(start, end):
                    new_tags[k] = O_ID
                modified = True
                continue

            # --- 規則 B: 過濾含職位的長實體 (Overly Long with Title) ---
            # 條件：長度 > 12 且 包含職位關鍵字
            if len(entity_text) > 12:
                hit_title = any(t in entity_text for t in TITLE_KEYWORDS)
                
                if hit_title:
                    # print(f"  🔪 切斷含職位長實體: {entity_text}")
                    # 策略：因為很難精確切分，為了安全，將整段標記為 O (視為負樣本)
                    # 或者：您可以選擇只保留前 5-8 個字，後面變 O
                    # 這裡採用「全殺」策略，避免教錯模型
                    for k in range(start, end):
                        new_tags[k] = O_ID
                    modified = True
                    continue

        if modified:
            fixed_count += 1
            item["ner_tags"] = new_tags
        
        cleaned_data.append(item)

    print(f"🧹 清洗完成：共修復了 {fixed_count} 條包含「泛區域」或「職位混合」的錯誤數據。")
    return cleaned_data

# ===========================
# 4. 主程式
# ===========================
if __name__ == "__main__":
    input_file = "train_data_lora.json"
    output_file = "train_data_lora_cleaned.json"
    
    print(f"📂 讀取 {input_file}...")
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            raw = json.load(f)
            data = raw["data"] if isinstance(raw, dict) and "data" in raw else raw
    except FileNotFoundError:
        print("❌ 錯誤：找不到 train_data_lora.json。請先執行 prepare_data.py！")
        exit()

    # 1. 執行核心清洗 (修復泛區域 & 長實體)
    data = fix_bad_entities(data)
    
    # 2. 注入負面樣本
    negative_data_ids = convert_samples_to_ids(NEGATIVE_SAMPLES_RAW)
    print(f"💉 注入 {len(negative_data_ids)} 條負面樣本 (已轉為 ID)...")
    data.extend(negative_data_ids)
    
    # 3. 儲存
    final_output = {
        "data": data,
        "label2id": LABEL2ID,
        "id2label": ID2LABEL
    }
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_output, f, ensure_ascii=False, indent=2)
        
    print(f"✅ 搞掂！新數據已儲存至 {output_file}")
    print(f"🚀 下一步：請執行 train_lora.py (確保它讀取 {output_file})")