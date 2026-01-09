import re
# 確保引用路徑正確
from src.utils.tokenizer import smart_tokenize 
from .config import LABEL2ID

class AutoLabeler:
    def __init__(self):
        self.label2id = LABEL2ID

    # ✅ 修正：將函數名稱由 process_text 改為 process
    def process(self, text, target_entities_dict):
        """
        text: 原始文本
        target_entities_dict: 字典，例如 {"B-NAME": ["李嘉誠", "Sammi"], "B-ORG": ["港鐵"]}
        """
        # 1. 分句
        sentences = re.split(r'([。！？\n])', text)
        segments = []
        current = ""
        for s in sentences:
            current += s
            if re.match(r'[。！？\n]', s):
                if current.strip(): segments.append(current.strip())
                current = ""
        if current.strip(): segments.append(current.strip())

        final_data = []
        
        for sent in segments:
            tokens = smart_tokenize(sent)
            tags = [0] * len(tokens) # 0 is "O"
            
            # 建立 Token Spans
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

            # 統一標註邏輯
            for label_key, name_list in target_entities_dict.items():
                # label_key example: "B-NAME"
                # 推導 I-Label: "I-NAME"
                i_label_key = label_key.replace("B-", "I-")
                
                # 獲取對應的 ID
                b_id = self.label2id.get(label_key, 0)
                i_id = self.label2id.get(i_label_key, 0)

                for name in name_list:
                    for match in re.finditer(re.escape(name), sent):
                        m_start, m_end = match.span()
                        for idx, span in enumerate(token_spans):
                            if span is None: continue
                            t_start, t_end = span
                            if t_start >= m_start and t_end <= m_end:
                                if tags[idx] == 0: # 防止覆蓋
                                    if t_start == m_start:
                                        tags[idx] = b_id
                                    else:
                                        tags[idx] = i_id

            if len(tokens) > 0:
                final_data.append({"tokens": tokens, "ner_tags": tags})
        
        return final_data