---
description: Run the test suite and linter
agent: build
---

Run the project checks from the repository root:

```bash
venv/bin/python -m pytest -q
venv/bin/ruff check .
```

Fix any failures, then re-run until both pass. Report the final result
(test counts and lint status).