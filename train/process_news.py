import json
import re
# ✅ 引入共用的 tokenizer
from data_utils.tokenizer import smart_tokenize 

# ==========================================
# 1. 定義要標註的清單
# ==========================================

# A. 機構 (ORG)
target_orgs = [
    "中國國家鐵路集團有限公司",
    "國鐵集團"
]

# B. 地名/地址 (ADDRESS) - ✅ 新增這個！
# 根據你的新聞內容，我提取了出現過的地點
target_addrs = [
    "大嶼山", "屯門", "北都", 
    "長贛", "瀋白", # 雖然是高鐵線名，但通常包含地名，視乎你想不想標
    "香港", "中國"
]

# ==========================================
# 2. 原始文本 (不變)
# ==========================================
raw_content = """據中國國家鐵路集團有限公司今（4日）披露，鐵路「十四五」實現圓滿收官。「十四五」期間，全國鐵路營業里程由14.63萬公里增至16.5萬公里、增長12.8%，高鐵由3.79萬公里增至5.04萬公里、增長32.98%，中國建成世界規模最大、先進發達的高速鐵路網。

2025年，國鐵集團加快建設現代化鐵路基礎設施體系，圓滿完成鐵路建設任務，全國鐵路完成固定資產投資9015億元人民幣、同比增長6%，投產新線3109公里，其中高鐵2862公里，鐵路投資拉動作用充分顯現。

2025年，國鐵集團以國家「十四五」規劃綱要確定的102項重大工程鐵路項目和「兩重」項目為重點，加大實施力度，長贛高鐵等8個項目開工建設，瀋白高鐵等25個項目開通運營。加快物流基礎設施建設，建成鐵路專用線52條。

「十五五」期間，國鐵集團將進一步推進鐵路網建設。到2030年，全國鐵路營業里程達到18萬公里左右，其中高鐵6萬公里左右，復線率和電氣化率分別達到64%和78%，戰略骨幹通道全面加強，「八縱八橫」高鐵系統成網，區域互聯互通水平顯著提升，貨運網絡能力大幅增強，基本建成世界一流的現代化鐵路網。

原文網址：https://news.mingpao.com/ins/%E5%85%A9%E5%B2%B8/article/20260104/s00004/1767518315152"""

# ==========================================
# 3. 處理邏輯
# ==========================================
def process_news(text):
    # A. 簡單清洗
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
        tokens = smart_tokenize(sent)
        tags = [label2id["O"]] * len(tokens)
        
        # 建立 Alignment 映射
        token_spans = []
        search_start = 0
        for token in tokens:
            start = sent.find(token, search_start)
            if start == -1:
                token_spans.append(None)
                continue
            end = start + len(token)
            token_spans.append((start, end))
            search_start = end

        # 定義標註函數
        def apply_labels(targets, label_b, label_i):
            for target in targets:
                for match in re.finditer(re.escape(target), sent):
                    match_start, match_end = match.span()
                    
                    for idx, span in enumerate(token_spans):
                        if span is None: continue
                        t_start, t_end = span
                        
                        if t_start >= match_start and t_end <= match_end:
                            if t_start == match_start:
                                if tags[idx] == label2id["O"]:
                                    tags[idx] = label2id[label_b]
                            else:
                                if tags[idx] == label2id["O"]:
                                    tags[idx] = label2id[label_i]

        # 執行標註
        # 1. 標註機構
        apply_labels(target_orgs, "B-ORG", "I-ORG")
        
        # 2. 標註地名 ✅ (新增這行)
        apply_labels(target_addrs, "B-ADDRESS", "I-ADDRESS")
        
        if len(tokens) > 0:
            final_data.append({
                "tokens": tokens,
                "ner_tags": tags
            })
            
    return final_data

# ==========================================
# 4. 執行與儲存
# ==========================================
news_json_data = process_news(raw_content)

output_file = "news_data.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(news_json_data, f, ensure_ascii=False, indent=2)

print(f"✅ 處理完成！共生成 {len(news_json_data)} 條新聞數據。")
print(f"   - 已標註 ORG: {target_orgs}")
print(f"   - 已標註 ADDRESS: {target_addrs}") # 顯示已標註的地名
print(f"📁 檔案已儲存為: {output_file}")