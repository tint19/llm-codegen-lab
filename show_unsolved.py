import json

for line in open("results/search_k5.jsonl"):
    r = json.loads(line)
    if r["n_correct"] == 0:
        vis = sum(c["visible"] for c in r["candidates"])
        print(f"{r['task_id']}: 0/5 correct, {vis}/5 passed visible tests")