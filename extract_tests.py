import json
from pathlib import Path

from data import load_humaneval
from execute import run_program
from llm import extract_code, generate

SYSTEM = (
    "You convert the examples written in a Python docstring into assert statements. "
    "Only use examples that literally appear in the docstring; never invent new ones. "
    "Write exactly one assert per line, calling the function by its name. "
    "Return them in a single ```python code block. "
    "If the docstring has no examples, return an empty code block."
)


def extract_visible_tests(problem):
    """Ask Claude to turn docstring examples into assert lines."""
    msg = f"Function name: {problem['entry_point']}\n\n{problem['prompt']}"
    text = generate([{"role": "user", "content": msg}], system=SYSTEM)
    code = extract_code(text)
    return [line.strip() for line in code.splitlines()
            if line.strip().startswith("assert ")]


def passes_reference(problem, assertion):
    """A correct example must pass on the correct solution."""
    program = problem["prompt"] + problem["canonical_solution"] + "\n\n" + assertion + "\n"
    return run_program(program, timeout=5)["passed"]


if __name__ == "__main__":
    problems = load_humaneval()
    visible = {}
    total = kept = 0
    no_tests = []

    for i, p in enumerate(problems):
        asserts = extract_visible_tests(p)
        good = [a for a in asserts if passes_reference(p, a)]
        dropped = len(asserts) - len(good)

        total += len(asserts)
        kept += len(good)
        if not good:
            no_tests.append(p["task_id"])
        if dropped:
            print(f"{p['task_id']}: dropped {dropped}/{len(asserts)} (disagree with reference)")
        visible[p["task_id"]] = good
        print(f"[{i+1}/{len(problems)}] {p['task_id']}: {len(good)} visible tests")

    Path("artifacts").mkdir(exist_ok=True)
    Path("artifacts/visible_tests.json").write_text(json.dumps(visible, indent=2))

    print(f"\nExtracted {total} asserts, kept {kept} ({kept/total:.1%} valid)")
    print(f"Problems with no usable visible tests: {len(no_tests)} {no_tests}")
    print("Saved to artifacts/visible_tests.json")