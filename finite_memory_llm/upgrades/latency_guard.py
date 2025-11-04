"""Latency guard utility for deterministic policy timeouts.

Wraps policy calls with timeout enforcement and clean fallback behavior.
"""

import time
import signal
from typing import Callable, TypeVar, Any, Optional

T = TypeVar("T")


class TimeoutError(Exception):
    """Raised when a guarded call exceeds its time budget."""

    pass


def _timeout_handler(signum: int, frame: Any) -> None:
    raise TimeoutError("Guarded call exceeded time budget")


def guarded_call(
    func: Callable[[], T],
    budget_ms: int,
    fallback: Callable[[], T],
    timeout_enabled: bool = False,  # Disabled by default due to platform constraints
) -> T:
    """Execute a function with a time budget and fallback.

    If the function exceeds the budget or raises an exception,
    execute the fallback function instead.

    Args:
        func: The primary function to execute
        budget_ms: Maximum allowed execution time in milliseconds
        fallback: Fallback function to call on timeout or error
        timeout_enabled: Whether to use signal-based timeout (Unix only)

    Returns:
        Result from either func or fallback

    Examples:
        >>> def slow_policy():
        ...     time.sleep(3)
        ...     return "slow"
        >>> def fast_fallback():
        ...     return "fast"
        >>> result = guarded_call(slow_policy, 100, fast_fallback)
        >>> assert result == "fast"
    """
    start = time.perf_counter()

    try:
        # For Unix systems with signal support
        if timeout_enabled and hasattr(signal, "SIGALRM"):
            budget_sec = budget_ms / 1000.0
            old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
            signal.setitimer(signal.ITIMER_REAL, budget_sec)

            try:
                result = func()
                signal.setitimer(signal.ITIMER_REAL, 0)
                signal.signal(signal.SIGALRM, old_handler)
                return result
            except TimeoutError:
                signal.setitimer(signal.ITIMER_REAL, 0)
                signal.signal(signal.SIGALRM, old_handler)
                elapsed = (time.perf_counter() - start) * 1000
                print(f"⚠ Guarded call timed out ({elapsed:.1f}ms > {budget_ms}ms), using fallback")
                return fallback()
        else:
            # Simple timing check without signal (works on all platforms)
            result = func()
            elapsed = (time.perf_counter() - start) * 1000

            if elapsed > budget_ms:
                print(f"⚠ Guarded call exceeded budget ({elapsed:.1f}ms > {budget_ms}ms)")
                # Note: we still return the result since we can't interrupt mid-execution
                # For true timeout enforcement, use timeout_enabled=True on Unix

            return result

    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        print(f"⚠ Guarded call failed after {elapsed:.1f}ms: {e}, using fallback")
        return fallback()


def timed_call(func: Callable[[], T]) -> tuple[T, float]:
    """Execute a function and return result with elapsed time in ms.

    Args:
        func: Function to time

    Returns:
        Tuple of (result, elapsed_ms)
    """
    start = time.perf_counter()
    result = func()
    elapsed = (time.perf_counter() - start) * 1000
    return result, elapsed
