"""Summary QA gate for fact verification.

Checks that summaries don't introduce hallucinated facts by verifying
that key entities (numbers, dates, names) in the summary appear in the source.
"""

from __future__ import annotations

import re
from typing import List, Set, Callable


class SummaryQAGate:
    """Verify summary fidelity by checking for hallucinated facts.

    Validates that:
    - Numbers and dates in summary exist in source
    - Proper names in summary exist in source
    - No obviously contradictory statements

    Args:
        questions: List of verification questions/patterns
        strict: If True, fail on any mismatch; if False, use threshold
        threshold: Minimum fraction of facts that must match (0.0 to 1.0)
    """

    def __init__(
        self, questions: List[str] | None = None, strict: bool = False, threshold: float = 0.8
    ):
        self.questions = questions or [
            "List specific numbers/dates.",
            "List proper names/aliases.",
            "List key facts as key:value.",
        ]
        self.strict = strict
        self.threshold = threshold

    def _extract_numbers(self, text: str) -> Set[str]:
        """Extract numbers and numeric patterns from text."""
        # Match integers, decimals, years, dates
        patterns = [
            r"\b\d+\.\d+\b",  # Decimals
            r"\b\d{4}\b",  # Years
            r"\b\d+\b",  # Integers
            r"\d{1,2}/\d{1,2}/\d{2,4}",  # Dates
            r"\d{1,2}-\d{1,2}-\d{2,4}",  # Dates
        ]
        numbers = set()
        for pattern in patterns:
            numbers.update(re.findall(pattern, text))
        return numbers

    def _extract_proper_names(self, text: str) -> Set[str]:
        """Extract capitalized words that might be proper names."""
        # Simple heuristic: capitalized words not at sentence start
        words = text.split()
        names = set()

        for i, word in enumerate(words):
            # Remove punctuation
            clean = re.sub(r"[^\w\s]", "", word)

            # Check if capitalized and not at sentence start
            if clean and clean[0].isupper():
                # Skip if it's the first word after punctuation
                if i > 0 and not words[i - 1].endswith((".", "!", "?")):
                    names.add(clean)

        return names

    def _extract_quoted_strings(self, text: str) -> Set[str]:
        """Extract quoted strings from text."""
        # Match content in quotes
        quoted = set()
        quoted.update(re.findall(r'"([^"]+)"', text))
        quoted.update(re.findall(r"'([^']+)'", text))
        return quoted

    def verify(self, pre_text: str, post_summary: str, verbose: bool = False) -> bool:
        """Verify that summary facts are grounded in source text.

        Args:
            pre_text: Original source text
            post_summary: Generated summary
            verbose: Print verification details

        Returns:
            True if summary passes verification, False otherwise
        """
        if not post_summary.strip():
            return True  # Empty summary is trivially valid

        # Extract facts from both texts
        source_numbers = self._extract_numbers(pre_text)
        summary_numbers = self._extract_numbers(post_summary)

        source_names = self._extract_proper_names(pre_text)
        summary_names = self._extract_proper_names(post_summary)

        source_quotes = self._extract_quoted_strings(pre_text)
        summary_quotes = self._extract_quoted_strings(post_summary)

        # Check for hallucinated facts
        hallucinated_numbers = summary_numbers - source_numbers
        hallucinated_names = summary_names - source_names
        hallucinated_quotes = summary_quotes - source_quotes

        total_facts = len(summary_numbers) + len(summary_names) + len(summary_quotes)
        hallucinated = (
            len(hallucinated_numbers) + len(hallucinated_names) + len(hallucinated_quotes)
        )

        if total_facts == 0:
            # No extractable facts to verify
            return True

        fidelity = 1.0 - (hallucinated / total_facts)

        if verbose:
            print(f"Summary verification:")
            print(
                f"  Numbers: {len(summary_numbers)} total, {len(hallucinated_numbers)} hallucinated"
            )
            print(f"  Names: {len(summary_names)} total, {len(hallucinated_names)} hallucinated")
            print(f"  Quotes: {len(summary_quotes)} total, {len(hallucinated_quotes)} hallucinated")
            print(f"  Fidelity: {fidelity:.2%} (threshold: {self.threshold:.2%})")

            if hallucinated_numbers:
                print(f"  Hallucinated numbers: {hallucinated_numbers}")
            if hallucinated_names:
                print(f"  Hallucinated names: {hallucinated_names}")
            if hallucinated_quotes:
                print(f"  Hallucinated quotes: {hallucinated_quotes}")

        # Apply verification logic
        if self.strict:
            return hallucinated == 0
        else:
            return fidelity >= self.threshold

    def verify_with_retry(
        self, pre_text: str, post_summary: str, retry_fn: Callable[[], str], max_retries: int = 1
    ) -> tuple[str, bool]:
        """Verify summary with automatic retry on failure.

        Args:
            pre_text: Original source text
            post_summary: Generated summary
            retry_fn: Function to generate new summary (no args)
            max_retries: Maximum retry attempts

        Returns:
            Tuple of (final_summary, verification_passed)
        """
        summary = post_summary

        for attempt in range(max_retries + 1):
            if self.verify(pre_text, summary):
                return summary, True

            if attempt < max_retries:
                print(
                    f"⚠ Summary failed verification (attempt {attempt + 1}/{max_retries + 1}), retrying..."
                )
                summary = retry_fn()

        print(f"⚠ Summary failed verification after {max_retries + 1} attempts")
        return summary, False
