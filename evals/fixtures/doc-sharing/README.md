# doc-sharing (EVAL FIXTURE)

Authorization for a document-sharing service: who may read, comment on, edit, share, or delete a
document. `docs/policy.md` is the promise to customers; `sharing/policy.py` decides, and
`sharing/api.py` is the one path through which actions happen.

```bash
python3 -m unittest discover -s tests
```
