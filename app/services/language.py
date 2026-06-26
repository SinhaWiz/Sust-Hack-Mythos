import re

def detect_language(text: str) -> str:
    """Detect if text is primarily Bangla, English, or mixed.
    
    Uses Unicode range for Bangla: \u0980-\u09FF.
    """
    if not text:
        return "en"
        
    bangla_chars = len(re.findall(r'[\u0980-\u09FF]', text))
    latin_chars = len(re.findall(r'[a-zA-Z]', text))
    total = bangla_chars + latin_chars
    
    if total == 0:
        return "en"  # default to English if no alpha/Bangla chars are found (e.g. only punctuation, numbers)
    
    bangla_ratio = bangla_chars / total
    if bangla_ratio > 0.6:
        return "bn"
    elif bangla_ratio > 0.2:
        return "mixed"
    else:
        return "en"
