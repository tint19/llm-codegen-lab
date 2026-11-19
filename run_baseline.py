import json
import sys
import time
from pathlib import Path

from data import load_humaneval
from execute import build_program_full, run_program
from llm import DEFAULT_MODEL, extract_code, generate
from prompts import SOLVE_SYSTEM as SYSTEM

limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
problems = load_humaneval()
problems = problems[:limit] if limit else problems

Path("results").mkdir(exist_ok=True)
out_path = Path("results/baseline.jsonl")

passed = 0
start = time.time()
with out_path.open("w") as out:
    for i, p in enumerate(problems):
        text = generate([{"role": "user", "content": p["prompt"]}], system=SYSTEM)
        code = extract_code(text)
        r = run_program(build_program_full(p, code))
        passed += r["passed"]
        out.write(json.dumps({
            "task_id": p["task_id"], "passed": r["passed"],
            "error": r["error"], "code": code,
        }) + "\n")
        print(f"[{i+1}/{len(problems)}] {p['task_id']}: {'PASS' if r['passed'] else 'FAIL'}")

n = len(problems)
print(f"\nModel: {DEFAULT_MODEL}")
print(f"Baseline pass@1: {passed}/{n} = {passed/n:.1%}  ({time.time()-start:.0f}s)")