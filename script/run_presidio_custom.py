import logging
from typing import List

# Presidio Imports
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern, RecognizerResult
from presidio_analyzer.nlp_engine import TransformersNlpEngine, NlpEngineProvider, NerModelConfiguration

# Setup logging
logging.getLogger("presidio-analyzer").setLevel(logging.WARNING)

# ==========================================
# 1. 智能編號 Logic (Stateful Anonymizer)
# ==========================================
class StatefulAnonymizer:
    def __init__(self):
        self.mapping_store = {}
        self.counters = {}

    def _get_replacement(self, entity_type: str, entity_value: str) -> str:
        if entity_value in self.mapping_store:
            return self.mapping_store[entity_value]

        if entity_type not in self.counters:
            self.counters[entity_type] = 0
        self.counters[entity_type] += 1
        
        # 建立 Tag, e.g. [PERSON_1]
        new_tag = f"[{entity_type}_{self.counters[entity_type]}]"
        self.mapping_store[entity_value] = new_tag
        return new_tag

    def anonymize(self, text: str, analysis_results: List[RecognizerResult]) -> str:
        # 根據 Start 位置倒序排列，避免替換時 index 錯位
        analysis_results.sort(key=lambda x: x.start, reverse=True)
        
        last_start = len(text) + 1
        
        for result in analysis_results:
            if result.end > last_start: continue # 防止重疊
            
            entity_value = text[result.start : result.end]
            replacement = self._get_replacement(result.entity_type, entity_value)
            
            text = text[:result.start] + replacement + text[result.end:]
            last_start = result.start
            
        return text

def main():
    # ==========================================
    # 2. 設定 AI 模型 (Your Custom Model)
    # ==========================================
    model_path = "./my_merged_presidio_model" # 指向你 Merge 好的模型路徑

    # 定義標籤對應
    ner_mapping = {
        "NAME": "PERSON",
        "ADDRESS": "ADDRESS",
        "PHONE": "PHONE_NUMBER", # 模型捉到的電話
        "ID": "HKID",
        "ACCOUNT": "ACCOUNT"
    }

    model_config = [{"lang_code": "en", "model_name": {"spacy": "en_core_web_sm", "transformers": model_path}}]
    
    provider = NlpEngineProvider(nlp_configuration={
        "nlp_engine_name": "transformers",
        "models": model_config
    })

    # ⚠️ 修正：移除了不支援的 'low_confidence_score_threshold'
    ner_config = NerModelConfiguration(
        labels_to_ignore=["O"],
        aggregation_strategy="simple",
        model_to_presidio_entity_mapping=ner_mapping
    )

    transformers_engine = TransformersNlpEngine(
        models=model_config,
        ner_model_configuration=ner_config
    )

    # 初始化 Analyzer
    analyzer = AnalyzerEngine(nlp_engine=transformers_engine)

    # ==========================================
    # 3. 補強規則 (Add Regex for HK Phone)
    # ==========================================
    # 這是為了補足 AI 可能漏捉的「純數字」電話
    hk_phone_pattern = Pattern(name="hk_phone_pattern", regex=r"\b([5689]\d{3}[ -]?\d{4})\b", score=0.8)
    hk_phone_recognizer = PatternRecognizer(supported_entity="HK_PHONE", patterns=[hk_phone_pattern])
    
    # 將 Regex 加入到 Analyzer 的 Registry 中
    analyzer.registry.add_recognizer(hk_phone_recognizer)

    # ==========================================
    # 4. 測試執行
    # ==========================================
    user_input = (
        "你好，我係 Sammi。我住係 Tuen Mun 屯門市廣場 10 樓。"
        "我的電話係 9123 4567。身分證 A123456(7)。"
        "Sammi 之前打過黎。"
    )

    print(f"原始輸入:\n{user_input}\n")

    # 分析 (同時使用 AI 模型 + Regex)
    try:
        # ⚠️ 修正：將 score_threshold 放在這裡
        results = analyzer.analyze(text=user_input, language="en", score_threshold=0.4)
    except Exception as e:
        print(f"❌ 執行分析時發生錯誤: {e}")
        return

    print("[偵測結果]")
    for res in results:
        val = user_input[res.start:res.end]
        print(f"- {res.entity_type}: {val} (Score: {res.score:.2f})")

    # 去識別化
    masker = StatefulAnonymizer()
    masked_text = masker.anonymize(text=user_input, analysis_results=results)

    print(f"\n[處理結果]\n{masked_text}")
    print(f"\n[還原對照表]\n{masker.mapping_store}")

if __name__ == "__main__":
    main()