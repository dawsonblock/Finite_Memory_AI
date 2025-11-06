#!/usr/bin/env python3
"""Tests for utility functions."""

import pytest
import time

from finite_memory_llm.utils import (
    timer,
    retry_with_backoff,
    truncate_text,
    format_bytes,
    safe_divide,
    clamp,
    validate_positive_int,
    validate_range,
)


class TestTimer:
    """Test timer context manager."""

    def test_timer_basic(self):
        """Test basic timer functionality."""
        with timer("test") as t:
            time.sleep(0.01)  # Sleep for 10ms

        assert "elapsed" in t
        assert t["elapsed"] >= 0.01
        assert t["elapsed"] < 0.1  # Should be much less than 100ms

    def test_timer_zero_time(self):
        """Test timer with minimal operation."""
        with timer() as t:
            pass

        assert "elapsed" in t
        assert t["elapsed"] >= 0


class TestRetryWithBackoff:
    """Test retry with backoff."""

    def test_retry_success_first_try(self):
        """Test successful function on first try."""
        call_count = [0]

        def success_func():
            call_count[0] += 1
            return "success"

        result = retry_with_backoff(success_func, max_retries=3)
        assert result == "success"
        assert call_count[0] == 1

    def test_retry_success_after_failures(self):
        """Test successful function after some failures."""
        call_count = [0]

        def flaky_func():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ValueError("Temporary error")
            return "success"

        result = retry_with_backoff(
            flaky_func,
            max_retries=3,
            initial_delay=0.01,
            exceptions=(ValueError,),
        )
        assert result == "success"
        assert call_count[0] == 3

    def test_retry_all_failures(self):
        """Test function that always fails."""

        def always_fails():
            raise ValueError("Always fails")

        with pytest.raises(ValueError, match="Always fails"):
            retry_with_backoff(
                always_fails,
                max_retries=2,
                initial_delay=0.01,
            )


class TestTruncateText:
    """Test text truncation."""

    def test_truncate_short_text(self):
        """Test truncating text shorter than max length."""
        text = "Short"
        result = truncate_text(text, max_length=100)
        assert result == "Short"

    def test_truncate_long_text(self):
        """Test truncating long text."""
        text = "This is a very long text that should be truncated"
        result = truncate_text(text, max_length=20)
        assert len(result) == 20
        assert result.endswith("...")

    def test_truncate_custom_suffix(self):
        """Test truncating with custom suffix."""
        text = "Long text here"
        result = truncate_text(text, max_length=10, suffix=">>")
        assert len(result) == 10
        assert result.endswith(">>")


class TestFormatBytes:
    """Test byte formatting."""

    def test_format_bytes_small(self):
        """Test formatting small byte counts."""
        assert "B" in format_bytes(100)

    def test_format_kb(self):
        """Test formatting kilobytes."""
        result = format_bytes(1536)  # 1.5 KB
        assert "KB" in result
        assert "1.5" in result

    def test_format_mb(self):
        """Test formatting megabytes."""
        result = format_bytes(1024 * 1024 * 2)  # 2 MB
        assert "MB" in result

    def test_format_gb(self):
        """Test formatting gigabytes."""
        result = format_bytes(1024 * 1024 * 1024 * 3)  # 3 GB
        assert "GB" in result


class TestSafeDivide:
    """Test safe division."""

    def test_safe_divide_normal(self):
        """Test normal division."""
        result = safe_divide(10, 2)
        assert result == 5.0

    def test_safe_divide_by_zero(self):
        """Test division by zero returns default."""
        result = safe_divide(10, 0, default=0.0)
        assert result == 0.0

    def test_safe_divide_custom_default(self):
        """Test division by zero with custom default."""
        result = safe_divide(10, 0, default=-1.0)
        assert result == -1.0


class TestClamp:
    """Test value clamping."""

    def test_clamp_within_range(self):
        """Test clamping value within range."""
        assert clamp(5, 0, 10) == 5

    def test_clamp_below_min(self):
        """Test clamping value below minimum."""
        assert clamp(-5, 0, 10) == 0

    def test_clamp_above_max(self):
        """Test clamping value above maximum."""
        assert clamp(15, 0, 10) == 10

    def test_clamp_at_boundaries(self):
        """Test clamping at exact boundaries."""
        assert clamp(0, 0, 10) == 0
        assert clamp(10, 0, 10) == 10


class TestValidatePositiveInt:
    """Test positive integer validation."""

    def test_validate_positive_int_valid(self):
        """Test validating valid positive integer."""
        validate_positive_int(10, "test_param")
        # Should not raise

    def test_validate_positive_int_zero(self):
        """Test validating zero raises error."""
        with pytest.raises(ValueError, match="must be positive"):
            validate_positive_int(0, "test_param")

    def test_validate_positive_int_negative(self):
        """Test validating negative raises error."""
        with pytest.raises(ValueError, match="must be positive"):
            validate_positive_int(-5, "test_param")

    def test_validate_positive_int_wrong_type(self):
        """Test validating non-integer raises error."""
        with pytest.raises(TypeError, match="must be an integer"):
            validate_positive_int(5.5, "test_param")  # type: ignore


class TestValidateRange:
    """Test range validation."""

    def test_validate_range_valid(self):
        """Test validating value within range."""
        validate_range(0.5, 0.0, 1.0, "test_param")
        # Should not raise

    def test_validate_range_at_boundaries(self):
        """Test validating values at boundaries."""
        validate_range(0.0, 0.0, 1.0, "test_param")
        validate_range(1.0, 0.0, 1.0, "test_param")
        # Should not raise

    def test_validate_range_below_min(self):
        """Test validating value below minimum."""
        with pytest.raises(ValueError, match="must be between"):
            validate_range(-0.1, 0.0, 1.0, "test_param")

    def test_validate_range_above_max(self):
        """Test validating value above maximum."""
        with pytest.raises(ValueError, match="must be between"):
            validate_range(1.1, 0.0, 1.0, "test_param")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
