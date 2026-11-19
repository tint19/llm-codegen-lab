import json

with open("results/baseline.jsonl") as f:
    rows = [json.loads(line) for line in f]

failures = [r for r in rows if not r["passed"]]
print(f"{len(failures)} failures out of {len(rows)}\n")

for r in failures:
    last_line = r["error"].strip().splitlines()[-1] if r["error"].strip() else "(no error text)"
    print("=" * 60)
    print(r["task_id"], "->", last_line)
    print("-" * 60)
    print(r["code"])