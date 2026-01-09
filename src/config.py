# src/config.py

# 基礎模型
BASE_MODEL_NAME = "Davlan/xlm-roberta-large-ner-hrl"

# 你的 Label List (集中管理)
LABEL_LIST = [
    "O", 
    "B-NAME", "I-NAME", 
    "B-ADDRESS", "I-ADDRESS", 
    "B-PHONE", "I-PHONE", 
    "B-ID", "I-ID", 
    "B-ACCOUNT", "I-ACCOUNT", 
    "B-LICENSE_PLATE", "I-LICENSE_PLATE",
    "B-ORG", "I-ORG"
]

# 自動生成 ID Map
LABEL2ID = {l: i for i, l in enumerate(LABEL_LIST)}
ID2LABEL = {i: l for l, i in LABEL2ID.items()}