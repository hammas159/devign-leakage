# Method

[<- back to README](../README.md)

## Two normalisation levels

### exact

Collapse runs of whitespace to a single space and trim. Nothing else.

Two functions that collide here are **textually the same** - the only difference is
formatting.

### structural

1. Strip block comments (`/* ... */`) and line comments (`// ...`)
2. Replace string literals with `"S"` and character literals with `'C'`
3. Replace every number with `N`
4. Replace every identifier that is **not** a C keyword or standard type with `V`
5. Collapse whitespace

Two functions that collide here differ only in **naming and constants** - a copy-paste with
the variables renamed, which for a benchmark is still a duplicate.

**Control flow and types are preserved on purpose.** `if` and `while` are both keywords, so
they never collapse into each other; `int` and `char` stay distinct. Only names and values
are erased.

## Leakage versus label noise

Both are overlaps, and they are counted separately because the consequences differ:

| | Meaning | Consequence |
|---|---|---|
| **leakage** | same function, **same** label, both sides | the model can score by memorising |
| **label noise** | same function, **opposite** labels | **no model can be right on both copies** |

A single "% overlap" figure would hide that distinction entirely. The second is arguably
worse: leakage inflates a score, but conflicting labels put a ceiling on it that no amount
of model quality can lift.

## Comparison

Every function in the reference split is normalised, hashed with SHA-256, and indexed
against the set of labels it carries. Every row in the test split is then normalised,
hashed, and looked up.

A function carrying **both** labels in the reference split counts as both leakage and
noise - correctly, because one of its copies agrees with the test row and one does not.

## Duplicates within one split

The same hashing applied inside a single split. Reported separately from cross-split
overlap, because a duplicate inside test is not leakage - it is redundancy, and if the
labels disagree, it is an unwinnable pair.

## Determinism

Hashing and token substitution only. No model, no embeddings, no random seed. The same
input always produces the same counts.
