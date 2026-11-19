import json

from data import load_humaneval
from execute import build_visible_program, run_program

problems = {p["task_id"]: p for p in load_humaneval()}
visible = json.load(open("artifacts/visible_tests.json"))
rows = [json.loads(line) for line in open("results/baseline.jsonl")]

counts = {"both pass": 0, "both fail": 0,
          "visible pass, hidden FAIL": 0, "visible FAIL, hidden pass": 0}

for r in rows:
    p = problems[r["task_id"]]
    v = run_program(build_visible_program(p, r["code"], visible[r["task_id"]]))["passed"]
    h = r["passed"]
    if v and h:
        counts["both pass"] += 1
    elif not v and not h:
        counts["both fail"] += 1
        print("Caught by visible tests:", r["task_id"])
    elif v and not h:
        counts["visible pass, hidden FAIL"] += 1
        print("MISSED (passes visible, fails hidden):", r["task_id"])
    else:
        counts["visible FAIL, hidden pass"] += 1
        print("FALSE ALARM (fails visible, passes hidden):", r["task_id"])

print()
for k, v in counts.items():
    print(f"{k:28s} {v}")