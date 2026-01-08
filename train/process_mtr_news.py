import json
import re
# ✅ 引入共用的 tokenizer
from data_utils.tokenizer import smart_tokenize 

# ==========================================
# 1. 定義要標註的「實體名單」
# ==========================================
target_names = ["楊美珍", "金澤培"]
target_orgs = ["港鐵"]

# ==========================================
# 2. 原始文本
# ==========================================
raw_content = """港鐵新任行政總裁楊美珍昨履新，她今早（2日）於港鐵總部會見傳媒，稱上任後工作重點包括推進6個新鐵路項目，專注工程和財務管理及建設高峰期的現金流，亦會積極用好科技及人工智能去面對挑戰，同時發展開拓不同業務。楊美珍又表示，著重與員工溝通，盼締造良好工作環境讓員工發揮所長。

楊美珍原是港鐵常務總監（香港客運服務），昨日起接替金澤培升任行政總裁。她稱加入港鐵已26年，明白新崗位責任重大，會關心明白乘客需要並不斷提升鐵路服務，與時並進，同時鞏固鐵路資產、質素及韌性。
她又說，港鐵目前另一重任是推進6個涉及大嶼山、屯門及北都的鐵路新項目，未計及北環線部分的投資已涉1400億元，將在2027年至2034年帶來逾20個新車站，工程及財務管理將屬工作重點。楊提到，港鐵去年有不同組合應付現金流需要，將持續利用相關做法，認為現時管理現金流方面做得不錯。
楊美珍續稱，港鐵鐵路服務是香港民生及經濟的重要基建設施，必須讓其能持續發展，面對乘客需求轉變、市場及環境變化等挑戰，會努力積極利用人工智能，以創新、提升服務和營運效率，同時保持競爭力，透露現正有不同AI方面的測試及實驗，目標是將更多相關計劃落實及擴大。
楊美珍亦表示，港鐵有優秀的團隊，想為員工締造良好工作平台，期望加強工作文化及溝通。

原文網址：https://news.mingpao.com/ins/%E6%B8%AF%E8%81%9E/article/20260102/s00001/1767321394120"""

# ==========================================
# 3. 處理邏輯 (已修正為 Word-level 兼容)
# ==========================================
def process_data(text):
    # A. 移除 URL
    if "原文網址：" in text:
        text = text.split("原文網址：")[0]

    # B. 分句
    sentences = re.split(r'([。！？\n])', text)
    segments = []
    current_sent = ""
    for s in sentences:
        current_sent += s
        if re.match(r'[。！？\n]', s):
            if current_sent.strip():
                segments.append(current_sent.strip())
            current_sent = ""
    if current_sent.strip(): segments.append(current_sent.strip())

    # C. 自動標註
    label2id = {
        "O": 0, "B-NAME": 1, "I-NAME": 2, 
        "B-ADDRESS": 3, "I-ADDRESS": 4, 
        "B-PHONE": 5, "I-PHONE": 6, 
        "B-ID": 7, "I-ID": 8, 
        "B-ACCOUNT": 9, "I-ACCOUNT": 10,
        "B-LICENSE_PLATE": 11, "I-LICENSE_PLATE": 12,
        "B-ORG": 13, "I-ORG": 14
    }

    final_data = []

    for sent in segments:
        # [修正 1] 使用 smart_tokenize (Word-level)
        tokens = smart_tokenize(sent) 
        tags = [label2id["O"]] * len(tokens)
        
        # [修正 2] 建立 Token 與 字符位置 的映射 (Token Spans)
        # 這是最關鍵的一步：確保不管是 "MTR" (len 3) 還是 "楊" (len 1) 都能對準位置
        token_spans = []
        search_start = 0
        for token in tokens:
            # 在句子中尋找這個 token 的真實位置
            start = sent.find(token, search_start)
            if start == -1: 
                token_spans.append(None)
                continue
            end = start + len(token)
            token_spans.append((start, end)) # 記錄 (開始, 結束)
            search_start = end

        # 定義一個通用的標註函數
        def apply_labels(targets, label_b, label_i):
            for target in targets:
                # 使用 re.escape 避免名字中有特殊符號導致 regex 報錯
                for match in re.finditer(re.escape(target), sent):
                    match_start, match_end = match.span()
                    
                    # 檢查每一個 Token 是否落在這個 match 的範圍內
                    for idx, span in enumerate(token_spans):
                        if span is None: continue
                        t_start, t_end = span
                        
                        # 如果 Token 的範圍完全在 match 範圍內
                        if t_start >= match_start and t_end <= match_end:
                            # 如果是該實體的開頭
                            if t_start == match_start:
                                if tags[idx] == label2id["O"]: # 避免覆蓋
                                    tags[idx] = label2id[label_b]
                            else:
                                if tags[idx] == label2id["O"]:
                                    tags[idx] = label2id[label_i]

        # 執行標註
        apply_labels(target_names, "B-NAME", "I-NAME")
        apply_labels(target_orgs, "B-ORG", "I-ORG")
        
        if len(tokens) > 0:
            final_data.append({
                "tokens": tokens,
                "ner_tags": tags
            })
            
    return final_data

# ==========================================
# 4. 執行與儲存
# ==========================================
# 注意：這裡輸出檔名改為 news_data.json 以區分 mtr_news
mtr_json_data = process_data(raw_content)

output_file = "news_data.json" 
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(mtr_json_data, f, ensure_ascii=False, indent=2)

print(f"✅ 處理完成！共生成 {len(mtr_json_data)} 條混合數據。")
print(f"   - 已標註 NAME: {target_names}")
print(f"   - 已標註 ORG:  {target_orgs}")
print(f"📁 檔案已儲存為: {output_file}")