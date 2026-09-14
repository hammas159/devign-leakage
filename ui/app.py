"""How much of Devign's test set is already in its training set?

Everything is computed live from the cached parquet files by the same functions the
CLI uses. Change the normalisation level and the overlap is recounted - no
precomputed results.

Run:  streamlit run ui/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from leakage import (
    compare,
    digest,
    internal_duplicates,
    load,
    normalise_exact,
    normalise_structural,
)

st.set_page_config(page_title="devign leakage", layout="wide")

RED, AMBER, BLUE, GREEN = "#dc2626", "#f59e0b", "#2563eb", "#16a34a"
LEVELS = {
    "exact (whitespace-insensitive)": normalise_exact,
    "structural (identifiers renamed)": normalise_structural,
}

st.title("Is the test set already in the training set?")
st.caption(
    "Devign is a standard vulnerability-detection benchmark: C functions labelled "
    "vulnerable or not. A test score only measures generalisation if the two splits do "
    "not overlap. This counts the overlap, and separates **leakage** (same function, "
    "same label - memorisable) from **label noise** (same function, *different* labels "
    "- unwinnable by construction)."
)


@st.cache_data(show_spinner="Loading splits...")
def get(split: str):
    return load(split)


try:
    test, validation = get("test"), get("validation")
except FileNotFoundError as exc:
    st.error(str(exc))
    st.stop()

# train is optional: it is 17.85 MB and may not be cached. The validation->test
# comparison is still meaningful on its own (selecting a model on validation leaks into
# test), so the app must work without it rather than refuse to start.
try:
    train = get("train")
except FileNotFoundError:
    train = None

choices = ["validation"] if train is None else ["train", "validation"]
if train is None:
    st.info(
        "The **train** split is not in the local cache, so the train -> test comparison "
        "is unavailable and only validation -> test is shown. Fetch it with:\n\n"
        '```\npython -c "from huggingface_hub import hf_hub_download as d; '
        "d('google/code_x_glue_cc_defect_detection',"
        "'data/train-00000-of-00001.parquet',repo_type='dataset')\"\n```"
    )
left_name = st.selectbox("Compare against", choices, index=0)
reference = train if left_name == "train" else validation


@st.cache_data(show_spinner="Hashing...")
def overlap(level: str, ref_name: str):
    fn = LEVELS[level]
    ref = train if ref_name == "train" else validation
    o = compare(ref, test, fn)
    dup, conflict = internal_duplicates(test, fn)
    return o, dup, conflict


rows = []
for level in LEVELS:
    o, dup, conflict = overlap(level, left_name)
    rows.append(
        {
            "level": level.split(" ")[0],
            "matched": o.matched_test_rows,
            "matched_share": o.matched_share,
            "leakage (same label)": o.same_label,
            "label noise (conflicting)": o.conflicting_label,
            "dupes inside test": dup,
            "of those, conflicting": conflict,
        }
    )
frame = pd.DataFrame(rows)

a, b, c, d = st.columns(4)
a.metric(f"{left_name} rows", f"{len(reference):,}")
b.metric("test rows", f"{len(test):,}")
c.metric("overlap (exact)", f"{frame.iloc[0]['matched_share']:.2%}")
d.metric("overlap (structural)", f"{frame.iloc[1]['matched_share']:.2%}")

worst = frame["matched_share"].max()
if worst > 0.05:
    st.error(
        f"**{worst:.1%} of the test split also appears in {left_name}.** A model can "
        "score on those by memorising."
    )
else:
    st.success(
        f"Cross-split overlap is small — at most {worst:.2%} of test rows appear in "
        f"{left_name}. On this evidence the split is cleaner than a duplicate-heavy "
        "corpus would suggest, and reported scores are not obviously inflated by "
        "train/test copying."
    )

conflicting_inside = int(frame["of those, conflicting"].max())
if conflicting_inside:
    st.warning(
        f"**{conflicting_inside} rows inside the test split are duplicates carrying "
        "conflicting labels** — the same function marked both vulnerable and not. No "
        "model can be right on both copies, so that fraction of the benchmark is "
        "unwinnable by construction, independent of any leakage."
    )

st.subheader("Counts by normalisation level")
st.dataframe(frame, hide_index=True, width="stretch")
st.caption(
    "**exact** collapses whitespace only. **structural** also strips comments and "
    "literals and renames every identifier, so a copy-paste with the variables renamed "
    "still collides."
)

melted = frame.melt(
    id_vars="level",
    value_vars=["leakage (same label)", "label noise (conflicting)"],
    var_name="kind",
    value_name="rows",
)
chart = (
    alt.Chart(melted)
    .mark_bar()
    .encode(
        x=alt.X("level:N", title=None),
        y=alt.Y("rows:Q", title="test rows"),
        color=alt.Color(
            "kind:N",
            scale=alt.Scale(
                domain=["leakage (same label)", "label noise (conflicting)"], range=[AMBER, RED]
            ),
            legend=alt.Legend(orient="top", title=None),
        ),
        tooltip=["level", "kind", "rows"],
    )
    .properties(height=320)
)
st.altair_chart(chart, width="stretch")

# --- inspect ---------------------------------------------------------------------------

st.subheader("Look at an overlapping pair")
level = st.selectbox("Normalisation", list(LEVELS))
fn = LEVELS[level]


@st.cache_data(show_spinner="Finding pairs...")
def pairs(level_name: str, ref_name: str):
    f = LEVELS[level_name]
    ref = train if ref_name == "train" else validation
    index: dict[str, list[int]] = {}
    for i, code in enumerate(ref["func"]):
        index.setdefault(digest(f(code)), []).append(i)
    out = []
    for j, (code, target) in enumerate(zip(test["func"], test["target"])):
        hit = index.get(digest(f(code)))
        if hit:
            out.append((j, hit[0], bool(target), bool(ref["target"].iloc[hit[0]])))
    return out


found = pairs(level, left_name)
st.write(f"**{len(found)}** overlapping pairs at this level.")

if found:
    idx = st.selectbox(
        "Pair",
        range(len(found)),
        format_func=lambda i: (
            f"test#{found[i][0]} ({'vuln' if found[i][2] else 'clean'})  vs  "
            f"{left_name}#{found[i][1]} ({'vuln' if found[i][3] else 'clean'})"
            + ("   <-- CONFLICTING" if found[i][2] != found[i][3] else "")
        ),
    )
    ti, ri, tl, rl = found[idx]
    if tl != rl:
        st.error("Same function, opposite labels. One of these two rows must be wrong.")
    x, y = st.columns(2)
    x.markdown(f"**test row {ti}** — label `{'vulnerable' if tl else 'not vulnerable'}`")
    x.code(test["func"].iloc[ti][:2500], language="c")
    y.markdown(f"**{left_name} row {ri}** — label `{'vulnerable' if rl else 'not vulnerable'}`")
    y.code(reference["func"].iloc[ri][:2500], language="c")

st.divider()
st.caption(
    "Data: `google/code_x_glue_cc_defect_detection` (Devign). Comparison is hashing and "
    "token substitution only — deterministic, no model, no embeddings, no seed."
)
