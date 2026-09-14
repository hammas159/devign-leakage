# Limitations

[<- back to README](../README.md)

## train -> test is not measured

**The most important limitation.** The headline comparison for any leakage analysis is
train against test, and this repository does not contain it: the 17.85 MB train split would
not download.

Everything reported is `validation` &harr; `test`. That still matters - selecting a model on
validation leaks into test - but it is the weaker of the two questions.

## The structural count is inflated by design

Structural normalisation renames **every** identifier. Two genuinely different functions
with identical control flow and types will collide - for example two short getters that
differ only in which field they return.

That is why exact and structural are **always reported separately** and never blended into
one "overlap" figure. The exact count is a floor; the structural count is a generous upper
bound.

## Exact-match on a normal form, not similarity search

Two functions differing by a single statement are not detected at either level. Real
near-duplicates in the middle of that range are invisible here, so the true overlap is
somewhere above the structural number.

## Only `func` and `target` are used

The dataset also carries `project` and `commit_id`, which could corroborate a match or
reveal that duplicates cluster in particular upstream projects. Neither is used.

## The ceiling is small

The conflicting-label finding is real but modest: four exact rows out of 2,732. It puts a
ceiling below 100% on the benchmark, but not one that changes how a published result should
be read. It is a dataset-quality observation, not a refutation.

## One dataset, one task

Nothing here says whether other CodeXGLUE tasks have the same property. Clone detection in
particular would be worth checking, since duplication is structural to that task.
