import ast
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from math import comb
from pathlib import Path

from data import load_humaneval
from execute import build_program_full, build_visible_program, run_program
from llm import DEFAULT_MODEL, extract_code, generate
from prompts import SOLVE_SYSTEM

K = int(sys.argv[1]) if len(sys.argv) > 1 else 5
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else None


def parses(code):
    """Static check: is it valid Python? Parsing does NOT run the code."""
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False


def pass_at_k(n, c, k):
    """Unbiased pass@k estimator from the Codex paper (n samples, c correct)."""
    if n - c < k:
        return 1.0
    return 1.0 - comb(n - c, k) / comb(n, k)


def sample(problem, i):
    text = generate([{"role": "user", "content": problem["prompt"]}],
                    system=SOLVE_SYSTEM, sample_id=i)
    return extract_code(text)


problems = load_humaneval()
problems = problems[:LIMIT] if LIMIT else problems
visible = json.load(open("artifacts/visible_tests.json"))

Path("results").mkdir(exist_ok=True)
out_path = Path(f"results/search_k{K}.jsonl")

n = len(problems)
selected_pass = 0
calls_used = 0
pass1_sum = 0.0
passk_sum = 0.0
start = time.time()

with ThreadPoolExecutor(max_workers=K) as pool, out_path.open("w") as out:
    for idx, p in enumerate(problems):
        tid = p["task_id"]
        codes = list(pool.map(lambda i: sample(p, i), range(K)))

        cands = []
        for i, code in enumerate(codes):
            ok = parses(code)
            vis = ok and run_program(build_visible_program(p, code, visible[tid]))["passed"]
            hid = ok and run_program(build_program_full(p, code))["passed"]  # scoring only
            cands.append({"i": i, "parses": ok, "visible": vis, "hidden": hid, "code": code})

        # SELECTION uses only parse + visible results. Never c["hidden"].
        chosen = next((c for c in cands if c["visible"]), cands[0])
        calls_used += (chosen["i"] + 1) if chosen["visible"] else K
        selected_pass += chosen["hidden"]

        c_correct = sum(c["hidden"] for c in cands)
        pass1_sum += c_correct / K
        passk_sum += pass_at_k(K, c_correct, K)

        out.write(json.dumps({
            "task_id": tid, "n_correct": c_correct, "chosen": chosen["i"],
            "chosen_passed": chosen["hidden"], "candidates": cands,
        }) + "\n")
        print(f"[{idx+1}/{n}] {tid}: {c_correct}/{K} correct, "
              f"chose #{chosen['i']} -> {'PASS' if chosen['hidden'] else 'FAIL'}")

print(f"\nModel: {DEFAULT_MODEL}, K = {K}, problems = {n}")
print(f"Average pass@1 (mean over {K} samples): {pass1_sum/n:.1%}")
print(f"pass@1 WITH search (selected):         {selected_pass}/{n} = {selected_pass/n:.1%}")
print(f"pass@{K} (oracle upper bound):            {passk_sum/n:.1%}")
print(f"Avg API calls if stopping at first visible pass: {calls_used/n:.2f}")
print(f"Time: {time.time()-start:.0f}s")