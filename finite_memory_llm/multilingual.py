"""Multi-language support for Finite Memory LLM.

Provides:
- Language detection
- Multi-lingual tokenization
- Language-specific memory policies
- Translation support (optional)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    from langdetect import detect, detect_langs
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False
    detect = None
    detect_langs = None


@dataclass
class LanguageInfo:
    """Information about detected language."""
    code: str  # ISO 639-1 code (e.g., 'en', 'es', 'fr')
    name: str  # Full name (e.g., 'English', 'Spanish')
    confidence: float  # Detection confidence (0.0-1.0)
    script: str  # Writing system (e.g., 'Latin', 'Cyrillic', 'Han')


# Language metadata
LANGUAGE_METADATA = {
    "en": {"name": "English", "script": "Latin", "rtl": False},
    "es": {"name": "Spanish", "script": "Latin", "rtl": False},
    "fr": {"name": "French", "script": "Latin", "rtl": False},
    "de": {"name": "German", "script": "Latin", "rtl": False},
    "it": {"name": "Italian", "script": "Latin", "rtl": False},
    "pt": {"name": "Portuguese", "script": "Latin", "rtl": False},
    "ru": {"name": "Russian", "script": "Cyrillic", "rtl": False},
    "zh-cn": {"name": "Chinese (Simplified)", "script": "Han", "rtl": False},
    "zh-tw": {"name": "Chinese (Traditional)", "script": "Han", "rtl": False},
    "ja": {"name": "Japanese", "script": "Mixed", "rtl": False},
    "ko": {"name": "Korean", "script": "Hangul", "rtl": False},
    "ar": {"name": "Arabic", "script": "Arabic", "rtl": True},
    "he": {"name": "Hebrew", "script": "Hebrew", "rtl": True},
    "hi": {"name": "Hindi", "script": "Devanagari", "rtl": False},
    "bn": {"name": "Bengali", "script": "Bengali", "rtl": False},
    "th": {"name": "Thai", "script": "Thai", "rtl": False},
    "vi": {"name": "Vietnamese", "script": "Latin", "rtl": False},
    "tr": {"name": "Turkish", "script": "Latin", "rtl": False},
    "pl": {"name": "Polish", "script": "Latin", "rtl": False},
    "nl": {"name": "Dutch", "script": "Latin", "rtl": False},
}


class LanguageDetector:
    """Detect language of text with confidence scores.
    
    Uses langdetect library for detection. Falls back to English if unavailable.
    """
    
    def __init__(self, default_language: str = "en"):
        self.default_language = default_language
        self.available = LANGDETECT_AVAILABLE
        
        if not self.available:
            print("⚠ langdetect not installed. Install with: pip install langdetect")
            print(f"  Defaulting to: {default_language}")
    
    def detect_language(self, text: str) -> LanguageInfo:
        """Detect language of text.
        
        Args:
            text: Input text to analyze
            
        Returns:
            LanguageInfo with detected language and confidence
        """
        if not text or not text.strip():
            return self._get_language_info(self.default_language, 1.0)
        
        if not self.available:
            return self._get_language_info(self.default_language, 0.5)
        
        try:
            # Detect language
            lang_code = detect(text)
            
            # Get confidence from detailed detection
            langs = detect_langs(text)
            confidence = 0.0
            for lang in langs:
                if lang.lang == lang_code:
                    confidence = lang.prob
                    break
            
            return self._get_language_info(lang_code, confidence)
            
        except Exception as e:
            print(f"⚠ Language detection failed: {e}")
            return self._get_language_info(self.default_language, 0.5)
    
    def _get_language_info(self, code: str, confidence: float) -> LanguageInfo:
        """Get language info from code."""
        metadata = LANGUAGE_METADATA.get(code, {
            "name": code.upper(),
            "script": "Unknown",
            "rtl": False
        })
        
        return LanguageInfo(
            code=code,
            name=metadata["name"],
            confidence=confidence,
            script=metadata["script"]
        )
    
    def is_rtl(self, text: str) -> bool:
        """Check if text is right-to-left language."""
        lang_info = self.detect_language(text)
        metadata = LANGUAGE_METADATA.get(lang_info.code, {})
        return metadata.get("rtl", False)


class MultilingualTokenizer:
    """Tokenizer wrapper with language-aware features.
    
    Provides:
    - Language detection before tokenization
    - Language-specific token counting
    - Multi-script support
    """
    
    def __init__(self, base_tokenizer: Any, detect_language: bool = True):
        self.base_tokenizer = base_tokenizer
        self.detector = LanguageDetector() if detect_language else None
        self.language_stats = {}  # Track language distribution
    
    def encode(self, text: str, detect_lang: bool = True) -> tuple[list[int], LanguageInfo | None]:
        """Encode text with optional language detection.
        
        Args:
            text: Text to encode
            detect_lang: Whether to detect language
            
        Returns:
            Tuple of (token_ids, language_info)
        """
        lang_info = None
        
        if detect_lang and self.detector:
            lang_info = self.detector.detect_language(text)
            
            # Update stats
            if lang_info.code not in self.language_stats:
                self.language_stats[lang_info.code] = 0
            self.language_stats[lang_info.code] += 1
        
        # Encode with base tokenizer
        tokens = self.base_tokenizer.encode(text, add_special_tokens=False)
        
        return tokens, lang_info
    
    def decode(self, tokens: list[int]) -> str:
        """Decode tokens to text."""
        return self.base_tokenizer.decode(tokens, skip_special_tokens=True)
    
    def get_language_distribution(self) -> dict[str, int]:
        """Get distribution of languages seen."""
        return self.language_stats.copy()
    
    def get_dominant_language(self) -> str | None:
        """Get most common language seen."""
        if not self.language_stats:
            return None
        return max(self.language_stats, key=self.language_stats.get)


class MultilingualMemoryPolicy:
    """Language-aware memory policy adjustments.
    
    Different languages have different characteristics:
    - CJK languages: More information per token
    - Agglutinative languages: Longer words, more morphology
    - Isolating languages: More tokens per concept
    """
    
    # Token multipliers for different scripts
    SCRIPT_MULTIPLIERS = {
        "Han": 1.5,  # Chinese characters pack more info
        "Hangul": 1.3,  # Korean
        "Mixed": 1.4,  # Japanese (mixed scripts)
        "Arabic": 1.2,  # Arabic script
        "Devanagari": 1.2,  # Hindi, Sanskrit
        "Latin": 1.0,  # Baseline
        "Cyrillic": 1.0,  # Russian, etc.
    }
    
    def __init__(self, base_max_tokens: int = 512):
        self.base_max_tokens = base_max_tokens
        self.detector = LanguageDetector()
    
    def adjust_max_tokens(self, text: str) -> int:
        """Adjust max tokens based on language characteristics.
        
        Args:
            text: Sample text to detect language
            
        Returns:
            Adjusted max_tokens value
        """
        lang_info = self.detector.detect_language(text)
        multiplier = self.SCRIPT_MULTIPLIERS.get(lang_info.script, 1.0)
        
        # Adjust token limit based on script
        adjusted = int(self.base_max_tokens * multiplier)
        
        return adjusted
    
    def get_recommended_policy(self, text: str) -> str:
        """Recommend memory policy based on language.
        
        Args:
            text: Sample text to analyze
            
        Returns:
            Recommended policy name
        """
        lang_info = self.detector.detect_language(text)
        
        # CJK languages: semantic clustering works well
        if lang_info.script in ("Han", "Hangul", "Mixed"):
            return "semantic"
        
        # RTL languages: importance-based works well
        metadata = LANGUAGE_METADATA.get(lang_info.code, {})
        if metadata.get("rtl", False):
            return "importance"
        
        # Default: sliding window for simplicity
        return "sliding"


# ====================== TRANSLATION SUPPORT (OPTIONAL) ======================


class TranslationBridge:
    """Optional translation support for cross-lingual conversations.
    
    Requires: googletrans or similar translation library
    """
    
    def __init__(self, target_language: str = "en"):
        self.target_language = target_language
        self.translator = None
        
        try:
            from googletrans import Translator
            self.translator = Translator()
            self.available = True
        except ImportError:
            self.available = False
            print("⚠ googletrans not installed. Translation unavailable.")
            print("  Install with: pip install googletrans==4.0.0-rc1")
    
    def translate(self, text: str, target_lang: str | None = None) -> str:
        """Translate text to target language.
        
        Args:
            text: Text to translate
            target_lang: Target language code (default: self.target_language)
            
        Returns:
            Translated text
        """
        if not self.available:
            return text
        
        target = target_lang or self.target_language
        
        try:
            result = self.translator.translate(text, dest=target)
            return result.text
        except Exception as e:
            print(f"⚠ Translation failed: {e}")
            return text
    
    def detect_and_translate(self, text: str) -> tuple[str, str]:
        """Detect language and translate if needed.
        
        Returns:
            Tuple of (translated_text, source_language)
        """
        if not self.available:
            return text, "unknown"
        
        try:
            result = self.translator.translate(text, dest=self.target_language)
            return result.text, result.src
        except Exception as e:
            print(f"⚠ Translation failed: {e}")
            return text, "unknown"


# ====================== EXAMPLE USAGE ======================


def example_multilingual():
    """Example of multilingual support."""
    detector = LanguageDetector()
    
    # Test different languages
    texts = {
        "Hello, how are you?": "en",
        "Hola, ¿cómo estás?": "es",
        "Bonjour, comment allez-vous?": "fr",
        "你好，你好吗？": "zh-cn",
        "こんにちは、お元気ですか？": "ja",
        "مرحبا، كيف حالك؟": "ar",
    }
    
    print("Language Detection Examples:")
    print("=" * 60)
    
    for text, expected in texts.items():
        lang_info = detector.detect_language(text)
        print(f"\nText: {text}")
        print(f"Detected: {lang_info.name} ({lang_info.code})")
        print(f"Confidence: {lang_info.confidence:.2f}")
        print(f"Script: {lang_info.script}")
        print(f"Expected: {expected} - {'✓' if lang_info.code == expected else '✗'}")
    
    # Memory policy recommendations
    print("\n" + "=" * 60)
    print("Memory Policy Recommendations:")
    print("=" * 60)
    
    policy_advisor = MultilingualMemoryPolicy()
    
    for text in texts.keys():
        policy = policy_advisor.get_recommended_policy(text)
        adjusted_tokens = policy_advisor.adjust_max_tokens(text)
        print(f"\n{text[:30]}...")
        print(f"  Recommended policy: {policy}")
        print(f"  Adjusted max_tokens: {adjusted_tokens}")


if __name__ == "__main__":
    example_multilingual()
