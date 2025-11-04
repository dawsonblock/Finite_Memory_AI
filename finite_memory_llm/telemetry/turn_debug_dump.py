"""Turn-level debug dumping for offline analysis.

Writes detailed turn information to JSONL for:
- Debugging policy behavior
- Offline accuracy evaluation
- Cost analysis
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import asdict


class TurnDumper:
    """Write turn-level debug information to JSONL file.
    
    Each line contains:
    - Timestamp
    - Input/output text
    - Token counts
    - Memory statistics
    - Policy decisions
    
    Args:
        enabled: Whether to write dumps
        path: Output file path
        buffer_size: Number of turns to buffer before writing
    """
    
    def __init__(
        self,
        enabled: bool = False,
        path: str = "logs/turns.jsonl",
        buffer_size: int = 10
    ):
        self.enabled = enabled
        self.path = Path(path)
        self.buffer_size = buffer_size
        
        self._buffer: list[Dict[str, Any]] = []
        self._turn_count = 0
        
        if self.enabled:
            # Ensure directory exists
            self.path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create or append to file
            if not self.path.exists():
                self.path.touch()
    
    def write(
        self,
        stats: Any,
        input_text: str,
        output_text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Write turn information to dump file.
        
        Args:
            stats: MemoryStats object
            input_text: User input
            output_text: Model output
            metadata: Optional additional metadata
        """
        if not self.enabled:
            return
        
        self._turn_count += 1
        
        # Build turn record
        record = {
            "turn": self._turn_count,
            "timestamp": time.time(),
            "input": input_text,
            "output": output_text,
            "stats": asdict(stats),
        }
        
        if metadata:
            record["metadata"] = metadata
        
        # Add to buffer
        self._buffer.append(record)
        
        # Flush if buffer is full
        if len(self._buffer) >= self.buffer_size:
            self.flush()
    
    def flush(self) -> None:
        """Write buffered records to file."""
        if not self._buffer or not self.enabled:
            return
        
        try:
            with open(self.path, "a") as f:
                for record in self._buffer:
                    f.write(json.dumps(record) + "\n")
            
            self._buffer.clear()
        
        except Exception as e:
            print(f"⚠ Failed to write turn dump: {e}")
    
    def read_turns(
        self,
        limit: Optional[int] = None
    ) -> list[Dict[str, Any]]:
        """Read turn records from dump file.
        
        Args:
            limit: Maximum number of turns to read (most recent)
        
        Returns:
            List of turn records
        """
        if not self.path.exists():
            return []
        
        turns = []
        try:
            with open(self.path, "r") as f:
                for line in f:
                    if line.strip():
                        turns.append(json.loads(line))
            
            if limit:
                turns = turns[-limit:]
            
            return turns
        
        except Exception as e:
            print(f"⚠ Failed to read turn dump: {e}")
            return []
    
    def get_stats_summary(self) -> Dict[str, Any]:
        """Get summary statistics from dump file.
        
        Returns:
            Dictionary of aggregate statistics
        """
        turns = self.read_turns()
        
        if not turns:
            return {"total_turns": 0}
        
        # Calculate aggregates
        total_tokens_seen = sum(t["stats"]["tokens_seen"] for t in turns)
        total_tokens_retained = sum(t["stats"]["tokens_retained"] for t in turns)
        total_evictions = sum(t["stats"]["evictions"] for t in turns)
        
        compression_ratios = [t["stats"]["compression_ratio"] for t in turns]
        policy_latencies = [t["stats"]["policy_latency_ms"] for t in turns]
        fallback_count = sum(t["stats"]["fallback_count"] for t in turns)
        
        return {
            "total_turns": len(turns),
            "total_tokens_seen": total_tokens_seen,
            "total_tokens_retained": total_tokens_retained,
            "total_evictions": total_evictions,
            "avg_compression_ratio": sum(compression_ratios) / len(compression_ratios),
            "avg_policy_latency_ms": sum(policy_latencies) / len(policy_latencies),
            "total_fallbacks": fallback_count,
            "first_turn_time": turns[0]["timestamp"],
            "last_turn_time": turns[-1]["timestamp"],
        }
    
    def __del__(self):
        """Flush buffer on cleanup."""
        self.flush()
