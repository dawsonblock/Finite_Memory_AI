#!/usr/bin/env python3
"""
Production Deployment Example for Finite Memory AI v2.4.0

This example demonstrates a production-ready setup with:
- Proper error handling
- Monitoring and telemetry
- Health checks
- Rate limiting
- Logging
- Graceful degradation
"""

import logging
import time
from collections import deque
from typing import Any

from finite_memory_llm import CompleteFiniteMemoryLLM, HuggingFaceBackend, PrometheusHook

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple rate limiter for production use."""

    def __init__(self, max_calls: int = 100, period: int = 60):
        self.max_calls = max_calls
        self.period = period
        self.calls = deque()

    def allow_request(self) -> bool:
        """Check if request is allowed under rate limit."""
        now = time.time()

        # Remove old calls outside the time window
        while self.calls and now - self.calls[0] > self.period:
            self.calls.popleft()

        if len(self.calls) < self.max_calls:
            self.calls.append(now)
            return True

        return False


class ProductionLLMService:
    """Production-ready LLM service with monitoring and error handling."""

    def __init__(
        self,
        model_name: str = "gpt2",
        device: str = "cpu",
        max_tokens: int = 2048,
        memory_policy: str = "hybrid",
    ):
        """Initialize production LLM service.

        Args:
            model_name: Model to use
            device: Device (cpu/cuda)
            max_tokens: Maximum context tokens
            memory_policy: Memory management policy
        """
        logger.info(f"Initializing LLM service with model: {model_name}")

        # Initialize backend
        try:
            self.backend = HuggingFaceBackend(
                model_name=model_name, device=device, enable_kv_cache=True
            )
            logger.info("Backend initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize backend: {e}")
            raise

        # Initialize telemetry
        try:
            self.telemetry = PrometheusHook()
            logger.info("Telemetry initialized")
        except ImportError:
            logger.warning("Prometheus not available, telemetry disabled")
            self.telemetry = None

        # Initialize LLM
        try:
            self.llm = CompleteFiniteMemoryLLM(
                backend=self.backend,
                max_tokens=max_tokens,
                memory_policy=memory_policy,
                window_size=512,
                max_policy_ms=100.0,  # 100ms latency budget
                telemetry_hook=self.telemetry,
            )
            logger.info("LLM initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")
            raise

        # Initialize rate limiter
        self.rate_limiter = RateLimiter(max_calls=100, period=60)

        # Track statistics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0

    def validate_input(self, message: str) -> str:
        """Validate and sanitize user input.

        Args:
            message: User message

        Returns:
            Sanitized message

        Raises:
            ValueError: If input is invalid
        """
        if not message:
            raise ValueError("Message cannot be empty")

        if len(message) > 10000:
            raise ValueError("Message too long (max 10000 characters)")

        # Remove control characters
        message = "".join(char for char in message if char.isprintable() or char.isspace())

        return message.strip()

    def chat(self, message: str, max_new_tokens: int = 100, user_id: str = None) -> dict[str, Any]:
        """Process chat message with production safeguards.

        Args:
            message: User message
            max_new_tokens: Maximum tokens to generate
            user_id: Optional user identifier for logging

        Returns:
            Response dictionary with result and metadata
        """
        self.total_requests += 1
        start_time = time.time()

        # Log request
        logger.info(
            f"Chat request from user={user_id}, "
            f"message_length={len(message)}, "
            f"max_tokens={max_new_tokens}"
        )

        # Check rate limit
        if not self.rate_limiter.allow_request():
            logger.warning(f"Rate limit exceeded for user={user_id}")
            self.failed_requests += 1
            return {
                "success": False,
                "error": "Rate limit exceeded. Please try again later.",
                "error_code": "RATE_LIMIT",
            }

        # Validate input
        try:
            message = self.validate_input(message)
        except ValueError as e:
            logger.warning(f"Invalid input from user={user_id}: {e}")
            self.failed_requests += 1
            return {
                "success": False,
                "error": str(e),
                "error_code": "INVALID_INPUT",
            }

        # Process with LLM
        try:
            result = self.llm.chat(message, max_new_tokens=max_new_tokens)

            # Calculate metrics
            elapsed_time = time.time() - start_time

            self.successful_requests += 1

            logger.info(
                f"Chat successful for user={user_id}, "
                f"latency={elapsed_time:.2f}s, "
                f"tokens_used={result['tokens_used']}"
            )

            return {
                "success": True,
                "response": result["response"],
                "metadata": {
                    "tokens_used": result["tokens_used"],
                    "context_length": result["context_length"],
                    "latency_ms": elapsed_time * 1000,
                    "memory_policy": result["memory_policy"],
                    "stats": {
                        "compression_ratio": result["stats"].compression_ratio,
                        "tokens_seen": result["stats"].tokens_seen,
                        "tokens_retained": result["stats"].tokens_retained,
                    },
                },
            }

        except Exception as e:
            elapsed_time = time.time() - start_time
            self.failed_requests += 1

            logger.error(f"Chat failed for user={user_id}: {e}, " f"latency={elapsed_time:.2f}s")

            return {
                "success": False,
                "error": "An error occurred processing your request.",
                "error_code": "PROCESSING_ERROR",
                "metadata": {"latency_ms": elapsed_time * 1000},
            }

    def health_check(self) -> dict[str, Any]:
        """Perform health check.

        Returns:
            Health status dictionary
        """
        try:
            # Simple test
            self.llm.chat("test", max_new_tokens=5)

            return {
                "status": "healthy",
                "model": self.backend.get_model_name(),
                "stats": {
                    "total_requests": self.total_requests,
                    "successful_requests": self.successful_requests,
                    "failed_requests": self.failed_requests,
                    "success_rate": (
                        self.successful_requests / self.total_requests * 100
                        if self.total_requests > 0
                        else 0
                    ),
                },
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
            }

    def get_metrics(self) -> dict[str, Any]:
        """Get service metrics.

        Returns:
            Metrics dictionary
        """
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": (
                self.successful_requests / self.total_requests * 100
                if self.total_requests > 0
                else 0
            ),
            "llm_stats": {
                "tokens_seen": self.llm.stats.tokens_seen,
                "tokens_retained": self.llm.stats.tokens_retained,
                "compression_ratio": self.llm.stats.compression_ratio,
                "evictions": self.llm.stats.evictions,
            },
        }

    def reset_conversation(self):
        """Reset conversation state."""
        logger.info("Resetting conversation state")
        self.llm.reset()

    def save_checkpoint(self, path: str) -> str:
        """Save conversation checkpoint.

        Args:
            path: Path to save checkpoint

        Returns:
            Path to saved checkpoint
        """
        logger.info(f"Saving checkpoint to {path}")
        return self.llm.save_checkpoint(path)

    def load_checkpoint(self, path: str):
        """Load conversation checkpoint.

        Args:
            path: Path to checkpoint file
        """
        logger.info(f"Loading checkpoint from {path}")
        self.llm.load_checkpoint(path)


def main():
    """Example production deployment."""
    print("=" * 70)
    print("PRODUCTION DEPLOYMENT EXAMPLE")
    print("=" * 70)

    # Initialize service
    print("\n[1/4] Initializing service...")
    service = ProductionLLMService(
        model_name="gpt2", device="cpu", max_tokens=1024, memory_policy="hybrid"
    )
    print("✓ Service initialized")

    # Health check
    print("\n[2/4] Running health check...")
    health = service.health_check()
    print(f"✓ Health status: {health['status']}")

    # Example conversation
    print("\n[3/4] Testing conversation...")
    messages = [
        "Hello! How are you?",
        "What can you tell me about AI?",
        "That's interesting. Tell me more.",
    ]

    for _i, message in enumerate(messages, 1):
        print(f"\n  User: {message}")
        result = service.chat(message, max_new_tokens=50, user_id="demo_user")

        if result["success"]:
            print(f"  Bot: {result['response'][:100]}...")
            print(
                f"  Metrics: {result['metadata']['tokens_used']} tokens, "
                f"{result['metadata']['latency_ms']:.1f}ms"
            )
        else:
            print(f"  Error: {result['error']}")

    # Get metrics
    print("\n[4/4] Service metrics...")
    metrics = service.get_metrics()
    print(f"  Total requests: {metrics['total_requests']}")
    print(f"  Success rate: {metrics['success_rate']:.1f}%")
    print(f"  Compression ratio: {metrics['llm_stats']['compression_ratio']:.2f}x")

    print("\n" + "=" * 70)
    print("✓ Production deployment example complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
