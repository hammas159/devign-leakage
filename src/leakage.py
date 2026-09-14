"""Measure how much of Devign's test set already appears in its training set.

Devign (via CodeXGLUE) is a standard vulnerability-detection benchmark: C functions
labelled vulnerable or not. Models are trained on the train split and scored on the
test split - which only measures generalisation if the two do not overlap.

This counts the overlap three ways, from exact copies to normalised near-duplicates,
and separates two very different consequences:

  * leakage      - the same function, same label, on both sides. The model can score
                   by memorising.
  * label noise  - the same function with *different* labels. No model can get both
                   right, so some of the benchmark is unwinnable by construction.

Deterministic: hashing and token comparison only. No model, no embeddings, no seed.
"""

from __future__ import annotations

import glob
import hashlib
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

CACHE_DIR = "datasets--google--code_x_glue_cc_defect_detection"

BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
LINE_COMMENT = re.compile(r"//[^\n]*")
STRING = re.compile(r'"(?:[^"\\]|\\.)*"')
CHAR = re.compile(r"'(?:[^'\\]|\\.)*'")
NUMBER = re.compile(r"\b\d+(?:\.\d+)?\b")
SPACE = re.compile(r"\s+")
IDENT = re.compile(r"\b[A-Za-z_]\w*\b")

# Keeping control flow and types means two functions that differ only in variable and
# function *names* still collide - which is what "near-duplicate" should mean here.
KEYWORDS = {
    "auto",
    "break",
    "case",
    "char",
    "const",
    "continue",
    "default",
    "do",
    "double",
    "else",
    "enum",
    "extern",
    "float",
    "for",
    "goto",
    "if",
    "inline",
    "int",
    "long",
    "register",
    "restrict",
    "return",
    "short",
    "signed",
    "sizeof",
    "static",
    "struct",
    "switch",
    "typedef",
    "union",
    "unsigned",
    "void",
    "volatile",
    "while",
    "NULL",
    "size_t",
    "uint8_t",
    "uint16_t",
    "uint32_t",
    "uint64_t",
    "int8_t",
    "int16_t",
    "int32_t",
    "int64_t",
    "bool",
    "true",
    "false",
}


def normalise_exact(code: str) -> str:
    """Whitespace-insensitive only. Two functions colliding here are textually the same."""
    return SPACE.sub(" ", code).strip()


def normalise_structural(code: str) -> str:
    """Strip comments, literals and identifier names; keep control flow and types.

    Two functions that collide after this differ only in naming and constants - a
    copy-paste with the variables renamed, which for a benchmark is still a duplicate.
    """
    code = BLOCK_COMMENT.sub(" ", code)
    code = LINE_COMMENT.sub(" ", code)
    code = STRING.sub('"S"', code)
    code = CHAR.sub("'C'", code)
    code = NUMBER.sub("N", code)
    code = IDENT.sub(lambda m: m.group(0) if m.group(0) in KEYWORDS else "V", code)
    return SPACE.sub(" ", code).strip()


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()


@dataclass
class Overlap:
    level: str
    test_rows: int
    train_rows: int
    matched_test_rows: int
    same_label: int
    conflicting_label: int

    @property
    def matched_share(self) -> float:
        return self.matched_test_rows / self.test_rows if self.test_rows else 0.0

    @property
    def conflict_share(self) -> float:
        return self.conflicting_label / self.test_rows if self.test_rows else 0.0


def find_parquet(split: str) -> Path | None:
    import os

    roots = []
    if env := os.environ.get("HF_HUB_CACHE"):
        roots.append(Path(env))
    if env := os.environ.get("HF_HOME"):
        roots.append(Path(env) / "hub")
    roots.append(Path.home() / ".cache" / "huggingface" / "hub")
    for root in roots:
        hits = sorted(
            glob.glob(
                str(root / CACHE_DIR / "snapshots" / "*" / "**" / f"{split}-*.parquet"),
                recursive=True,
            )
        )
        if hits:
            return Path(hits[0])
    return None


def load(split: str):
    import pandas as pd

    path = find_parquet(split)
    if path is None:
        raise FileNotFoundError(
            f"Devign '{split}' split not in the Hugging Face cache. Fetch it with:\n"
            '  python -c "from huggingface_hub import hf_hub_download as d; '
            f"d('google/code_x_glue_cc_defect_detection','data/{split}-00000-of-00001.parquet',"
            "repo_type='dataset')\""
        )
    return pd.read_parquet(path)


def compare(train, test, normalise) -> Overlap:
    """How many test rows have a train row with the same normalised body?"""
    index: dict[str, set[bool]] = defaultdict(set)
    for code, target in zip(train["func"], train["target"]):
        index[digest(normalise(code))].add(bool(target))

    matched = same = conflict = 0
    for code, target in zip(test["func"], test["target"]):
        labels = index.get(digest(normalise(code)))
        if not labels:
            continue
        matched += 1
        if bool(target) in labels:
            same += 1
        if labels - {bool(target)}:
            conflict += 1

    return Overlap(
        level=normalise.__name__.replace("normalise_", ""),
        test_rows=len(test),
        train_rows=len(train),
        matched_test_rows=matched,
        same_label=same,
        conflicting_label=conflict,
    )


def internal_duplicates(frame, normalise) -> tuple[int, int]:
    """Duplicates *within* one split, and how many of those carry conflicting labels."""
    groups: dict[str, set[bool]] = defaultdict(set)
    counts: dict[str, int] = defaultdict(int)
    for code, target in zip(frame["func"], frame["target"]):
        key = digest(normalise(code))
        groups[key].add(bool(target))
        counts[key] += 1
    duplicated = sum(c for c in counts.values() if c > 1)
    conflicting = sum(counts[k] for k, v in groups.items() if len(v) > 1)
    return duplicated, conflicting


if __name__ == "__main__":
    import sys

    a, b = (sys.argv[1], sys.argv[2]) if len(sys.argv) > 2 else ("train", "test")
    left, right = load(a), load(b)
    print(f"{a}: {len(left)} rows   {b}: {len(right)} rows\n")
    for fn in (normalise_exact, normalise_structural):
        o = compare(left, right, fn)
        print(f"[{o.level}]")
        print(f"  {b} rows also present in {a}: {o.matched_test_rows} ({o.matched_share:.2%})")
        print(f"    same label       (leakage)    : {o.same_label}")
        print(f"    different label  (label noise): {o.conflicting_label} ({o.conflict_share:.2%})")
        dup, conf = internal_duplicates(right, fn)
        print(
            f"  duplicates inside {b} itself: {dup} rows, {conf} of them with conflicting labels\n"
        )
