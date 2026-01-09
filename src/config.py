# src/config.py

# 模型路徑
BASE_MODEL_NAME = "Davlan/xlm-roberta-large-ner-hrl"
LORA_MODEL_PATH = "./final_lora_model"

# 標籤定義
LABEL_LIST = [
    "O", "B-NAME", "I-NAME", "B-ADDRESS", "I-ADDRESS", "B-PHONE", "I-PHONE", 
    "B-ID", "I-ID", "B-ACCOUNT", "I-ACCOUNT", "B-LICENSE_PLATE", "I-LICENSE_PLATE",
    "B-ORG", "I-ORG"
]

# 自動生成 Mapping
LABEL2ID = {l: i for i, l in enumerate(LABEL_LIST)}
ID2LABEL = {i: l for l, i in LABEL2ID.items()}

# 過濾規則
BLACKLIST = ["健在", "不詳", "未知", "無業", "離異", "單身", "不便", "整合", "處理", "錯誤", "高度", "闊度"]
CANTONESE_NOISE = ["黎", "係", "打", "之前", "主席", "職", "仲要", "搵"]
STRICT_FORBIDDEN = ["中國", "國鐵", "港鐵", "MTR", "鐵路", "集團", "有限公司", "十四五", "十五五"]

# 推論參數
MIN_SCORE_THRESHOLD = 0.45
MAX_SEQ_LENGTH = 384