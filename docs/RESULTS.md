# Results

[<- back to README](../README.md)

`google/code_x_glue_cc_defect_detection` - test and validation splits, 2,732 rows each.
Test labels: 1,477 not-vulnerable / 1,255 vulnerable.

**train &rarr; test is not measured.** See [LIMITATIONS.md](LIMITATIONS.md).

## Cross-split overlap: validation -> test

| | exact | structural |
|---|---:|---:|
| test rows also present in validation | **1 (0.04%)** | **27 (0.99%)** |
| ...with the same label (leakage) | 0 | 22 |
| ...with the opposite label (noise) | 1 (0.04%) | 5 (0.18%) |

## Duplicates within a single split

| Split | Level | duplicate rows | with conflicting labels |
|---|---|---:|---:|
| test | exact | 4 (0.15%) | **4 (0.15%) - all of them** |
| test | structural | 31 (1.13%) | 12 (0.44%) |
| validation | exact | 0 | 0 |
| validation | structural | 47 (1.72%) | 13 (0.48%) |

## Reading these numbers

### The negative result

Cross-split overlap is **low**. At 0.04% exact and 0.99% structural, reported Devign scores
are not obviously inflated by copying between validation and test.

This contradicts the assumption the project started from - that CodeXGLUE's defect split is
known to be duplicate-heavy. **That claim could not be verified**, and nothing measured here
supports it at these thresholds, so it is not cited anywhere in this repository.

### The positive one

**All four exact duplicate pairs inside the test split carry opposite labels.** The same C
function appears twice, marked vulnerable once and not-vulnerable once. Whatever a model
predicts, it is scored wrong on one copy of each pair.

The same holds for 12 of the 31 structural duplicates in test, and for 13 duplicate rows in
validation.

The practical consequence is a small **ceiling below 100%** that no model can cross, and
which nothing in the benchmark's reporting mentions. It is small - well under 1% - but it is
a property of the dataset, not of any model evaluated on it.

## Raw output

`results/leakage.json` holds every count above, plus the label distribution per split.

## Reproducing

```bash
python src/leakage.py validation test
streamlit run ui/app.py
```
