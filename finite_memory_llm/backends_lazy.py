"""Lazy-loading backends - imports torch/transformers only when instantiated.

This module provides the same backends as core.py but with conditional imports.
Import time: <0.01s (no torch until backend is created)
"""

from __future__ import annotations

from typing import Any

from .interfaces import LLMBackend


class HuggingFaceBackendLazy(LLMBackend):
    """HuggingFace backend with lazy imports - torch loads on instantiation."""

    def __init__(
        self,
        model_name: str = "gpt2",
        device: str = "cpu",
        enable_kv_cache: bool = True,
    ):
        """Initialize backend with lazy torch import.
        
        Args:
            model_name: HuggingFace model name
            device: Device to run on ('cpu' or 'cuda')
            enable_kv_cache: Whether to enable KV-cache optimization
        """
        # Import torch ONLY when backend is instantiated
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.device = device
        self.model_name = model_name
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(model_name).to(device)
        self.model.eval()

        self.enable_kv_cache = enable_kv_cache
        self.past_key_values = None
        self.last_input_ids = None

        # KV-cache stats
        self.cache_hits = 0
        self.cache_misses = 0
        self.cached_tokens = 0
        self.total_tokens_processed = 0

        # Store torch module for later use
        self._torch = torch

    def generate(
        self, input_ids: Any, max_new_tokens: int, **kwargs: Any
    ) -> dict[str, Any]:
        """Generate text from input IDs."""
        torch = self._torch

        if self.enable_kv_cache and self.past_key_values is not None:
            # Check for KV-cache hit
            common_prefix_len = 0
            if (
                self.last_input_ids is not None
                and input_ids.shape[1] > self.last_input_ids.shape[1]
            ):
                if torch.equal(
                    input_ids[0, : self.last_input_ids.shape[1]],
                    self.last_input_ids[0],
                ):
                    common_prefix_len = self.last_input_ids.shape[1]
                    self.cache_hits += 1
                    self.cached_tokens += common_prefix_len
                else:
                    self.cache_misses += 1
            else:
                self.cache_misses += 1

            if common_prefix_len > 0:
                new_input_ids = input_ids[:, common_prefix_len:]
                with torch.no_grad():
                    outputs = self.model.generate(
                        new_input_ids,
                        max_new_tokens=max_new_tokens,
                        pad_token_id=self.tokenizer.eos_token_id,
                        past_key_values=self.past_key_values,
                        use_cache=True,
                        return_dict_in_generate=True,
                        **kwargs,
                    )
                self.past_key_values = outputs.past_key_values
                generated_ids = outputs.sequences
            else:
                with torch.no_grad():
                    outputs = self.model.generate(
                        input_ids,
                        max_new_tokens=max_new_tokens,
                        pad_token_id=self.tokenizer.eos_token_id,
                        use_cache=True,
                        return_dict_in_generate=True,
                        **kwargs,
                    )
                self.past_key_values = outputs.past_key_values
                generated_ids = outputs.sequences
        else:
            with torch.no_grad():
                generated_ids = self.model.generate(
                    input_ids,
                    max_new_tokens=max_new_tokens,
                    pad_token_id=self.tokenizer.eos_token_id,
                    use_cache=self.enable_kv_cache,
                    **kwargs,
                )

        self.last_input_ids = generated_ids
        self.total_tokens_processed += generated_ids.shape[1]

        return {"sequences": generated_ids}

    def encode(self, text: str) -> list[int]:
        """Encode text to token IDs."""
        return self.tokenizer.encode(text, add_special_tokens=False)

    def decode(self, tokens: list[int]) -> str:
        """Decode token IDs to text."""
        return self.tokenizer.decode(tokens, skip_special_tokens=True)

    def get_model_name(self) -> str:
        """Return the model name."""
        return self.model_name

    def get_cache_stats(self) -> dict[str, int]:
        """Get KV-cache statistics."""
        return {
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cached_tokens": self.cached_tokens,
            "total_tokens_processed": self.total_tokens_processed,
        }


class APIChatBackendLazy(LLMBackend):
    """API backend with lazy tokenizer import."""

    def __init__(
        self,
        tokenizer: Any,
        send_callable: Any,
        name: str = "api-backend",
    ):
        """Initialize API backend.
        
        Args:
            tokenizer: Tokenizer instance (can be lazy)
            send_callable: Function to call API
            name: Backend name
        """
        self.tokenizer = tokenizer
        self.send_callable = send_callable
        self.name = name

    def generate(
        self, input_ids: Any, max_new_tokens: int, **kwargs: Any
    ) -> dict[str, Any]:
        """Generate via API call."""
        # Decode input
        prompt = self.decode(input_ids[0].tolist() if hasattr(input_ids, 'tolist') else input_ids)
        
        # Call API
        response_text = self.send_callable(prompt, max_new_tokens)
        
        # Encode response
        response_ids = self.encode(response_text)
        
        # Return in expected format
        import torch
        full_ids = list(input_ids[0]) + response_ids
        return {"sequences": torch.tensor([full_ids])}

    def encode(self, text: str) -> list[int]:
        """Encode text to token IDs."""
        return self.tokenizer.encode(text, add_special_tokens=False)

    def decode(self, tokens: list[int]) -> str:
        """Decode token IDs to text."""
        return self.tokenizer.decode(tokens, skip_special_tokens=True)

    def get_model_name(self) -> str:
        """Return the backend name."""
        return self.name


__all__ = ["HuggingFaceBackendLazy", "APIChatBackendLazy"]
