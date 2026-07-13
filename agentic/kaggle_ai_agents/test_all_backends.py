#!/usr/bin/env python3
"""Test all 3 backends and compare outputs."""

import json
import subprocess
import sys
from pathlib import Path


def run_backend(backend_name, runner_module):
    """Run a backend and return output file path."""
    print(f"\n{'='*60}")
    print(f"Testing: {backend_name}")
    print('='*60)
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", runner_module],
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True,
            timeout=120,
        )
        
        if result.returncode != 0:
            print(f"❌ {backend_name} failed:")
            print(result.stderr[:500])
            return None
        
        print(result.stdout)
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print(f"❌ {backend_name} timed out")
        return None
    except Exception as e:
        print(f"❌ {backend_name} error: {str(e)[:100]}")
        return None


def main():
    """Test all backends."""
    print("\n🚀 Testing All 3 Backends\n")
    
    backends = [
        ("fully_scripted", "src.fully_scripted.runner"),
        ("google_adk (requires GEMINI_API_KEY)", "src.google_adk.runner"),
        ("ollama_agent (requires LangChain + Ollama)", "src.ollama_agent.runner"),
    ]
    
    results = {}
    for name, module in backends:
        result = run_backend(name, module)
        results[name] = result
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for name, result in results.items():
        status = "✅ PASSED" if result else "⏭️  SKIPPED/FAILED"
        print(f"  {name}: {status}")
    
    # Check outputs
    output_dir = Path(__file__).parent
    outputs = [
        output_dir / "brief_output.json",
        output_dir / "brief_output_adk.json",
        output_dir / "brief_output_ollama.json",
    ]
    
    print(f"\nOutput files:")
    for out in outputs:
        if out.exists():
            with open(out) as f:
                data = json.load(f)
            print(f"  ✅ {out.name} ({len(data.get('cards', []))} cards)")
        else:
            print(f"  ❌ {out.name} (not found)")


if __name__ == "__main__":
    main()
