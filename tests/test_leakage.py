"""Tests for the normalisation and overlap counting.

Every case is hand-written C, so the suite runs without the dataset and without the
network - a Hugging Face outage must not look like a code failure.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from leakage import (
    compare,
    digest,
    internal_duplicates,
    normalise_exact,
    normalise_structural,
)

A = "int add(int a, int b) {\n    return a + b;\n}"
A_SPACED = "int   add(int a,  int b)   {\n\n  return a + b;\n}"
A_RENAMED = "int sum(int x, int y) {\n    return x + y;\n}"
A_COMMENTED = "/* adds */\nint add(int a, int b) {\n    // sum\n    return a + b;\n}"
B = "void wipe(char *p, size_t n) {\n    memset(p, 0, n);\n}"


def frame(*rows):
    return pd.DataFrame([{"func": f, "target": t} for f, t in rows])


# --- exact normalisation ----------------------------------------------------------------


def test_exact_ignores_whitespace():
    assert normalise_exact(A) == normalise_exact(A_SPACED)


def test_exact_distinguishes_renamed_identifiers():
    assert normalise_exact(A) != normalise_exact(A_RENAMED)


def test_exact_distinguishes_different_functions():
    assert normalise_exact(A) != normalise_exact(B)


# --- structural normalisation -------------------------------------------------------------


def test_structural_collapses_renamed_identifiers():
    """A copy-paste with the variables renamed is still a duplicate for a benchmark."""
    assert normalise_structural(A) == normalise_structural(A_RENAMED)


def test_structural_ignores_comments():
    assert normalise_structural(A) == normalise_structural(A_COMMENTED)


def test_structural_still_separates_different_logic():
    assert normalise_structural(A) != normalise_structural(B)


def test_structural_keeps_control_flow():
    """`if` and `while` must not be collapsed into each other."""
    x = normalise_structural("void f(void) { if (a) g(); }")
    y = normalise_structural("void f(void) { while (a) g(); }")
    assert x != y


def test_structural_normalises_literals():
    x = normalise_structural('void f(void) { log("hello"); }')
    y = normalise_structural('void f(void) { log("goodbye"); }')
    assert x == y


def test_structural_normalises_numbers():
    assert normalise_structural("int f(void){return 1;}") == normalise_structural(
        "int f(void){return 99;}"
    )


def test_digest_is_stable():
    assert digest("abc") == digest("abc")
    assert digest("abc") != digest("abd")


# --- overlap counting -----------------------------------------------------------------------


def test_no_overlap_is_reported_as_none():
    o = compare(frame((A, True)), frame((B, False)), normalise_exact)
    assert o.matched_test_rows == 0
    assert o.matched_share == 0.0


def test_same_function_same_label_counts_as_leakage():
    o = compare(frame((A, True)), frame((A, True)), normalise_exact)
    assert o.matched_test_rows == 1
    assert o.same_label == 1
    assert o.conflicting_label == 0


def test_same_function_different_label_counts_as_noise():
    """Unwinnable by construction: no model can be right on both copies."""
    o = compare(frame((A, True)), frame((A, False)), normalise_exact)
    assert o.matched_test_rows == 1
    assert o.same_label == 0
    assert o.conflicting_label == 1


def test_a_function_carrying_both_labels_in_train_counts_as_both():
    o = compare(frame((A, True), (A, False)), frame((A, True)), normalise_exact)
    assert o.same_label == 1
    assert o.conflicting_label == 1


def test_renamed_copy_is_missed_by_exact_and_caught_by_structural():
    train, test = frame((A, True)), frame((A_RENAMED, True))
    assert compare(train, test, normalise_exact).matched_test_rows == 0
    assert compare(train, test, normalise_structural).matched_test_rows == 1


def test_matched_share_is_a_fraction_of_the_test_split():
    o = compare(frame((A, True)), frame((A, True), (B, False)), normalise_exact)
    assert o.matched_test_rows == 1
    assert o.matched_share == pytest.approx(0.5)


# --- duplicates inside one split -----------------------------------------------------------


def test_internal_duplicates_counts_repeated_rows():
    dup, conflict = internal_duplicates(frame((A, True), (A, True), (B, False)), normalise_exact)
    assert dup == 2
    assert conflict == 0


def test_internal_duplicates_flags_conflicting_labels():
    dup, conflict = internal_duplicates(frame((A, True), (A, False)), normalise_exact)
    assert dup == 2
    assert conflict == 2


def test_unique_rows_produce_no_duplicates():
    dup, conflict = internal_duplicates(frame((A, True), (B, False)), normalise_exact)
    assert dup == 0
    assert conflict == 0
