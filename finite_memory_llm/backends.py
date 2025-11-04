"""Additional LLM backends for Finite Memory AI.

Provides ready-to-use backends for:
- Cohere
- AI21 Labs
- Anthropic Claude
- Google PaLM/Gemini
- Hugging Face Inference API
- Together AI
- Replicate

Each backend implements the LLMBackend interface for seamless integration.
"""

from __future__ import annotations

from typing import Any, Callable

import torch

from .core import LLMBackend


# ====================== COHERE BACKEND ======================


class CohereBackend(LLMBackend):
    """Backend for Cohere API.
    
    Requires: cohere library
    Install: pip install cohere
    
    Args:
        api_key: Cohere API key
        model: Model name (e.g., 'command', 'command-light')
        tokenizer: HuggingFace tokenizer for token counting
    """
    
    def __init__(
        self,
        api_key: str,
        model: str = "command",
        tokenizer: Any = None,
    ):
        try:
            import cohere
            self.client = cohere.Client(api_key)
            self.model = model
            self.available = True
        except ImportError:
            self.available = False
            print("⚠ cohere not installed. Install with: pip install cohere")
        
        # Use provided tokenizer or load default
        if tokenizer is None:
            from transformers import AutoTokenizer
            tokenizer = AutoTokenizer.from_pretrained("gpt2")
        self.tokenizer = tokenizer
    
    def generate(
        self,
        input_ids: torch.Tensor,
        max_new_tokens: int,
        **kwargs: Any
    ) -> dict[str, Any]:
        """Generate response via Cohere API."""
        if not self.available:
            raise RuntimeError("Cohere library not available")
        
        prompt = self.decode(input_ids[0].tolist())
        
        response = self.client.generate(
            model=self.model,
            prompt=prompt,
            max_tokens=max_new_tokens,
            temperature=kwargs.get("temperature", 0.7),
        )
        
        text = response.generations[0].text
        out_ids = self.encode(text)
        seq = torch.tensor([input_ids[0].tolist() + out_ids], dtype=torch.long)
        
        return {"sequences": seq}
    
    def encode(self, text: str) -> list[int]:
        """Encode text to token IDs."""
        return self.tokenizer.encode(text, add_special_tokens=False)
    
    def decode(self, tokens: list[int]) -> str:
        """Decode token IDs to text."""
        return self.tokenizer.decode(tokens, skip_special_tokens=True)
    
    def get_model_name(self) -> str:
        """Return the model name."""
        return f"cohere-{self.model}"


# ====================== AI21 BACKEND ======================


class AI21Backend(LLMBackend):
    """Backend for AI21 Labs API.
    
    Requires: ai21 library
    Install: pip install ai21
    
    Args:
        api_key: AI21 API key
        model: Model name (e.g., 'j2-ultra', 'j2-mid')
        tokenizer: HuggingFace tokenizer for token counting
    """
    
    def __init__(
        self,
        api_key: str,
        model: str = "j2-ultra",
        tokenizer: Any = None,
    ):
        try:
            import ai21
            ai21.api_key = api_key
            self.ai21 = ai21
            self.model = model
            self.available = True
        except ImportError:
            self.available = False
            print("⚠ ai21 not installed. Install with: pip install ai21")
        
        if tokenizer is None:
            from transformers import AutoTokenizer
            tokenizer = AutoTokenizer.from_pretrained("gpt2")
        self.tokenizer = tokenizer
    
    def generate(
        self,
        input_ids: torch.Tensor,
        max_new_tokens: int,
        **kwargs: Any
    ) -> dict[str, Any]:
        """Generate response via AI21 API."""
        if not self.available:
            raise RuntimeError("AI21 library not available")
        
        prompt = self.decode(input_ids[0].tolist())
        
        response = self.ai21.Completion.execute(
            model=self.model,
            prompt=prompt,
            maxTokens=max_new_tokens,
            temperature=kwargs.get("temperature", 0.7),
        )
        
        text = response["completions"][0]["data"]["text"]
        out_ids = self.encode(text)
        seq = torch.tensor([input_ids[0].tolist() + out_ids], dtype=torch.long)
        
        return {"sequences": seq}
    
    def encode(self, text: str) -> list[int]:
        """Encode text to token IDs."""
        return self.tokenizer.encode(text, add_special_tokens=False)
    
    def decode(self, tokens: list[int]) -> str:
        """Decode token IDs to text."""
        return self.tokenizer.decode(tokens, skip_special_tokens=True)
    
    def get_model_name(self) -> str:
        """Return the model name."""
        return f"ai21-{self.model}"


# ====================== ANTHROPIC CLAUDE BACKEND ======================


class AnthropicBackend(LLMBackend):
    """Backend for Anthropic Claude API.
    
    Requires: anthropic library
    Install: pip install anthropic
    
    Args:
        api_key: Anthropic API key
        model: Model name (e.g., 'claude-3-opus-20240229')
        tokenizer: HuggingFace tokenizer for token counting
    """
    
    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-sonnet-20240229",
        tokenizer: Any = None,
    ):
        try:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=api_key)
            self.model = model
            self.available = True
        except ImportError:
            self.available = False
            print("⚠ anthropic not installed. Install with: pip install anthropic")
        
        if tokenizer is None:
            from transformers import AutoTokenizer
            tokenizer = AutoTokenizer.from_pretrained("gpt2")
        self.tokenizer = tokenizer
    
    def generate(
        self,
        input_ids: torch.Tensor,
        max_new_tokens: int,
        **kwargs: Any
    ) -> dict[str, Any]:
        """Generate response via Anthropic API."""
        if not self.available:
            raise RuntimeError("Anthropic library not available")
        
        prompt = self.decode(input_ids[0].tolist())
        
        message = self.client.messages.create(
            model=self.model,
            max_tokens=max_new_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        
        text = message.content[0].text
        out_ids = self.encode(text)
        seq = torch.tensor([input_ids[0].tolist() + out_ids], dtype=torch.long)
        
        return {"sequences": seq}
    
    def encode(self, text: str) -> list[int]:
        """Encode text to token IDs."""
        return self.tokenizer.encode(text, add_special_tokens=False)
    
    def decode(self, tokens: list[int]) -> str:
        """Decode token IDs to text."""
        return self.tokenizer.decode(tokens, skip_special_tokens=True)
    
    def get_model_name(self) -> str:
        """Return the model name."""
        return f"anthropic-{self.model}"


# ====================== GOOGLE PALM/GEMINI BACKEND ======================


class GoogleBackend(LLMBackend):
    """Backend for Google PaLM/Gemini API.
    
    Requires: google-generativeai library
    Install: pip install google-generativeai
    
    Args:
        api_key: Google API key
        model: Model name (e.g., 'gemini-pro')
        tokenizer: HuggingFace tokenizer for token counting
    """
    
    def __init__(
        self,
        api_key: str,
        model: str = "gemini-pro",
        tokenizer: Any = None,
    ):
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            self.model_obj = genai.GenerativeModel(model)
            self.model = model
            self.available = True
        except ImportError:
            self.available = False
            print("⚠ google-generativeai not installed.")
            print("  Install with: pip install google-generativeai")
        
        if tokenizer is None:
            from transformers import AutoTokenizer
            tokenizer = AutoTokenizer.from_pretrained("gpt2")
        self.tokenizer = tokenizer
    
    def generate(
        self,
        input_ids: torch.Tensor,
        max_new_tokens: int,
        **kwargs: Any
    ) -> dict[str, Any]:
        """Generate response via Google API."""
        if not self.available:
            raise RuntimeError("Google GenerativeAI library not available")
        
        prompt = self.decode(input_ids[0].tolist())
        
        response = self.model_obj.generate_content(
            prompt,
            generation_config={"max_output_tokens": max_new_tokens},
        )
        
        text = response.text
        out_ids = self.encode(text)
        seq = torch.tensor([input_ids[0].tolist() + out_ids], dtype=torch.long)
        
        return {"sequences": seq}
    
    def encode(self, text: str) -> list[int]:
        """Encode text to token IDs."""
        return self.tokenizer.encode(text, add_special_tokens=False)
    
    def decode(self, tokens: list[int]) -> str:
        """Decode token IDs to text."""
        return self.tokenizer.decode(tokens, skip_special_tokens=True)
    
    def get_model_name(self) -> str:
        """Return the model name."""
        return f"google-{self.model}"


# ====================== HUGGING FACE INFERENCE API BACKEND ======================


class HuggingFaceInferenceBackend(LLMBackend):
    """Backend for Hugging Face Inference API.
    
    Requires: huggingface_hub library
    Install: pip install huggingface_hub
    
    Args:
        api_key: HuggingFace API token
        model: Model name on HuggingFace Hub
        tokenizer: HuggingFace tokenizer for token counting
    """
    
    def __init__(
        self,
        api_key: str,
        model: str = "mistralai/Mistral-7B-Instruct-v0.1",
        tokenizer: Any = None,
    ):
        try:
            from huggingface_hub import InferenceClient
            self.client = InferenceClient(token=api_key)
            self.model = model
            self.available = True
        except ImportError:
            self.available = False
            print("⚠ huggingface_hub not installed.")
            print("  Install with: pip install huggingface_hub")
        
        if tokenizer is None:
            from transformers import AutoTokenizer
            try:
                tokenizer = AutoTokenizer.from_pretrained(model)
            except Exception:
                tokenizer = AutoTokenizer.from_pretrained("gpt2")
        self.tokenizer = tokenizer
    
    def generate(
        self,
        input_ids: torch.Tensor,
        max_new_tokens: int,
        **kwargs: Any
    ) -> dict[str, Any]:
        """Generate response via HuggingFace Inference API."""
        if not self.available:
            raise RuntimeError("HuggingFace Hub library not available")
        
        prompt = self.decode(input_ids[0].tolist())
        
        response = self.client.text_generation(
            prompt,
            model=self.model,
            max_new_tokens=max_new_tokens,
            temperature=kwargs.get("temperature", 0.7),
        )
        
        out_ids = self.encode(response)
        seq = torch.tensor([input_ids[0].tolist() + out_ids], dtype=torch.long)
        
        return {"sequences": seq}
    
    def encode(self, text: str) -> list[int]:
        """Encode text to token IDs."""
        return self.tokenizer.encode(text, add_special_tokens=False)
    
    def decode(self, tokens: list[int]) -> str:
        """Decode token IDs to text."""
        return self.tokenizer.decode(tokens, skip_special_tokens=True)
    
    def get_model_name(self) -> str:
        """Return the model name."""
        return f"hf-{self.model}"


# ====================== TOGETHER AI BACKEND ======================


class TogetherBackend(LLMBackend):
    """Backend for Together AI API.
    
    Requires: together library
    Install: pip install together
    
    Args:
        api_key: Together API key
        model: Model name (e.g., 'mistralai/Mixtral-8x7B-Instruct-v0.1')
        tokenizer: HuggingFace tokenizer for token counting
    """
    
    def __init__(
        self,
        api_key: str,
        model: str = "mistralai/Mixtral-8x7B-Instruct-v0.1",
        tokenizer: Any = None,
    ):
        try:
            import together
            together.api_key = api_key
            self.together = together
            self.model = model
            self.available = True
        except ImportError:
            self.available = False
            print("⚠ together not installed. Install with: pip install together")
        
        if tokenizer is None:
            from transformers import AutoTokenizer
            tokenizer = AutoTokenizer.from_pretrained("gpt2")
        self.tokenizer = tokenizer
    
    def generate(
        self,
        input_ids: torch.Tensor,
        max_new_tokens: int,
        **kwargs: Any
    ) -> dict[str, Any]:
        """Generate response via Together AI API."""
        if not self.available:
            raise RuntimeError("Together library not available")
        
        prompt = self.decode(input_ids[0].tolist())
        
        response = self.together.Complete.create(
            prompt=prompt,
            model=self.model,
            max_tokens=max_new_tokens,
            temperature=kwargs.get("temperature", 0.7),
        )
        
        text = response["output"]["choices"][0]["text"]
        out_ids = self.encode(text)
        seq = torch.tensor([input_ids[0].tolist() + out_ids], dtype=torch.long)
        
        return {"sequences": seq}
    
    def encode(self, text: str) -> list[int]:
        """Encode text to token IDs."""
        return self.tokenizer.encode(text, add_special_tokens=False)
    
    def decode(self, tokens: list[int]) -> str:
        """Decode token IDs to text."""
        return self.tokenizer.decode(tokens, skip_special_tokens=True)
    
    def get_model_name(self) -> str:
        """Return the model name."""
        return f"together-{self.model}"


# ====================== REPLICATE BACKEND ======================


class ReplicateBackend(LLMBackend):
    """Backend for Replicate API.
    
    Requires: replicate library
    Install: pip install replicate
    
    Args:
        api_key: Replicate API token
        model: Model version (e.g., 'meta/llama-2-70b-chat')
        tokenizer: HuggingFace tokenizer for token counting
    """
    
    def __init__(
        self,
        api_key: str,
        model: str = "meta/llama-2-70b-chat",
        tokenizer: Any = None,
    ):
        try:
            import replicate
            import os
            os.environ["REPLICATE_API_TOKEN"] = api_key
            self.replicate = replicate
            self.model = model
            self.available = True
        except ImportError:
            self.available = False
            print("⚠ replicate not installed. Install with: pip install replicate")
        
        if tokenizer is None:
            from transformers import AutoTokenizer
            tokenizer = AutoTokenizer.from_pretrained("gpt2")
        self.tokenizer = tokenizer
    
    def generate(
        self,
        input_ids: torch.Tensor,
        max_new_tokens: int,
        **kwargs: Any
    ) -> dict[str, Any]:
        """Generate response via Replicate API."""
        if not self.available:
            raise RuntimeError("Replicate library not available")
        
        prompt = self.decode(input_ids[0].tolist())
        
        output = self.replicate.run(
            self.model,
            input={
                "prompt": prompt,
                "max_new_tokens": max_new_tokens,
                "temperature": kwargs.get("temperature", 0.7),
            },
        )
        
        # Replicate returns a generator
        text = "".join(output)
        out_ids = self.encode(text)
        seq = torch.tensor([input_ids[0].tolist() + out_ids], dtype=torch.long)
        
        return {"sequences": seq}
    
    def encode(self, text: str) -> list[int]:
        """Encode text to token IDs."""
        return self.tokenizer.encode(text, add_special_tokens=False)
    
    def decode(self, tokens: list[int]) -> str:
        """Decode token IDs to text."""
        return self.tokenizer.decode(tokens, skip_special_tokens=True)
    
    def get_model_name(self) -> str:
        """Return the model name."""
        return f"replicate-{self.model}"


# ====================== EXAMPLE USAGE ======================


def example_backends():
    """Example usage of different backends."""
    from transformers import AutoTokenizer
    
    tokenizer = AutoTokenizer.from_pretrained("gpt2")
    
    # Example configurations (replace with real API keys)
    backends = {
        "Cohere": lambda: CohereBackend(
            api_key="your-cohere-key",
            model="command",
            tokenizer=tokenizer
        ),
        "AI21": lambda: AI21Backend(
            api_key="your-ai21-key",
            model="j2-ultra",
            tokenizer=tokenizer
        ),
        "Anthropic": lambda: AnthropicBackend(
            api_key="your-anthropic-key",
            model="claude-3-sonnet-20240229",
            tokenizer=tokenizer
        ),
        "Google": lambda: GoogleBackend(
            api_key="your-google-key",
            model="gemini-pro",
            tokenizer=tokenizer
        ),
    }
    
    print("Available Backends:")
    print("=" * 60)
    for name, backend_fn in backends.items():
        try:
            backend = backend_fn()
            print(f"✓ {name}: {backend.get_model_name()}")
        except Exception as e:
            print(f"✗ {name}: {e}")


if __name__ == "__main__":
    example_backends()
