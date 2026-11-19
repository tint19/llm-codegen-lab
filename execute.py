import os
import subprocess
import sys
import tempfile


def build_program(problem, completion):
    """prompt + model's function body + hidden tests + the call to check()."""
    return (
        problem["prompt"]
        + completion
        + "\n\n"
        + problem["test"]
        + "\n\n"
        + f"check({problem['entry_point']})\n"
    )


def run_program(program, timeout=10.0):
    """Run code in a separate, isolated Python process.

    Returns {"passed": bool, "error": str}.
    """
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "prog.py")
        with open(path, "w") as f:
            f.write(program)
        try:
            result = subprocess.run(
                [sys.executable, "-I", path],
                cwd=tmp,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return {"passed": False, "error": "timeout"}

    if result.returncode == 0:
        return {"passed": True, "error": ""}
    return {"passed": False, "error": result.stderr[-1000:]}