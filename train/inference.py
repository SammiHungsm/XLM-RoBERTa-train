from transformers import pipeline

# 載入您剛剛訓練好的模型
model_path = "./my_pii_model"

print("正在載入模型...")
nlp = pipeline("ner", model=model_path, aggregation_strategy="simple")

# 測試句子
test_sentences = [
    "陳大文住在新界元朗區仁壽圍31號。",
    "Please send the parcel to Flat 5, 12/F, Block A, 123 Nathan Road, Kowloon.",
    "我的身份證號碼是K123456(7)，請以此登記。",
    "王小明住在九龍旺角通菜街88號。"
]

print("-" * 30)
for text in test_sentences:
    results = nlp(text)
    print(f"\n原文: {text}")
    if not results:
        print("沒有偵測到敏感資料。")
    for entity in results:
        print(f" -> 發現: {entity['word']} | 類型: {entity['entity_group']} | 分數: {entity['score']:.4f}")