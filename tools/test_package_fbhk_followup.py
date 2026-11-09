"""Check public-only aggregation and reproducible source packaging."""
import io
import json
import unittest
import zipfile

import package_fbhk_followup as package


class PackageTest(unittest.TestCase):
    def test_individual_fields_removed_without_changing_aggregates(self):
        value = {"retained_genes": 406, "excluded_condition_ids": ["private-A"],
                 "nested": {"per_gene": {"private-B": 0.1}}, "seeds": [61, 62, 63]}
        cleaned, omitted = package.sanitize_protocol(value)
        self.assertEqual(cleaned, {"retained_genes": 406, "nested": {}, "seeds": [61, 62, 63]})
        self.assertEqual(omitted, ["/excluded_condition_ids", "/nested/per_gene"])

    def test_policy_summary_has_no_individual_gene_records(self):
        summary = package.policy_summary()
        self.assertEqual(summary["training_controller_seeds"], [61, 62, 63])
        self.assertEqual(summary["candidate_proposal_budget"], 6)
        for policy in summary["policies"].values():
            self.assertEqual(len(policy["per_seed"]), 3)
            for row in policy["per_seed"]:
                self.assertEqual(set(row), {"seed", "heldout_primary"})
        source = json.loads(package.POLICY.read_text())
        for key, policy in summary["policies"].items():
            self.assertEqual(policy["heldout_primary_mean"], source["policies"][key]["primary"])
        self.assertEqual(summary["paired_primary_differences"], source["paired_differences"])

    def test_archive_is_complete_and_deterministic(self):
        first, second = package.build(), package.build()
        self.assertEqual(first, second)
        manifest = json.loads(first["experiment_sources.manifest.json"])
        self.assertFalse(manifest["standalone"])
        self.assertFalse(manifest["includes_biological_measurements"])
        with zipfile.ZipFile(io.BytesIO(first["experiment_sources.zip"])) as archive:
            self.assertEqual(len(archive.namelist()), manifest["archive_file_count"])
            for name in archive.namelist():
                self.assertNotIn("__pycache__", name)
                self.assertTrue(name.endswith((".py", ".json", ".txt")))
                self.assertEqual(package.digest(archive.read(name)), manifest["archive_member_sha256"][name])

    def test_literal_credentials_are_rejected(self):
        with self.assertRaises(ValueError):
            package.assert_not_secret(b"sk-" + b"w" * 30, "synthetic-test")
        package.assert_not_secret(b'api_key=os.environ.get("LOCAL_KEY")', "synthetic-test")


if __name__ == "__main__":
    unittest.main()
