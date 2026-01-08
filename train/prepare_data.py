import random
import json
import re
from faker import Faker
from data_utils.tokenizer import smart_tokenize

# 引入自定義模組
# 注意：你需要確保 train/data_utils/__init__.py 存在
from data_utils.generators import get_random_fillers
from data_utils.loaders import load_names, load_addresses, load_negative_samples, load_pre_annotated_data
from data_utils.templates import get_all_templates

fake = Faker(['en_US', 'zh_TW'])

def smart_tokenize(text):
    """
    智能切分 (改良版 - 去除純空格 token)：
    1. 中文/符號：按字切分
    2. 英文/數字：按單詞切分
    3. 過濾掉純空格
    """
    result = []
    current_eng = ""
    
    # 遍歷每一個字符
    for char in text:
        # 如果是英文或數字，暫存到 current_eng
        if re.match(r'[a-zA-Z0-9]', char):
            current_eng += char
        else:
            # 如果遇到非英文數字 (如中文、空格、標點)
            
            # 1. 先結算之前的英文詞
            if current_eng:
                result.append(current_eng)
                current_eng = ""
            
            # 2. 處理當前字符：只有當它「不是空格」時才加入
            if char.strip():  # <--- 新增這行檢查！
                result.append(char)
            
    # 循環結束後，檢查是否有遺留的英文詞
    if current_eng:
        result.append(current_eng)
        
    return result

def create_dataset_safe(names, addresses, label2id, negative_texts=[], target_count=None):
    data = []
    templates = get_all_templates() # 從 templates.py 獲取
    
    if target_count is None: target_count = len(addresses)

    # 正負樣本比例 (85% : 15%)
    pos_count = int(target_count * 0.85)
    neg_count = target_count - pos_count
    
    print(f"🚀 生成數據中... (Template生成: {pos_count}, 純文本負樣本: {neg_count})")
    
    for _ in range(pos_count):
        template_parts = random.choice(templates)
        
        # 使用 generators.py 的邏輯獲取填充內容
        fillers = get_random_fillers(names, addresses)
        
        full_tokens = []
        full_tags = []
        
        for part in template_parts:
            # 1. 獲取文本內容
            text_segment = ""
            entity_type = "O"
            
            if part in fillers:
                text_segment = fillers[part]
                # 判斷實體類型
                if part == "{name}": entity_type = "NAME"
                elif part == "{addr}": entity_type = "ADDRESS"
                elif part == "{phone}": entity_type = "PHONE"
                elif part == "{id_num}": entity_type = "ID"
                elif part == "{account}": entity_type = "ACCOUNT"
                elif part == "{plate}": entity_type = "LICENSE_PLATE"
                elif part == "{org}": entity_type = "ORG"
            else:
                # 固定文字 (包括陷阱詞)
                text_segment = part

            # 2. 使用 Smart Tokenize 代替 list() [核心修改點]
            tokens = smart_tokenize(text_segment)
            
            if not tokens: continue
            
            full_tokens.extend(tokens)
            
            # 3. 生成對應的 Tags (按 Token 數量)
            if entity_type != "O":
                # 第一個 token 是 B-TAG
                full_tags.append(label2id[f"B-{entity_type}"])
                # 剩下的 tokens 是 I-TAG
                if len(tokens) > 1:
                    full_tags.extend([label2id[f"I-{entity_type}"]] * (len(tokens) - 1))
            else:
                full_tags.extend([label2id["O"]] * len(tokens))
        
        data.append({"tokens": full_tokens, "ner_tags": full_tags})
    
    # 加入純文本負樣本 (Novel/News raw text)
    if negative_texts:
        for i in range(neg_count):
            sent = negative_texts[i % len(negative_texts)]
            # 這裡也改用 smart_tokenize
            full_tokens = smart_tokenize(sent)
            full_tags = [label2id["O"]] * len(full_tokens)
            data.append({"tokens": full_tokens, "ner_tags": full_tags})
    else:
        # Fallback Faker sentences
        for _ in range(neg_count):
            sent = fake.sentence()
            full_tokens = smart_tokenize(sent)
            full_tags = [label2id["O"]] * len(full_tokens)
            data.append({"tokens": full_tokens, "ner_tags": full_tags})

    random.shuffle(data)
    return data

if __name__ == "__main__":
    label_list = ["O", "B-NAME", "I-NAME", "B-ADDRESS", "I-ADDRESS", "B-PHONE", "I-PHONE", "B-ID", "I-ID", "B-ACCOUNT", "I-ACCOUNT", "B-LICENSE_PLATE", "I-LICENSE_PLATE", "B-ORG", "I-ORG"]
    label2id = {l: i for i, l in enumerate(label_list)}

    # 1. 載入外部數據 (請確保這些路徑下的文件存在)
    # 建議：可以使用 Config 字典管理路徑，但為了保持代碼簡單，這裡維持原樣
    try:
        names_pool = load_names("./Chinese-Names-Corpus-master") 
        addr_pool = load_addresses("./geojson_files")
        negative_pool = load_negative_samples("./negative_corpus", max_samples=10000)
    except FileNotFoundError as e:
        print(f"⚠️ 警告：找不到數據文件 ({e})，請檢查路徑。將使用空數據繼續...")
        names_pool, addr_pool, negative_pool = [], [], []

    # 2. 生成合成數據
    # 注意：如果 addr_pool 為空，這裡可能會報錯或生成空數據
    training_data = create_dataset_safe(
        names_pool, 
        addr_pool, 
        label2id, 
        negative_texts=negative_pool,
        target_count=50000 
    )

    # 3. 合併預處理數據 (進行 Upsampling / 倍增)
    # 我們將真實數據重複多次，確保模型在訓練時「多看幾眼」
    novel_data = load_pre_annotated_data("novel_data.json")
    news_data = load_pre_annotated_data("news_data.json")
    mtr_data = load_pre_annotated_data("mtr_news_data.json")

    # 小說數據量尚可，重複 5 次
    if novel_data:
        print(f"📈 將小說數據倍增 5 倍 (總數: {len(novel_data) * 5})")
        training_data.extend(novel_data * 5)

    # 新聞數據極少但極重要 (教導忽略數字)，重複 50 次！
    if news_data:
        print(f"📈 將鐵路新聞數據倍增 50 倍 (總數: {len(news_data) * 50})")
        training_data.extend(news_data * 50)

    # 港鐵數據是混合樣本，重複 50 次！
    if mtr_data:
        print(f"📈 將港鐵新聞數據倍增 50 倍 (總數: {len(mtr_data) * 50})")
        training_data.extend(mtr_data * 50)
        
    random.shuffle(training_data)
    print(f"🚀 最終數據集總量: {len(training_data)} 條")

    output_data = {
        "data": training_data, 
        "label2id": label2id, 
        "id2label": {str(v): k for k, v in label2id.items()}
    }
    
    with open("train_data_lora.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False)
        
    print("✅ 數據準備完成！train_data_lora.json 已更新。")