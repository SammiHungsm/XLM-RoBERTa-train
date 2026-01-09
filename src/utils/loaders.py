import os
import json
import random
import re
from pathlib import Path

# 終極禁止名單：防止這些詞出現在標籤為 O 的數據中
STRICT_FORBIDDEN = ["中國", "國鐵", "港鐵", "MTR", "鐵路", "十四五", "十五五", "政府", "集團"]

def load_names(corpus_folder):
    names = []
    folder_path = Path(corpus_folder)
    default_names = ["陳大文", "李嘉誠", "張偉", "Alice", "Bob"]
    blacklist = {"先生", "小姐", "女士", "本人", "未知", "用戶"}

    if not folder_path.exists():
        return default_names
        
    for file_path in folder_path.glob("*.txt"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    name = line.strip()
                    # 零錯誤過濾：長度 2-4 中文，且不含禁止詞
                    if re.match(r'^[\u4e00-\u9fa5]{2,4}$', name):
                        if name not in blacklist and not any(f in name for f in STRICT_FORBIDDEN):
                            names.append(name)
        except: pass
    
    return list(set(names)) if names else default_names

def load_addresses(geojson_folder):
    # ... 你的 parse_one_feature 邏輯保留，那是正確的 ...
    # 這裡只修正最後的過濾邏輯
    
    # (假設已透過 parse_one_feature 拿到 raw_addresses)
    raw_addresses = [] # 這裡是你原本 load_addresses 的解析結果
    
    cleaned_addresses = []
    for addr in raw_addresses:
        # 零錯誤過濾：如果地址太短或是純粹的禁止詞，直接棄用
        if len(addr) < 5: continue
        if any(f == addr for f in STRICT_FORBIDDEN): continue 
        cleaned_addresses.append(addr)
    
    return cleaned_addresses

def load_negative_samples(folder_path, max_samples=5000):
    samples = []
    path = Path(folder_path)
    if not path.exists(): return []
    
    print(f"🛡️ 正在讀取並「清洗」負樣本...")
    for file_path in path.glob("*.txt"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
                sentences = re.split(r'[。！？\n]', text)
                for sent in sentences:
                    sent = sent.strip()
                    # 零錯誤關鍵：負樣本絕對不能包含禁止詞
                    if 10 < len(sent) < 150:
                        if not any(word in sent for word in STRICT_FORBIDDEN):
                            samples.append(sent)
        except: pass
        
    if len(samples) > max_samples:
        samples = random.sample(samples, max_samples)
    return samples