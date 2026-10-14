"""Regression checks for additive single-lab search appendix tables."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

import publish_single_lab_search as publication


class SearchPublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot = publication.read(publication.OUT / "snapshot.json")
        cls.tables = publication.render(cls.snapshot)

    def reject_change(self, change):
        altered = deepcopy(self.snapshot)
        change(altered)
        with self.assertRaises((ValueError, KeyError)):
            publication.validate(altered)

    def test_complete_counts(self):
        publication.validate(self.snapshot)
        self.assertEqual(len(self.snapshot["training_audits"]), 15)
        self.assertEqual(sum(x["full100_candidates"] for x in self.snapshot["training_audits"].values()), 180)

    def test_counts_not_inferred_from_complete_status(self):
        self.reject_change(lambda x: x["training_cost"].update(verified_full100_candidates=179))

    def test_missing_fit_rejected(self):
        self.reject_change(lambda x: x["training_audits"]["native_tapb/seed42"]["receipt_sha256"].pop("D11"))

    def test_missing_seed_rejected(self):
        self.reject_change(lambda x: x["rows"]["native_tapb"]["fixed"]["values"].pop("44"))

    def test_corrupt_mean_rejected(self):
        self.reject_change(lambda x: x["rows"]["native_tapb"]["fixed"].update(mean=.99))

    def test_population_sd_rejected(self):
        self.reject_change(lambda x: x["rows"]["native_tapb"]["fixed"].update(sd=.009921))

    def test_lab_scope_rejected(self):
        self.reject_change(lambda x: x["protocol"].update(search_clients=list(range(10))))

    def test_exact_random_protocol_rejected(self):
        self.reject_change(lambda x: x["search_runs"]["native_tapb/seed42"]["exact_random_6"].update(subset_count=461))

    def test_absolute_host_path_rejected(self):
        self.reject_change(lambda x: x["protocol"].update(source="/some/server/private"))

    def test_all_methods_are_retained(self):
        for method in publication.METHODS:
            self.assertIn(publication.LABELS[method], self.tables["comparison.tex"])
        self.assertIn(r"\mathbf{25.56}", self.tables["comparison.tex"])
        self.assertIn("22.25", self.tables["comparison.tex"])

    def test_best_rounding_ties(self):
        self.assertIn(r"\mathbf{90.10}", publication.cell(dict(mean=.90101, sd=.01), "90.10"))
        self.assertNotIn(r"\mathbf", publication.cell(dict(mean=.899, sd=.01), "90.10"))

    def test_explicit_reference_and_budget_semantics(self):
        table = self.tables["comparison.tex"]
        for text in ("Qwen2.5-7B-Instruct", "history-enabled", "lab~0", "one or ten laboratories"):
            self.assertIn(text, table)
        self.assertNotIn("Direct", table)
        self.assertIn("not their predictions", self.tables["search_expectation.tex"])
        self.assertEqual(self.snapshot["protocol"]["nominal_candidate_rounds"]["bayes_6"], 700)
        self.assertEqual(self.snapshot["protocol"]["nominal_candidate_rounds"]["exhaustive_12"], 1200)

    def test_native_width_no_image_or_resize(self):
        for table in self.tables.values():
            self.assertIn(r"\begin{table}[!ht]", table)
            self.assertIn(r"\begin{tabular*}{\textwidth}", table)
            for forbidden in (r"\resizebox", r"\tiny", r"\includegraphics", "SOTA", "significantly"):
                self.assertNotIn(forbidden, table)

    def test_tables_regenerate_identically(self):
        for name, content in self.tables.items():
            self.assertEqual((publication.OUT / name).read_text(encoding="utf-8"), content)

    def test_snapshot_is_aggregate_only(self):
        encoded = json.dumps(self.snapshot)
        for forbidden in ("/liziqing/", '"cluster_sizes":', '"compound_key":', '"probability":', '"Protein":', '"SMILES":'):
            self.assertNotIn(forbidden, encoded)

    def test_provenance_integrity(self):
        provenance = publication.read(publication.OUT / "provenance.json")
        self.assertEqual(provenance["snapshot_sha256"], publication.sha(publication.OUT / "snapshot.json"))
        self.assertGreater(len(provenance["source_artifacts_sha256"]), 100)
        for path, digest in provenance["source_artifacts_sha256"].items():
            self.assertFalse(Path(path).is_absolute())
            self.assertEqual(len(digest), 64)


if __name__ == "__main__":
    unittest.main()
