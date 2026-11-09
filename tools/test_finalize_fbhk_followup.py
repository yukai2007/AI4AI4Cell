"""Regression tests for complete rows, controls and the actual main-text end."""
from pathlib import Path
import unittest

import fitz

from finalize_fbhk_followup import (PAPER, POLICY_LABELS, NEW_TABLES, main_text_bounds, verify_log,
    verify_merged_rows, verify_control_rows, verify_compiled_labels, verify_lab_summary, load)


def make_document(conclusion_page, repro_page, continuation_page=None):
    doc = fitz.open()
    for i in range(repro_page):
        page = doc.new_page()
        page.insert_text((70,30), "Under review as a conference paper at ICLR 2027")
        page.insert_text((300,820), str(i+1))
        if i+1 < conclusion_page:
            page.insert_text((100,90), "Main scientific content.")
        if i+1 == conclusion_page:
            page.insert_text((100,90), "5. CONCLUSION")
            page.insert_text((100,110), "Conclusion starts here.")
        if i+1 == continuation_page:
            page.insert_text((100,90), "The conclusion continues onto this page.")
        if i+1 == repro_page:
            page.insert_text((100,200 if i+1 == continuation_page or i+1 == conclusion_page else 70),
                             "REPRODUCIBILITY STATEMENT")
    return doc


class FinalizerTests(unittest.TestCase):
    def test_conclusion_continuation_counts(self):
        with make_document(9,10,10) as doc:
            result = main_text_bounds(doc)
            self.assertEqual(result["conclusion_heading_page"],9)
            self.assertEqual(result["main_text_ends_page"],10)

    def test_continuation_past_limit_fails(self):
        with make_document(10,11,11) as doc:
            with self.assertRaisesRegex(ValueError,"continues to page 11"):
                main_text_bounds(doc)

    def test_repro_new_page_does_not_count_running_header(self):
        with make_document(10,11) as doc:
            self.assertEqual(main_text_bounds(doc)["main_text_ends_page"],10)

    def test_logs_reject_reference_and_layout_errors(self):
        for text in ("Overfull \\hbox", "Reference x undefined", "Missing character", "! Undefined control sequence", "Label x multiply defined"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                verify_log(text)
        verify_log("Underfull \\hbox\nOutput written on main.pdf")

    def test_all_controls_required_even_if_stronger(self):
        table = "\n".join(name + " & 1 & 2 \\\\" for name in POLICY_LABELS)
        verify_control_rows(table)
        with self.assertRaises(ValueError):
            verify_control_rows(table.replace("GP--EI", "Removed"))
        with self.assertRaises(ValueError):
            verify_control_rows(table + "\nRaw history & 1 & 2 \\\\")

    def original_rows(self):
        old = PAPER / "tables/completed_ablation"
        return [(old / name).read_text() for name in ("short6.tex", "long24.tex", "dynamics_short6.tex", "dynamics_long24.tex")]

    def merged_rows(self):
        new = PAPER / "tables/fbhk_followup_20261109"
        return [(new / name).read_text() for name in ("proposal_heldout_combined.tex", "proposal_dynamics_combined.tex")]

    def test_all_18_plus_18_rows_survive(self):
        result = verify_merged_rows(*self.original_rows(), *self.merged_rows())
        self.assertEqual(result, {"original_score_rows_retained":18,"original_dynamics_rows_retained":18})

    def test_negative_heldout_row_cannot_be_dropped(self):
        scores,dynamics = self.merged_rows()
        lines = scores.splitlines()
        damaged = "\n".join(line for line in lines if not (line.startswith("VCC & Qwen") and "19.61" in line))
        with self.assertRaises(ValueError):
            verify_merged_rows(*self.original_rows(),damaged,dynamics)

    def test_slow_history_dynamics_cannot_be_hidden(self):
        scores,dynamics = self.merged_rows()
        damaged = dynamics.replace("5/13", "5/5")
        with self.assertRaises(ValueError):
            verify_merged_rows(*self.original_rows(),scores,damaged)

    def test_original_datum_cannot_be_edited(self):
        scores,dynamics = self.merged_rows()
        with self.assertRaises(ValueError):
            verify_merged_rows(*self.original_rows(),scores.replace("13.43","26.87"),dynamics)

    def test_compiled_labels_require_new_tables_and_figure(self):
        labels = set().union(*NEW_TABLES.values()) | {"fig:fbhk-prefix"}
        aux = "\n".join("\\newlabel{" + label + "}{{E.1}{34}}" for label in labels)
        verify_compiled_labels(aux)
        with self.assertRaises(ValueError):
            verify_compiled_labels(aux.replace("fig:fbhk-prefix","fig:wrong"))
        with self.assertRaises(ValueError):
            verify_compiled_labels(aux + "\n\\newlabel{fig:fbhk-prefix}{{1}{40}}")

    def test_all_laboratory_outcomes_required(self):
        root = PAPER / "tables/fbhk_followup_20261109"
        report = load(root / "lab_identity.json")
        checks = load(root / "lab_identity.provenance.json")["checks"]
        verify_lab_summary(report, checks)
        with self.assertRaises(ValueError):
            verify_lab_summary(report, checks[:-1])
        report["rows"][0]["mean"] += 1
        with self.assertRaises(ValueError):
            verify_lab_summary(report,checks)


if __name__ == "__main__":
    unittest.main()
