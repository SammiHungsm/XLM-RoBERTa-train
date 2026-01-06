import random
import json
from faker import Faker

# 引入自定義模組
# 注意：你需要確保 train/data_utils/__init__.py 存在
from data_utils.generators import get_random_fillers
from data_utils.loaders import load_names, load_addresses, load_negative_samples, load_pre_annotated_data
from data_utils.templates import get_all_templates

fake = Faker(['en_US', 'zh_TW'])

def create_dataset_safe(names, addresses, label2id, negative_texts=[], target_count=None):
    data = []
    templates = get_all_templates() # 從 templates.py 獲取
    
    if target_count is None: target_count = len(addresses)

    # 正負樣本比例 (85% : 15%)
    # 留意：templates 本身已經包含了很多對抗樣本 (Boundary/Anti-hallucination)
    # 這裡的 negative_texts 是指「純小說/新聞」文本
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
            # 檢查是否為變數
            if part in fillers:
                entity_text = fillers[part]
                entity_type = "O"
                if part == "{name}": entity_type = "NAME"
                elif part == "{addr}": entity_type = "ADDRESS"
                elif part == "{phone}": entity_type = "PHONE"
                elif part == "{id_num}": entity_type = "ID"
                elif part == "{account}": entity_type = "ACCOUNT"
                elif part == "{plate}": entity_type = "LICENSE_PLATE"
                elif part == "{org}": entity_type = "ORG"
                
                chars = list(entity_text)
                if not chars: continue
                full_tokens.extend(chars)
                if entity_type != "O":
                    full_tags.append(label2id[f"B-{entity_type}"])
                    full_tags.extend([label2id[f"I-{entity_type}"]] * (len(chars) - 1))
                else:
                    full_tags.extend([label2id["O"]] * len(chars))
            else:
                # 固定文字 (包括陷阱詞) 標記為 O
                chars = list(part)
                if not chars: continue
                full_tokens.extend(chars)
                full_tags.extend([label2id["O"]] * len(chars))
        
        data.append({"tokens": full_tokens, "ner_tags": full_tags})
    
    # 加入純文本負樣本 (Novel/News raw text)
    if negative_texts:
        for i in range(neg_count):
            sent = negative_texts[i % len(negative_texts)]
            full_tokens = list(sent)
            full_tags = [label2id["O"]] * len(full_tokens)
            data.append({"tokens": full_tokens, "ner_tags": full_tags})
    else:
        # Fallback Faker sentences
        for _ in range(neg_count):
            sent = fake.sentence()
            full_tokens = list(sent)
            full_tags = [label2id["O"]] * len(full_tokens)
            data.append({"tokens": full_tokens, "ner_tags": full_tags})

    random.shuffle(data)
    return data

if __name__ == "__main__":
    label_list = ["O", "B-NAME", "I-NAME", "B-ADDRESS", "I-ADDRESS", "B-PHONE", "I-PHONE", "B-ID", "I-ID", "B-ACCOUNT", "I-ACCOUNT", "B-LICENSE_PLATE", "I-LICENSE_PLATE", "B-ORG", "I-ORG"]
    label2id = {l: i for i, l in enumerate(label_list)}

    # 1. 載入外部數據
    names_pool = load_names("./Chinese-Names-Corpus-master") 
    addr_pool = load_addresses("./geojson_files")
    negative_pool = load_negative_samples("./negative_corpus", max_samples=10000)

    # 2. 生成合成數據
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