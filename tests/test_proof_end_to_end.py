"""Run the whole thing and hand the result to veripb.

Until stage 4 these come back UNDER ASSERTIONS rather than VERIFIED, and that
is the point: everything except the propagators' own claims is already being
checked, including every line the search writes.  So the scaffolding is under
test from the beginning, and the exercises cannot break it.
"""

import io
import pathlib
import shutil
import subprocess
import tempfile
import unittest

from kindling.__main__ import INSTANCES
from kindling.proof.encoding import define_proof_model
from kindling.proof.log import ProofLog
from kindling.search import solve

HAVE_VERIPB = shutil.which("veripb") is not None


def prove(model):
    """Solve with proof logging on.  Returns (solution, opb text, pbp text)."""
    out = io.StringIO()
    log = ProofLog(out)
    solution = solve(model, log)
    return solution, define_proof_model(model).render(), out.getvalue(), log


def veripb(opb: str, pbp: str) -> str:
    with tempfile.TemporaryDirectory() as d:
        opb_path = pathlib.Path(d) / "m.opb"
        pbp_path = pathlib.Path(d) / "m.pbp"
        opb_path.write_text(opb)
        pbp_path.write_text(pbp)
        r = subprocess.run(
            ["veripb", str(opb_path), str(pbp_path)], capture_output=True, text=True
        )
        text = r.stdout + r.stderr
        for verdict in ("s UNDER ASSERTIONS", "s VERIFIED"):
            if verdict in text:
                return text[text.index(verdict) :].split("\n")[0]
        return f"REJECTED\n{text}"


@unittest.skipUnless(HAVE_VERIPB, "veripb is not on the path")
class TestEveryInstance(unittest.TestCase):
    def test_unsatisfiable_instances_produce_a_checkable_refutation(self):
        for name in ("pigeonhole", "agreement", "too-small"):
            with self.subTest(instance=name):
                solution, opb, pbp, log = prove(INSTANCES[name]())
                self.assertIsNone(solution)
                self.assertGreater(len(log.assertions), 0)
                self.assertEqual(
                    veripb(opb, pbp), "s UNDER ASSERTIONS UNSATISFIABLE"
                )

    def test_a_satisfiable_instance_claims_nothing_it_should_not(self):
        solution, opb, pbp, _ = prove(INSTANCES["latin"]())
        self.assertIsNotNone(solution)
        self.assertIn("conclusion NONE;", pbp)
        self.assertEqual(veripb(opb, pbp), "s UNDER ASSERTIONS NO CONCLUSION")


class TestProofShape(unittest.TestCase):
    def test_the_proof_is_the_same_every_time(self):
        """Proof output nobody can diff is proof output nobody can debug."""
        first = prove(INSTANCES["too-small"]())[2]
        second = prove(INSTANCES["too-small"]())[2]
        self.assertEqual(first, second)

    def test_the_search_closes_with_an_empty_clause(self):
        pbp = prove(INSTANCES["agreement"]())[2].splitlines()
        self.assertIn("rup >= 1 ;", pbp)
        self.assertEqual("conclusion UNSAT;", pbp[-2])

    def test_pigeonhole_needs_no_search(self):
        """One Hall violator at the root and nothing else: no decisions, so no
        node lines except the one that closes the proof."""
        pbp = prove(INSTANCES["pigeonhole"]())[2]
        self.assertNotIn("decide", pbp)
        self.assertEqual(pbp.count("rup"), 1)

    def test_every_assertion_says_which_propagator_made_it(self):
        pbp = prove(INSTANCES["too-small"]())[2]
        for line in pbp.splitlines():
            if line.startswith("a "):
                self.assertRegex(line, r": : [a-z_]+ ;$")


if __name__ == "__main__":
    unittest.main()
