"""Check execution order, formal definitions and fixed-slate accounting."""
from pathlib import Path
import json
import unittest

PAPER = Path(__file__).resolve().parents[1]


class MethodExecutionTests(unittest.TestCase):
    def setUp(self):
        self.method = (PAPER / "sections/03_method.tex").read_text()
        self.appendix = (PAPER / "sections/22_appendix_unified_protocol.tex").read_text()

    def test_duration_is_not_a_design_factor(self):
        self.assertIn("assign each candidate 100 training rounds", self.method)
        self.assertIn(r"not by \texttt{design\_id}", self.method)
        self.assertIn("learning rate, weight decay, coordinator momentum", self.method)
        self.assertIn("This separate allocation study", self.method)
        self.assertIn("does not generate language-model proposals", self.method)
        for phrase in ("every design for 80 rounds", "each for 20 rounds",
                       "six promoted designs restart from their initial parameters",
                       "four unpromoted designs stop after screening"):
            self.assertIn(phrase, self.appendix)
        protocol = json.loads((PAPER / "provenance/v6_loop_summary.json").read_text())["protocol"]
        self.assertEqual(protocol["candidate_count_per_arm"], 10)
        self.assertEqual(10 * 80, 10 * 20 + 6 * 100)
        self.assertEqual(protocol["full_client_rounds_per_arm"], 800)
        self.assertIn("8,000 local epochs", self.appendix)
        self.assertIn("160 aggregate development evaluations", self.appendix)

    def test_inputs_precede_fitting_and_research_equations(self):
        self.assertLess(self.method.index(r"D_i^{\mathrm{train}}"),
                        self.method.index(r"\label{eq:local-fitting}"))
        for token in (r"\pi_i=n_i/\sum_{j=1}^{K}n_j",
                      r"v_r&=\beta_a v_{r-1}+\bar w_r-w_{r-1}",
                      r"\bar s(a,r)=\frac{1}{|\mathcal P|}\sum_{i\in\mathcal P}s_i(a,r)",
                      r"\bar\ell(a,r)=\frac{1}{|\mathcal P|}\sum_{i\in\mathcal P}\ell_i^{\mathrm{dev}}(a,r)",
                      r"\mathcal E_{t+1}=\mathcal E_t\mathbin{\|}[e_t]"):
            self.assertIn(token, self.method)
        self.assertIn("earlier round retained on a complete tie", self.method)
        self.assertIn("History feedback begins with the second proposal", self.method)
        self.assertIn("fixed-pool repartitioning retains all ten original panels", self.method)
        self.assertIn("source-transfer studies use the original target panels", self.method)
        self.assertIn("only if its score/loss pair is better", self.appendix)

    def test_initialization_and_feedback_boundaries(self):
        for phrase in ("resets the predictor to its prescribed initialization",
                       "distributes it to all training laboratories",
                       "first and last development-evaluation rounds",
                       "without fine-tuning the self-improving model",
                       "source-specific head", "original target's development panels"):
            self.assertIn(phrase, self.method)
        self.assertIn("failed fits consume a proposal slot", self.method)
        self.assertNotIn("The research language model remains fixed; adaptation occurs", self.method)

    def test_notation_and_roles_are_consistent(self):
        self.assertIn(r"\{D_i^{\mathrm{dev}}\}_{i\in\mathcal P}", self.method)
        self.assertNotIn(r"D_j^{\mathrm{dev}}", self.method)
        self.assertIn(r"instantiate $f_{a,w}$ as task-specific predictors", self.method)
        self.assertIn(r"evaluate the aggregated predictor $f_{a,w_r}$", self.method)
        self.assertNotRegex(self.method.lower(), r"\bworkers?\b|\bserver\b|\bclients?\b")
        self.assertNotIn(r"\operatorname{Init}(a,z)", self.method)
        self.assertEqual(self.method.count("Appendix A"), 1)
        self.assertIn("Floating-point buffers", self.appendix)
        self.assertIn("study seed", self.appendix)

    def test_promotion_and_resampling_are_explicit(self):
        for phrase in ("best screening checkpoint", "round 5 to round 20",
                       "lower round-20 development loss", "5,000 hierarchical paired resamples",
                       "1,000 fixed-seed resamples", "resets each round"):
            self.assertIn(phrase, self.appendix)

    def test_design_schema_does_not_execute_rationale(self):
        for key in ("hypothesis", "experiment", "expected_effect", "design_id"):
            self.assertIn('"' + key + '"', self.appendix)
        self.assertIn("D00 denotes the starting configuration", self.appendix)
        self.assertIn("not an additional executable instruction or a measured result", self.appendix)
        self.assertIn("same", self.appendix.split("Five-option queries and scoring.")[1])
        self.assertIn("fixed shuffled option order", self.appendix)


if __name__ == "__main__":
    unittest.main()
