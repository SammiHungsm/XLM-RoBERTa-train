# data_utils/tokenizer.py
import re

def smart_tokenize(text):
    result = []
    current_eng = ""
    
    for char in text:
        # ✅ 關鍵：將中文點號 (．和·) 視為文字的一部分，或者是英文/數字
        if re.match(r'[a-zA-Z0-9\+\-\.\@]', char): 
            current_eng += char
        else:
            if current_eng:
                result.append(current_eng)
                current_eng = ""
            
            # ✅ 這裡很重要：如果是名字中間的點，要單獨作為一個 Token 保留
            # 或者是直接和前後文連在一起（視乎你的策略），最穩陣係單獨切分
            if char.strip():
                result.append(char)
                
    if current_eng:
        result.append(current_eng)
    return result