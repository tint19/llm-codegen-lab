from datasets import load_dataset


def load_humaneval():
    """Return the 164 HumanEval problems as a list of dicts."""
    return list(load_dataset("openai/openai_humaneval", split="test"))