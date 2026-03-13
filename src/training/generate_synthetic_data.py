import json
import os
import random
import sys
from tqdm import tqdm
from faker import Faker

# 設定路徑以便讀取 src 模組
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.utils.tokenizer import smart_tokenize
# 🔥 [Fix] 使用 PIIDataGenerator 類別，而非舊的 get_random_fillers 函數
from src.utils.generators import PIIDataGenerator
from src.utils.loaders import load_names, load_addresses, load_negative_samples
from src.utils.templates import get_all_templates
from src.config import LABEL2ID

fake = Faker(['zh_TW', 'en_US'])

# ===========================
# 🛡️ 禁止名單設定
# ===========================
CRITICAL_FORBIDDEN = [
    "中國", "國鐵", "港鐵", "MTR", "鐵路", "集團", "有限公司", 
    "十四五", "十五五", "建設", "發展", "高鐵", "銀行", "分行"
]

def align_tokens_and_labels(text, entities, tokens):
    """
    🔥 核心對齊函數：將 Generator 產生的字元級別 (Character-level) 實體
    轉換為訓練所需的 Token 級別 (Token-level) BIO 標籤。
    """
    tags = ["O"] * len(tokens)
    
    # 1. 建立 Token 到字元位置的映射 (Token Spans)
    token_spans = []
    current_char = 0
    for token in tokens:
        # 尋找 token 在原文中的位置
        # 注意：smart_tokenize 可能會去除空格，這裡做簡單的查找
        start = text.find(token, current_char)
        if start == -1: 
            # 如果找不到 (罕見情況)，假設緊接上一個
            start = current_char 
        end = start + len(token)
        token_spans.append((start, end))
        current_char = end # 移動指針
        
    # 2. 標註實體
    for ent in entities:
        start_char = ent['start']
        end_char = ent['end']
        label = ent['label']
        
        # 找出這個實體覆蓋了哪些 Token
        ent_token_indices = []
        for idx, (t_start, t_end) in enumerate(token_spans):
            # 判斷重疊：Token 的範圍與實體範圍有交集
            # t_end > start_char AND t_start < end_char
            if t_end > start_char and t_start < end_char:
                ent_token_indices.append(idx)
                
        if not ent_token_indices:
            continue
            
        # 3. 賦予 BIO 標籤
        first = True
        for idx in ent_token_indices:
            if first:
                tags[idx] = f"B-{label}"
                first = False
            else:
                tags[idx] = f"I-{label}"
                
    # 4. 轉換為 ID
    tag_ids = []
    for t in tags:
        tag_ids.append(LABEL2ID.get(t, LABEL2ID["O"]))
        
    return tag_ids

def generate_synthetic(target_count=30000): # 建議數量提升至 3萬+
    print("📂 [1/4] 正在載入基礎語料庫...")
    
    # 1. 載入名字
    raw_names_data = load_names("./data/raw/Chinese-Names-Corpus-master")
    
    # 2. 載入地址 (Loaders 現在會返回分類好的地址)
    # full_addrs: 完整地址 (e.g. 屯門市廣場) -> 用於正樣本
    # location_frags: 地名碎片 (e.g. 屯門) -> 用於負樣本或低權重生成
    full_addrs, location_frags = load_addresses("./data/raw/geojson_files", "./data/raw/train.jsonl")
    
    # 清洗名字
    standard_clean = [n for n in raw_names_data["standard"] if not any(w in n for w in CRITICAL_FORBIDDEN)]
    trans_clean = [n for n in raw_names_data["transliterated"] if not any(w in n for w in CRITICAL_FORBIDDEN)]
    names_data = {"standard": standard_clean, "transliterated": trans_clean}
    
    print("⚙️ [2/4] 初始化 PIIDataGenerator (注入噪音策略)...")
    
    # 獲取所有模板 (已統一為字串列表)
    all_templates = get_all_templates()
    templates_dict = {"default": all_templates}
    
    # 🔥 初始化新版生成器
    generator = PIIDataGenerator(
        full_addresses=full_addrs,
        locations=location_frags,
        names_dict=names_data,
        templates=templates_dict
    )
    
    # 3. 載入真實負樣本 (用於混合)
    print("🛡️ [3/4] 載入真實負樣本...")
    existing_jsons = [
        "./data/raw/news_data.json", 
        "./data/raw/novel_data.json", 
        "./data/raw/mtr_news_data.json"
    ]
    # 確保這些檔案存在，否則傳空列表
    valid_paths = [p for p in existing_jsons if os.path.exists(p)]
    real_negative_samples = load_negative_samples(valid_paths, max_samples=8000)
    
    data = []
    print(f"🚀 [4/4] 開始生成數據... 目標: {target_count}")
    
    with tqdm(total=target_count) as pbar:
        while len(data) < target_count:
            # 80% 正樣本 (由 Generator 生成，含噪音), 20% 純負樣本
            is_positive = random.random() < 0.80
            
            if is_positive:
                # ✅ 使用 Generator 生成
                # 這會自動處理地址噪音、年齡邊界、列表分隔等邏輯
                sample = generator.generate_sample("default")
                if not sample: continue
                
                text = sample['text']
                entities = sample['entities']
                
                # 安全檢查
                if any(word in text for word in CRITICAL_FORBIDDEN): continue

                # Tokenization & Tagging
                tokens = smart_tokenize(text)
                tags = align_tokens_and_labels(text, entities, tokens)
                
            else:
                # ❌ 負樣本 (全 O)
                if real_negative_samples and random.random() < 0.7:
                    text = random.choice(real_negative_samples)
                else:
                    text = fake.sentence()
                    
                if any(word in text for word in CRITICAL_FORBIDDEN): continue
                
                tokens = smart_tokenize(text)
                tags = [LABEL2ID["O"]] * len(tokens)
            
            # 最終校對：長度必須一致且非空
            if len(tokens) == len(tags) and len(tokens) > 0:
                data.append({"tokens": tokens, "ner_tags": tags})
                pbar.update(1)
                
    return data

if __name__ == "__main__":
    target = 30000 
    results = generate_synthetic(target_count=target)
    
    output_path = "train_data_lora.json" # 直接輸出清洗好的格式
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
        
    print(f"✅ 生成完成！數據已儲存至: {output_path}")
    print("💡 提示：此檔案已包含 token 和 ner_tags，可直接用於訓練 (跳過 prepare_data.py 的標註步驟)")