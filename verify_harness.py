from data import load_humaneval
from execute import build_program, run_program

problems = load_humaneval()

# Test 1: correct solutions should all PASS
passed = 0
for p in problems:
    r = run_program(build_program(p, p["canonical_solution"]))
    if r["passed"]:
        passed += 1
    else:
        print("Reference FAILED:", p["task_id"], r["error"][-200:])
print(f"Reference solutions: {passed}/{len(problems)} passed (expect 164)")

# Test 2: a wrong solution should FAIL
wrong = "    return None\n"
false_passes = sum(run_program(build_program(p, wrong))["passed"] for p in problems)
print(f"Dummy 'return None': {false_passes}/{len(problems)} passed (expect ~0)")

# Test 3: an infinite loop should TIME OUT, not hang forever
r = run_program(build_program(problems[0], "    while True: pass\n"), timeout=3)
print("Infinite loop result:", r)