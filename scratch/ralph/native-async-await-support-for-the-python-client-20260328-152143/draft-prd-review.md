# Draft PRD Review: Native Async/Await Support for the Python Client

## Task 1.1: Add AsyncCopilotClient class with async request primitives

- ISSUE: The `Run:` command is `pytest tests/test_client.py -v`, but `tests/test_client.py` contains zero async tests and has no knowledge of `AsyncCopilotClient`. Running it will only confirm existing sync tests still pass — it provides no verification that the new class actually works.
- FIX: Change `Run:` to `python -c "import asyncio; from copilot_proxy import AsyncCopilotClient; print('Import OK')"` (a smoke-import check), or acknowledge that full verification happens in task 2.2. Alternatively, add a note that tests/test_async_client.py won't exist until task 2.2, so this command is intentionally just a regression guard for sync tests.

- ISSUE: Description says "Add the TYPE_CHECKING-gated import for AsyncIterator from collections.abc". The file already has `from __future__ import annotations` at line 3, which means all annotations are treated as strings and no runtime import is needed. A `TYPE_CHECKING` guard is therefore optional/cosmetic, not required for correctness. The description should not imply this import is mandatory.
- FIX: Change wording to: "Add `from collections.abc import AsyncIterator` under `if TYPE_CHECKING:` as a best-practice annotation guard, or rely on the existing `from __future__ import annotations` — both are acceptable on Python 3.10+."

## Task 1.2: Implement async def chat() with non-streaming and async streaming support

- ISSUE: `Run: pytest tests/test_async_client.py -v` references a file that does not exist yet and won't be created until task 2.2 (which depends on 2.1 → 1.3 → **1.2**). Running this command at the end of task 1.2 will fail with `ERROR: not found: tests/test_async_client.py`.
- FIX: Change `Run:` to `python -c "import asyncio; from copilot_proxy.client import AsyncCopilotClient; print('AsyncCopilotClient OK')"` as a smoke-import check, or add a note that full test coverage is delivered by task 2.2.

## Task 1.3: Add module-level async convenience functions and export from __init__.py

- ISSUE: The acceptance criteria includes `"__version__ is updated to 0.3.0 in both __init__.py and pyproject.toml"`, but `pyproject.toml` is not listed in the `files` array. The version in `pyproject.toml` (currently `version = "0.2.0"` at line 3) must be kept in sync with `__init__.py`, so the implementer needs to edit it.
- FIX: Add `"pyproject.toml"` to the `files` array for task 1.3.

- ISSUE: `Run: pytest tests/test_client.py tests/test_async_client.py -v` — `tests/test_async_client.py` still does not exist at this stage (same issue as 1.2). The command will abort with a collection error.
- FIX: Change `Run:` to `pytest tests/test_client.py -v` only (the file that actually exists), or add `--ignore-glob='*async*'` fallback. The full two-file run belongs in task 2.2+.

## Task 2.1: Add pytest-asyncio dev dependency and configure asyncio test mode

- ISSUE: None identified. File path `pyproject.toml` is correct and exists. The `[tool.pytest.ini_options]` section already exists (line 37-38) with `testpaths = ["tests"]`; the task correctly enhances it. Description is well over 300 chars. `Run:` command is valid.
- OK (minor note): Task correctly targets an existing file for enhancement, not creation.

## Task 2.2: Write comprehensive async unit tests in tests/test_async_client.py

- ISSUE: The acceptance criteria state "The mock_server fixture is shared via conftest.py so both test files can use it without duplication." Moving `mock_server` (and the `MockProxyHandler` / `MOCK_MODELS` it depends on) to `tests/conftest.py` requires **removing** those definitions from `tests/test_client.py`. However, `tests/test_client.py` is not listed in the `files` array, so the implementer may not realise they need to modify it.
- FIX: Add `"tests/test_client.py"` to the `files` array for task 2.2, with a note that the `mock_server` fixture and its supporting code must be moved out of `test_client.py` into `conftest.py` and the import removed/replaced.

- ISSUE: `tests/conftest.py` does not currently exist; the task correctly lists it as a file to create. No path issue here, but the task description says "import it from test_client **or** refactor it into a conftest.py." The acceptance criteria then mandates conftest.py. The description should not leave the "import from test_client" option open since it would not satisfy the acceptance criterion.
- FIX: Remove the "import it from test_client" option from the description; state only "move the fixture to tests/conftest.py."

## Task 3.1: Add async usage section to README.md

- OK. `README.md` exists at the repo root. The target anchor section `### Python Client (zero dependencies)` exists at line 66, so inserting immediately after it is unambiguous. Description is well over 300 chars. `Run:` command (`python -m doctest README.md --option ELLIPSIS || true`) is valid (the `|| true` correctly tolerates doctest failures from live-network examples). Dependencies `["1.3"]` are correct.

## Task 3.2: Add examples/async_usage.py with runnable async examples

- OK. `examples/` directory exists; `examples/async_usage.py` does not yet exist, so this is a correct create operation. Description is well over 300 chars. `Run:` command (ast.parse syntax check) is valid and correct. Dependencies `["3.1"]` are correct.
