from datasets import load_dataset

ds = load_dataset("openai/openai_humaneval", split="test")

print("Number of problems:", len(ds))
print("Fields:", ds.column_names)

problem = ds[0]
for field in ds.column_names:
    print("\n" + "=" * 20, field, "=" * 20)
    print(problem[field])