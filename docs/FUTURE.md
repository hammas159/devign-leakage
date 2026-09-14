# Future work

[<- back to README](../README.md)

## 1. Measure train -> test

The comparison that matters, and the one thing this repository is missing. The code path
exists and is tested; it needs the 17.85 MB split.

```bash
python src/leakage.py train test
```

## 2. Near-duplicate detection beyond exact-match

MinHash/LSH or token-level edit distance would catch functions differing by a single
statement - currently invisible at both levels. That would turn the structural number from a
coarse upper bound into a real estimate.

## 3. Use `project` and `commit_id`

Both are in the dataset and unused. They would corroborate matches and show whether
duplicates cluster in particular upstream projects - which would say something about how the
dataset was assembled.

## 4. Quantify the ceiling explicitly

Conflicting labels cap achievable accuracy below 100%. Computing that bound and comparing it
against published Devign scores would show whether any reported result is close enough to it
to matter.

## 5. Re-score a published model on a cleaned split

De-duplicate, remove conflicting pairs, re-run a published model. If the score does not
move, that is a stronger validation of the benchmark than this analysis alone - and if it
does, that is a stronger finding.

## 6. Apply the same analysis to other CodeXGLUE tasks

Clone detection especially, where duplication is structural to the task and the definition
of "leakage" is correspondingly subtler.
