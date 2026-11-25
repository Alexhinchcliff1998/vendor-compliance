# VendorGuard | Compliance Workflow

SQLite-backed fictional vendor compliance register for evidence expirations, corrective actions and hash-chained audit history. Risk rules are illustrative, not official regulations. The hash chain detects casual changes, not an administrator rewriting the entire history.

```bash
pip install -r requirements.txt
python compliance.py demo --as-of 2025-11-01
python -m pytest -q
python compliance.py --help
```
Independent AI-assisted demonstration. Never use actual vendor data in public repositories.
