"""Async/await support for Finite Memory LLM.

Provides async versions of core functionality for:
- Async streaming generation
- Async chat interface
- Async backend support
- Non-blocking policy execution

Compatible with asyncio, FastAPI, and other async frameworks.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

import torch

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

from .core import (
    CompleteFiniteMemoryLLM,
    HuggingFaceBackend,
    LLMBackend,
    MemoryStats,
)

# ====================== ASYNC BACKEND INTERFACE ======================


class AsyncLLMBackend(ABC):
    """Abstract interface for async LLM backends."""

    @abstractmethod
    async def generate_async(
        self, input_ids: torch.Tensor, max_new_tokens: int, **kwargs: Any
    ) -> dict[str, Any]:
        """Async generation method."""
        ...

    @abstractmethod
    async def generate_stream_async(
        self, input_ids: torch.Tensor, max_new_tokens: int, **kwargs: Any
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Async streaming generation."""
        ...

    @abstractmethod
    def encode(self, text: str) -> list[int]:
        """Encode text to token IDs (sync)."""
        ...

    @abstractmethod
    def decode(self, tokens: list[int]) -> str:
        """Decode token IDs to text (sync)."""
        ...

    @abstractmethod
    def get_model_name(self) -> str:
        """Return the model name."""
        ...


# ====================== ASYNC HUGGINGFACE BACKEND ======================


class AsyncHuggingFaceBackend(AsyncLLMBackend):
    """Async wrapper for HuggingFace backend.

    Runs blocking operations in thread pool to avoid blocking event loop.
    """

    def __init__(
        self,
        model_name: str = "gpt2",
        device: str = "cpu",
        enable_kv_cache: bool = True,
    ):
        self._sync_backend = HuggingFaceBackend(
            model_name=model_name, device=device, enable_kv_cache=enable_kv_cache
        )

    async def generate_async(
        self, input_ids: torch.Tensor, max_new_tokens: int, **kwargs: Any
    ) -> dict[str, Any]:
        """Async generation using thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: self._sync_backend.generate(input_ids, max_new_tokens, **kwargs)
        )

    async def generate_stream_async(
        self, input_ids: torch.Tensor, max_new_tokens: int, **kwargs: Any
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Async streaming generation."""
        # Run sync generator in thread pool and yield results
        loop = asyncio.get_event_loop()

        def _sync_gen():
            return list(self._sync_backend.generate_stream(input_ids, max_new_tokens, **kwargs))

        tokens = await loop.run_in_executor(None, _sync_gen)
        for token_data in tokens:
            yield token_data
            # Small delay to allow event loop to process other tasks
            await asyncio.sleep(0)

    def encode(self, text: str) -> list[int]:
        """Encode text to token IDs."""
        return self._sync_backend.encode(text)

    def decode(self, tokens: list[int]) -> str:
        """Decode token IDs to text."""
        return self._sync_backend.decode(tokens)

    def get_model_name(self) -> str:
        """Return the model name."""
        return self._sync_backend.get_model_name()

    def get_cache_stats(self) -> dict[str, int]:
        """Get KV-cache statistics."""
        return self._sync_backend.get_cache_stats()


# ====================== ASYNC API BACKEND ======================


class AsyncAPIChatBackend(AsyncLLMBackend):
    """Async backend for hosted APIs.

    Args:
        tokenizer: Any HF tokenizer for token counting
        send_callable_async: Async function (prompt: str, max_tokens: int) -> str
        name: Name identifier for this backend
    """

    def __init__(
        self,
        tokenizer: Any,
        send_callable_async: Any,  # async callable
        name: str = "async-api-chat",
    ) -> None:
        self._tok = tokenizer
        self._send_async = send_callable_async
        self._name = name

    async def generate_async(
        self, input_ids: torch.Tensor, max_new_tokens: int, **kwargs: Any
    ) -> dict[str, Any]:
        """Async generation via API call."""
        prompt = self.decode(input_ids[0].tolist())
        text = await self._send_async(prompt, max_new_tokens)
        out_ids = self.encode(text)
        seq = torch.tensor([input_ids[0].tolist() + out_ids], dtype=torch.long)
        return {"sequences": seq}

    async def generate_stream_async(
        self, input_ids: torch.Tensor, max_new_tokens: int, **kwargs: Any
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Async streaming generation (if API supports it)."""
        # For APIs that support streaming, implement token-by-token yield
        # For now, fallback to single generation
        result = await self.generate_async(input_ids, max_new_tokens, **kwargs)
        generated = result["sequences"][0].tolist()[len(input_ids[0]) :]

        for i, token_id in enumerate(generated):
            yield {
                "token_id": token_id,
                "token_text": self.decode([token_id]),
                "is_final": (i == len(generated) - 1),
            }
            await asyncio.sleep(0)

    def encode(self, text: str) -> list[int]:
        """Encode text to token IDs."""
        return self._tok.encode(text, add_special_tokens=False)

    def decode(self, tokens: list[int]) -> str:
        """Decode token IDs to text."""
        return self._tok.decode(tokens, skip_special_tokens=True)

    def get_model_name(self) -> str:
        """Return the backend name."""
        return self._name


# ====================== ASYNC COMPLETE FINITE MEMORY LLM ======================


class AsyncCompleteFiniteMemoryLLM:
    """Async version of CompleteFiniteMemoryLLM.

    Provides async/await interface for non-blocking operations.
    Wraps sync implementation and runs blocking operations in thread pool.
    """

    def __init__(
        self,
        backend: LLMBackend | AsyncLLMBackend,
        max_tokens: int = 512,
        memory_policy: str = "sliding",
        window_size: int = 128,
        semantic_clusters: int = 4,
        summary_interval: int = 256,
        embedding_model: str | None = None,
        device: str = "cpu",
        max_policy_ms: float | None = None,
        telemetry_hook: Any = None,
    ) -> None:
        # Wrap sync backend if needed
        if isinstance(backend, AsyncLLMBackend):
            # For async backends, we need to adapt them
            self._async_backend = backend
            # Create a sync wrapper for the underlying CompleteFiniteMemoryLLM
            self._sync_llm = None  # We'll handle this differently
        else:
            # Sync backend - wrap in async
            self._async_backend = None
            self._sync_llm = CompleteFiniteMemoryLLM(
                backend=backend,
                max_tokens=max_tokens,
                memory_policy=memory_policy,
                window_size=window_size,
                semantic_clusters=semantic_clusters,
                summary_interval=summary_interval,
                embedding_model=embedding_model,
                device=device,
                max_policy_ms=max_policy_ms,
                telemetry_hook=telemetry_hook,
            )

    async def chat_async(self, message: str, max_new_tokens: int = 50) -> dict[str, Any]:
        """Async chat interface."""
        if self._sync_llm:
            # Run sync chat in thread pool
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, lambda: self._sync_llm.chat(message, max_new_tokens)
            )
        else:
            # TODO: Implement native async path
            raise NotImplementedError("Native async backend not yet fully implemented")

    async def chat_stream_async(
        self, message: str, max_new_tokens: int = 50
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Async streaming chat interface.

        Yields:
            dict with 'token_id', 'token_text', 'is_final', and optionally 'stats'
        """
        if not self._sync_llm:
            raise NotImplementedError("Streaming requires sync backend wrapper")

        # Encode message
        msg_tokens = self._sync_llm.backend.encode(message)
        if not msg_tokens:
            msg_tokens = [0]

        # Apply policy (sync operation in thread pool)
        loop = asyncio.get_event_loop()
        policy_out = await loop.run_in_executor(
            None, lambda: self._sync_llm._apply_policy(msg_tokens)
        )

        # Build context
        context_tokens, _ = await loop.run_in_executor(
            None,
            lambda: self._sync_llm.context_builder.build(
                self._sync_llm.backend,
                list(self._sync_llm.token_buffer),
                policy_out,
            ),
        )

        input_tensor = torch.tensor([context_tokens], device=self._sync_llm.device)

        # Stream generation
        if hasattr(self._sync_llm.backend, "generate_stream"):
            for token_data in self._sync_llm.backend.generate_stream(input_tensor, max_new_tokens):
                yield token_data
                await asyncio.sleep(0)  # Yield control to event loop
        else:
            # Fallback to non-streaming
            result = await self.chat_async(message, max_new_tokens)
            yield {
                "token_id": 0,
                "token_text": result["response"],
                "is_final": True,
                "stats": result["stats"],
            }

    async def save_checkpoint_async(self, path: str) -> str:
        """Async checkpoint save."""
        if self._sync_llm:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: self._sync_llm.save_checkpoint(path))
            return str(result)
        raise NotImplementedError("Async backend checkpoint not implemented")

    async def load_checkpoint_async(self, path: str) -> dict[str, Any]:
        """Async checkpoint load."""
        if self._sync_llm:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: self._sync_llm.load_checkpoint(path))
        raise NotImplementedError("Async backend checkpoint not implemented")

    def reset(self) -> None:
        """Reset memory state (sync operation)."""
        if self._sync_llm:
            self._sync_llm.reset()

    def get_context_window(self) -> str:
        """Get current context window (sync operation)."""
        if self._sync_llm:
            return self._sync_llm.get_context_window()
        return ""

    @property
    def stats(self) -> MemoryStats:
        """Get current statistics."""
        if self._sync_llm:
            return self._sync_llm.stats
        return MemoryStats()


# ====================== EXAMPLE USAGE ======================


async def example_async_chat():
    """Example of async chat usage."""
    # Initialize async backend
    backend = AsyncHuggingFaceBackend("gpt2", device="cpu")

    # Create async LLM
    llm = AsyncCompleteFiniteMemoryLLM(
        backend._sync_backend,  # Use sync backend for now
        memory_policy="sliding",
        max_tokens=512,
        window_size=128,
    )

    # Async chat
    result = await llm.chat_async("Hello, how are you?")
    print(f"Response: {result['response']}")

    # Async streaming
    print("\nStreaming response:")
    async for token_data in llm.chat_stream_async("Tell me a story", max_new_tokens=50):
        print(token_data["token_text"], end="", flush=True)
        if token_data["is_final"]:
            print()  # New line at end


if __name__ == "__main__":
    # Run example
    asyncio.run(example_async_chat())
