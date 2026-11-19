# LLM Code Generation & Repair Framework

An automated framework for measuring how often a large language model (Claude) writes correct Python code, and for testing techniques that raise that rate: multi-candidate search, iterative repair from error feedback, differential testing against reference implementations, and parallel test execution.

All results are measured on the standard **HumanEval** benchmark (and later **HumanEval+**) and recorded in [`RESULTS.md`](RESULTS.md).

---

## Research question

A single LLM sample is often wrong, but wrong in ways that can be *filtered* or *fixed*. **How much accuracy can be gained by spending more compute at test time on sampling, checking, and repairing, and is it worth the extra cost?**

### Background reading

| Paper | Why it matters here |
|---|---|
| Chen et al., 2021 — *Evaluating Large Language Models Trained on Code* (Codex) | Introduced HumanEval and the pass@k metric |
| Austin et al., 2021 — *Program Synthesis with Large Language Models* (MBPP) | Second standard benchmark |
| Li et al., 2022 — *AlphaCode* | Sample many candidates, filter by tests |
| Chen et al., 2022 — *CodeT* | Rank candidates using model-generated tests |
| Chen et al., 2023 — *Teaching LLMs to Self-Debug*; Shinn et al., 2023 — *Reflexion* | Repair loops using execution feedback |
| Olausson et al., 2023 — *Is Self-Repair a Silver Bullet for Code Generation?* | Repair vs. resampling at equal compute budget |
| Liu et al., 2023 — *EvalPlus* (HumanEval+) | Original tests are weak; differential testing exposes false passes |

---

## Pipeline

```
 HumanEval problem
        │
        ▼
 ┌──────────────┐   prompt    ┌──────────────┐
 │   data.py    │ ──────────▶ │    llm.py    │  Claude API + disk cache
 └──────────────┘             └──────┬───────┘
                                     │ code
                                     ▼
                              ┌──────────────┐
                              │  execute.py  │  sandboxed run → pass / fail + error
                              └──────┬───────┘
                                     │
                                     ▼
                           results/*.jsonl  →  RESULTS.md
```

Planned stages (see [Roadmap](#roadmap)) plug in between `llm.py` and `execute.py`: filtering, multi-candidate selection, repair, and differential testing.

---

## Project structure

```
llm-codegen-lab/
├── data.py              # Loads benchmark problems
├── execute.py           # Builds runnable programs and runs them safely
├── llm.py               # Calls Claude, caches responses, extracts code
├── verify_harness.py    # Validates the execution harness
├── run_baseline.py      # Experiment: one sample per problem → pass@1
├── show_failures.py     # Prints failed problems with errors and code
├── RESULTS.md           # Lab notebook: every experiment and its result
├── requirements.txt
├── .env                 # API key (NOT committed)
├── .gitignore
├── cache/               # Cached API responses (NOT committed)
└── results/             # Per-run outputs as JSONL (NOT committed)
```

### What each file does

**`data.py`** — `load_humaneval()` returns the 164 HumanEval problems. Each has:
- `prompt`: function signature + docstring (what the model sees)
- `canonical_solution`: reference solution (function body only)
- `test`: hidden `check(candidate)` function with assertions
- `entry_point`: the function's name

**`execute.py`** — the judge. Every reported number depends on it.
- `build_program(problem, body)`: `prompt + body + tests + check(entry_point)`, used when the completion is only a function body (e.g. the reference solutions).
- `build_program_full(problem, code)`: used when the model returns a whole function. The original prompt is kept first (some prompts define imports or helper functions); `pass` closes the empty stub, and the model's `def` redefines it.
- `run_program(program, timeout)`: runs the program and returns `{"passed": bool, "error": str}`.

Safety design for running untrusted, model-written code:

| Measure | Protects against |
|---|---|
| Separate process (`subprocess`) | Crashes, `exit()` calls taking down the harness |
| Timeout (default 10 s) | Infinite loops hanging the run |
| Temporary working directory | Generated code writing or deleting project files |
| `python -I` (isolated mode) | Access to environment variables (API key) and project imports |
| Return code check | `0` = all assertions passed; anything else = fail |

**`llm.py`** — the only file that talks to the API.
- `generate(messages, model, system, max_tokens, sample_id)`: calls Claude and caches the response on disk, keyed by a SHA-256 hash of **every setting that can change the output**. Reruns are free and reproducible. `sample_id` lets you request several distinct samples of the same prompt. `stop_reason` is recorded so truncated responses are visible.
- `extract_code(text)`: pulls code out of a ```` ```python ```` block, including an unclosed block if the response was cut off.

> Note: the current Anthropic Python SDK (2.x) does not accept a `temperature` parameter, so outputs vary between calls. The cache is what makes results reproducible; report baselines averaged over several runs.

**`verify_harness.py`** — tests the tester, in both directions:

| Check | Expected | Proves |
|---|---|---|
| Reference solutions | 164/164 pass | Harness doesn't reject correct code |
| `return None` for every problem | ~0/164 pass | Harness doesn't accept wrong code |
| `while True: pass` | timeout | Harness can't be hung |

**`run_baseline.py`** — one Claude call per problem, then run against hidden tests. Writes `results/baseline.jsonl` and prints pass@1.

**`show_failures.py`** — prints each failed task, the last line of its error, and the generated code, for error analysis.

---

## Setup

Requires Python 3.10+ and an Anthropic API key with credits.

```bash
git clone <your-repo-url> llm-codegen-lab
cd llm-codegen-lab

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt    # or: pip install datasets anthropic python-dotenv
```

Create `.env` in the project root:

```
ANTHROPIC_API_KEY=sk-ant-...
```

> Activate the virtual environment in **every new terminal** (`source .venv/bin/activate`). You should see `(.venv)` at the start of the prompt. On macOS, `python` only exists inside the venv; outside it, use `python3`.

Set a monthly spending limit in the Anthropic Console before running experiments.

---

## Usage

```bash
# 1. Validate the harness (no API calls)
python verify_harness.py

# 2. Smoke test on 5 problems
python run_baseline.py 5

# 3. Full baseline (164 problems)
python run_baseline.py

# 4. Run again: should be near-instant with an identical result (cache check)
python run_baseline.py

# 5. Inspect failures
python show_failures.py
```

After each experiment, add a row to `RESULTS.md` and commit:

```bash
git add .
git commit -m "Describe the experiment and result"
```

---

## Results so far

| Experiment | Model | Benchmark | Result | Notes |
|---|---|---|---|---|
| Harness verification | — | HumanEval | 164/164 reference pass; 0/164 dummy pass; timeout works | Instrument validated |
| Baseline (1 sample) | claude-haiku-4-5 | HumanEval | 158/164 = 96.3% | Sequential, 459 s. Included a truncation bug (see below) |
| Baseline (1 sample), bug fixed | claude-haiku-4-5 | HumanEval | _pending_ | `max_tokens` 1024 → 4096 |

### Failure analysis (first baseline)

| Category | Tasks | Plausible fix |
|---|---|---|
| Pipeline bug: response truncated at `max_tokens`, prose passed to Python | HumanEval/147 | Fixed in `llm.py` |
| Fails a **visible** docstring example | HumanEval/93, /130, /132, /145 | Multi-candidate filtering + repair |
| Hidden edge case not shown in docstring | HumanEval/76 (`is_simple_power(1, 1)`) | Hard: no signal available to the model |

### Findings

1. **Measurement bugs look like model failures.** One of six failures was caused by the pipeline, not the model. A second bug, `max_tokens` missing from the cache key, would have silently returned stale truncated answers after the fix. Rule: the cache key must include every setting that affects output.
2. **HumanEval is close to saturated.** At 96.3%, the maximum possible gain is 3.7 points, so large improvements require a stricter benchmark (HumanEval+) or a harder setting.
3. **Most real failures are detectable before submission.** 4 of 5 model failures fail an example already in the prompt, which motivates multi-candidate selection on visible tests.
4. **Sequential execution is slow.** About 2.8 s per problem, mostly waiting on the API. With multiple candidates and repair rounds this grows to hours, which motivates parallel execution.

---

## Roadmap

| Stage | Description | Status |
|---|---|---|
| A | Sandboxed execution harness, validated both ways | ✅ Done |
| B | Single-sample baseline pass@1 | ✅ Done (rerun after fix pending) |
| C | Static filter (Ruff / Mypy) + multi-candidate sampling, selection on visible docstring examples | ⬜ |
| D | Repair loop: feed failing input + traceback back to Claude, up to N rounds; compare to resampling **at equal API-call budget** | ⬜ |
| E | Differential testing: generate many inputs per problem, compare candidate output to reference output; count false passes | ⬜ |
| F | Parallel execution (`asyncio` for API, process pool for tests), rate limiting, timing before/after | ⬜ |
| G | HumanEval+ benchmark; repeat B–E; average over multiple runs | ⬜ |

### Reporting rules for this project

- Report **absolute percentage points** (e.g. 85.0% → 92.1%, +7.1 pts), not relative percentages.
- Compare techniques **at equal API-call budget**: k samples vs. 1 sample + (k−1) repairs.
- Never select candidates using hidden tests. Only the visible docstring examples may be used before submission.
- Every number in this README or on a resume must trace back to a row in `RESULTS.md` and a git commit.

---

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `zsh: command not found: python` | venv not active / wrong folder | `cd llm-codegen-lab && source .venv/bin/activate` |
| `can't open file '...py'` | File not created, or saved with a `.txt` extension | Create it in the project root; check with `ls` |
| `Messages.create() got an unexpected keyword argument 'temperature'` | SDK 2.x removed sampling parameters | Don't pass `temperature` |
| `404 not_found_error ... model:` | Retired model name | Use a current model ID, e.g. `claude-haiku-4-5-20251001` |
| `'Message' object has no attribute 'choices'` | OpenAI response format used with Anthropic | Use `resp.content[0].text` |
| `ImportError: cannot import name ...` | Part of a file was overwritten | Restore the full file |
| `HF_TOKEN` warning | Unauthenticated Hugging Face download | Harmless; ignore |