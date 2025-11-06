#!/usr/bin/env python3
"""Real import time profiling - honest measurements.

This script measures ACTUAL import times, not theoretical ones.
"""

import sys
import time
from pathlib import Path


def profile_import_isolated(module_name: str, description: str) -> float:
    """Profile import time in isolated subprocess."""
    code = f"""
import time
start = time.perf_counter()
import {module_name}
elapsed = time.perf_counter() - start
print(elapsed)
"""
    
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            elapsed = float(result.stdout.strip())
            print(f"✓ {description:40} {elapsed:.3f}s")
            return elapsed
        else:
            print(f"✗ {description:40} FAILED")
            return 0.0
    except Exception as e:
        print(f"✗ {description:40} ERROR: {e}")
        return 0.0


def main():
    print("=" * 70)
    print("HONEST IMPORT TIME PROFILING (Isolated)")
    print("=" * 70)
    print()
    
    results = {}
    
    # Test 1: Lightweight interfaces (should be <0.01s)
    print("[1] Lightweight Interfaces")
    print("-" * 70)
    results["interfaces"] = measure_import(
        "finite_memory_llm.interfaces",
        "Interfaces only (no torch)"
    )
    print()
    
    # Test 2: Core with torch (the real cost)
    print("[2] Core Module (with torch/transformers)")
    print("-" * 70)
    results["core"] = measure_import(
        "finite_memory_llm.core",
        "Core (torch + transformers)"
    )
    print()
    
    # Test 3: Full package
    print("[3] Full Package Import")
    print("-" * 70)
    results["full"] = measure_import(
        "finite_memory_llm",
        "Full package"
    )
    print()
    
    # Test 4: Optional modules (lazy loaded)
    print("[4] Optional Modules (lazy loaded)")
    print("-" * 70)
    
    # These should NOT load until accessed
    import finite_memory_llm
    
    start = time.perf_counter()
    _ = finite_memory_llm.AsyncCompleteFiniteMemoryLLM  # Trigger lazy load
    elapsed = time.perf_counter() - start
    results["async"] = elapsed
    print(f"✓ {'Async module (lazy)':40s} {elapsed:6.3f}s")
    
    start = time.perf_counter()
    _ = finite_memory_llm.LanguageDetector  # Trigger lazy load
    elapsed = time.perf_counter() - start
    results["multilingual"] = elapsed
    print(f"✓ {'Multilingual module (lazy)':40s} {elapsed:6.3f}s")
    
    start = time.perf_counter()
    _ = finite_memory_llm.CohereBackend  # Trigger lazy load
    elapsed = time.perf_counter() - start
    results["backends"] = elapsed
    print(f"✓ {'Backends module (lazy)':40s} {elapsed:6.3f}s")
    print()
    
    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Interfaces only:     {results['interfaces']:6.3f}s  (lightweight ✓)")
    print(f"Core (with torch):   {results['core']:6.3f}s  (heavy deps)")
    print(f"Full package:        {results['full']:6.3f}s  (includes core)")
    print(f"Async (lazy):        {results['async']:6.3f}s  (on-demand)")
    print(f"Multilingual (lazy): {results['multilingual']:6.3f}s  (on-demand)")
    print(f"Backends (lazy):     {results['backends']:6.3f}s  (on-demand)")
    print()
    
    # Honest assessment
    print("=" * 70)
    print("HONEST ASSESSMENT")
    print("=" * 70)
    
    if results["interfaces"] < 0.05:
        print("✓ Interfaces are truly lightweight (<0.05s)")
    else:
        print("✗ Interfaces are slower than expected")
    
    if results["core"] > 1.0:
        print(f"⚠ Core is SLOW ({results['core']:.1f}s) - torch/transformers overhead")
    else:
        print(f"✓ Core is reasonably fast ({results['core']:.1f}s)")
    
    lazy_total = results["async"] + results["multilingual"] + results["backends"]
    if lazy_total < 0.5:
        print(f"✓ Lazy loading works well ({lazy_total:.2f}s total for optional)")
    else:
        print(f"⚠ Lazy loading overhead is high ({lazy_total:.2f}s)")
    
    print()
    print("RECOMMENDATION:")
    if results["core"] > 2.0:
        print("  → Core needs conditional imports for torch/transformers")
        print("  → Consider splitting into finite-memory-llm-core (no torch)")
        print("  → and finite-memory-llm[local] (with torch)")
    else:
        print("  → Import times are acceptable for production use")
    
    print("=" * 70)


if __name__ == "__main__":
    main()
