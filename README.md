# devign-leakage

**Devign's cross-split leakage is smaller than commonly assumed — but every exact
duplicate inside its test set is labelled inconsistently.**

Devign (via CodeXGLUE) is a standard vulnerability-detection benchmark: C functions
labelled vulnerable or not. A test score only measures generalisation if the splits do
not overlap, and only means anything if the labels are self-consistent.

This measures both, and keeps them apart, because they have different consequences:

- **leakage** — the same function, same label, on both sides. A model can score by
  memorising.
- **label noise** — the same function with *opposite* labels. No model can be right on
  both copies, so that slice of the benchmark is **unwinnable by construction**.

---

## Measured result

`validation` → `test`, 2,732 rows each:

| | exact | structural |
|---|---|---|
| test rows also in validation | **1 (0.04%)** | **27 (0.99%)** |
| …same label (leakage) | 0 | 22 |
| …opposite label (noise) | 1 | 5 |

Duplicates *within* a single split:

| Split | level | duplicate rows | with conflicting labels |
|---|---|---|---|
| test | exact | 4 (0.15%) | **4 — all of them** |
| test | structural | 31 (1.13%) | 12 (0.44%) |
| validation | exact | 0 | 0 |
| validation | structural | 47 (1.72%) | 13 (0.48%) |

### The finding

**Cross-split overlap is low.** At 0.04% exact and 0.99% structural, reported Devign
scores are not obviously inflated by train/test copying. That is a negative result, and
it runs against the assumption this repo started from.

**But the duplicates that do exist are labelled inconsistently.** Every one of the four
exact duplicate pairs inside the test split carries opposite labels. Whatever a model
predicts, it is scored wrong on one copy of each pair. The same holds for 12 of the 31
structural duplicates, and for 13 duplicate rows inside validation.

The practical consequence is a small ceiling below 100% that no model can cross, and
which nothing in the benchmark's reporting mentions.

---

## ⚠️ Incomplete: train → test is not measured here

The comparison that matters most — **train → test** — is **not in this README.** The
train split (17.85 MB) would not download: two attempts produced 0-byte files while the
connection was saturated by another transfer.

The code path exists and is tested. Once the split is available:

```bash
python src/leakage.py train test
```

Treat the numbers above as `validation`↔`test` only. Validation overlap still matters —
model selection on validation leaks into test — but it is the weaker of the two
questions, and this repo does not yet answer the stronger one.

I also could not verify the claim, which I had assumed going in, that CodeXGLUE's
defect-detection split is *known* to be duplicate-heavy. Nothing in what I measured
supports it at these thresholds. It is not cited here because I did not confirm it.

---

## How the comparison works

**exact** — collapse whitespace. A collision means the two functions are textually the
same.

**structural** — strip comments and literals, normalise numbers, and rename every
identifier that is not a C keyword or standard type. A collision means the two differ
only in naming and constants: a copy-paste with the variables renamed, which for a
benchmark is still a duplicate. Control flow and types are preserved, so `if` and
`while` never collapse into each other.

Hashing and token substitution only — deterministic, no model, no embeddings, no seed.

## Run it

```bash
python src/leakage.py validation test   # the numbers above
python src/leakage.py train test        # once the train split is available
streamlit run ui/app.py                 # inspect overlapping pairs side by side
pytest -q                               # 19 tests, no dataset, no network
```

The dashboard shows each overlapping pair as two code panes with their labels, and
flags the conflicting ones — those are worth looking at directly.

## Limitations

- **Structural normalisation is deliberately aggressive.** Two genuinely different
  functions with identical control flow and types will collide. That inflates the
  structural count relative to what a human would call a duplicate, which is why exact
  and structural are always reported separately rather than blended.
- **Duplicate detection is exact-match on a normal form**, not similarity search. Two
  functions differing by one statement are not detected at either level.
- **Only `func` and `target` are compared.** `project` and `commit_id` are not used to
  corroborate a match.

## Data

`google/code_x_glue_cc_defect_detection` — test and validation splits (2.1 MB each)
from the local Hugging Face cache. Test labels: 1,477 not-vulnerable / 1,255 vulnerable.

## Layout

```
src/leakage.py    normalisation, hashing, overlap and duplicate counting
ui/app.py         Streamlit: counts, charts, side-by-side pair inspection
tests/            19 tests on hand-written C - no dataset needed
results/          measured output
```
