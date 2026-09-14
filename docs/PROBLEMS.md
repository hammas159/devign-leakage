# Problems hit while building this

[<- back to README](../README.md)

## 1. My prior was wrong, and the data said so

The project started from an assumption: that CodeXGLUE's defect-detection split is *known*
to be duplicate-heavy, something "everyone knows".

The measurement found 0.04% exact and 0.99% structural overlap. **That is not a
duplicate-heavy corpus.**

**What was done:** the negative result is reported as the headline rather than buried, and
the unverified claim is **not cited** anywhere - because it could not be confirmed, not
because it is necessarily false.

The more interesting finding (all four exact duplicates carrying conflicting labels) only
surfaced because the expected one did not.

## 2. The train split would not download

17.85 MB. Two attempts, both leaving **0-byte** `.incomplete` files while the connection was
saturated by another large transfer.

**What was done:** shipped the `validation` &rarr; `test` result and marked
train &rarr; test **explicitly not measured**. No estimate, no placeholder number.

The code path exists and is tested, so it is one command once the split is available.

## 3. A silent "successful" download

`hf_hub_download` exited with code 0, but no file appeared in the cache. The analysis then
failed with a confusing missing-file error several steps later.

**Fix:** verify against the cache directory rather than trusting the exit code, and make
the error message name the exact command needed to fetch the split.

## 4. The dashboard refused to start

`ui/app.py` loaded the `train` split at import time, so anyone without that 17.85 MB file
got a crash instead of a dashboard - including anyone cloning the repo.

**Fix:** train is optional. The app degrades to validation-only and shows the fetch command,
rather than refusing to run.

## 5. CI cache misconfigured

`setup-uv` errors outright when its default `**/uv.lock` glob matches nothing.

**Fix:** keyed the cache on `pyproject.toml`.
