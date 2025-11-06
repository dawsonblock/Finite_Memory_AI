"""Utility functions for Finite Memory AI.

Common helper functions used across the codebase.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Any, Callable, Generator, TypeVar

T = TypeVar("T")


@contextmanager
def timer(name: str = "Operation") -> Generator[dict[str, float], None, None]:
    """Context manager for timing operations.
    
    Args:
        name: Name of the operation being timed
        
    Yields:
        Dictionary that will contain 'elapsed' key with time in seconds
        
    Example:
        >>> with timer("My operation") as t:
        ...     # do something
        ...     pass
        >>> print(f"Took {t['elapsed']:.3f}s")
    """
    result: dict[str, float] = {}
    start = time.perf_counter()
    try:
        yield result
    finally:
        result["elapsed"] = time.perf_counter() - start


def retry_with_backoff(
    func: Callable[..., T],
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> T:
    """Retry a function with exponential backoff.
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Multiplier for delay after each retry
        exceptions: Tuple of exception types to catch and retry
        
    Returns:
        Result of the function call
        
    Raises:
        Last exception if all retries fail
        
    Example:
        >>> def flaky_api_call():
        ...     # might fail sometimes
        ...     return "success"
        >>> result = retry_with_backoff(flaky_api_call, max_retries=3)
    """
    delay = initial_delay
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return func()
        except exceptions as e:
            last_exception = e
            if attempt < max_retries:
                time.sleep(delay)
                delay *= backoff_factor
            else:
                raise last_exception from None
    
    # Should never reach here, but for type checker
    raise last_exception  # type: ignore


def truncate_text(
    text: str,
    max_length: int = 100,
    suffix: str = "...",
) -> str:
    """Truncate text to maximum length with suffix.
    
    Args:
        text: Text to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
        
    Example:
        >>> truncate_text("This is a very long text", max_length=10)
        'This is...'
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def format_bytes(num_bytes: int) -> str:
    """Format bytes as human-readable string.
    
    Args:
        num_bytes: Number of bytes
        
    Returns:
        Formatted string (e.g., "1.5 MB")
        
    Example:
        >>> format_bytes(1536)
        '1.5 KB'
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(num_bytes) < 1024.0:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} PB"


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divide two numbers, returning default if denominator is zero.
    
    Args:
        numerator: Numerator
        denominator: Denominator
        default: Default value if denominator is zero
        
    Returns:
        Result of division or default
        
    Example:
        >>> safe_divide(10, 2)
        5.0
        >>> safe_divide(10, 0, default=0.0)
        0.0
    """
    if denominator == 0:
        return default
    return numerator / denominator


def clamp(value: float, min_value: float, max_value: float) -> float:
    """Clamp a value between min and max.
    
    Args:
        value: Value to clamp
        min_value: Minimum value
        max_value: Maximum value
        
    Returns:
        Clamped value
        
    Example:
        >>> clamp(5, 0, 10)
        5
        >>> clamp(-5, 0, 10)
        0
        >>> clamp(15, 0, 10)
        10
    """
    return max(min_value, min(value, max_value))


def get_memory_usage() -> dict[str, Any]:
    """Get current memory usage statistics.
    
    Returns:
        Dictionary with memory usage info
        
    Example:
        >>> stats = get_memory_usage()
        >>> print(f"RSS: {stats['rss_mb']:.1f} MB")
    """
    try:
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()
        
        return {
            "rss_bytes": mem_info.rss,
            "rss_mb": mem_info.rss / (1024 * 1024),
            "vms_bytes": mem_info.vms,
            "vms_mb": mem_info.vms / (1024 * 1024),
        }
    except ImportError:
        # psutil not available
        return {
            "rss_bytes": 0,
            "rss_mb": 0.0,
            "vms_bytes": 0,
            "vms_mb": 0.0,
            "error": "psutil not installed",
        }


def validate_positive_int(value: int, name: str = "value") -> None:
    """Validate that a value is a positive integer.
    
    Args:
        value: Value to validate
        name: Name of the parameter (for error messages)
        
    Raises:
        ValueError: If value is not a positive integer
        
    Example:
        >>> validate_positive_int(10, "max_tokens")
        >>> validate_positive_int(-5, "max_tokens")
        Traceback (most recent call last):
        ValueError: max_tokens must be positive, got -5
    """
    if not isinstance(value, int):
        raise TypeError(f"{name} must be an integer, got {type(value).__name__}")
    if value <= 0:
        raise ValueError(f"{name} must be positive, got {value}")


def validate_range(
    value: float,
    min_val: float,
    max_val: float,
    name: str = "value",
) -> None:
    """Validate that a value is within a range.
    
    Args:
        value: Value to validate
        min_val: Minimum allowed value (inclusive)
        max_val: Maximum allowed value (inclusive)
        name: Name of the parameter (for error messages)
        
    Raises:
        ValueError: If value is outside the range
        
    Example:
        >>> validate_range(0.5, 0.0, 1.0, "temperature")
        >>> validate_range(1.5, 0.0, 1.0, "temperature")
        Traceback (most recent call last):
        ValueError: temperature must be between 0.0 and 1.0, got 1.5
    """
    if not min_val <= value <= max_val:
        raise ValueError(
            f"{name} must be between {min_val} and {max_val}, got {value}"
        )
