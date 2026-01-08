import re

def smart_tokenize(text):
    """
    智能切分 (Smart Tokenization) - Word-level for English/Digits, Char-level for others.
    
    功能：
    1. 中文/標點：按字切分
    2. 英文/數字：按單詞切分 (避免 "Block" 變成 ['B', 'l', 'o', 'c', 'k'])
    3. 自動過濾純空格：節省 Token 空間，提升模型效率
    
    Args:
        text (str): 輸入文本
        
    Returns:
        list: Token 列表
    """
    if not text:
        return []
        
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
            if char.strip(): 
                result.append(char)
            
    # 循環結束後，檢查是否有遺留的英文詞
    if current_eng:
        result.append(current_eng)
        
    return result