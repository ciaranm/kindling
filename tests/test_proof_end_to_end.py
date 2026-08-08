"""Run the whole thing and hand the result to veripb.

Every line is now checked, so the only acceptable answer is VERIFIED.  An
assertion left anywhere downgrades that to UNDER ASSERTIONS, which is exactly
what a student sees while working through the exercises, and exactly what must
never be true of the solutions.
"""

import io
import pathlib
import random
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

from kindling.__main__ import INSTANCES
from kindling.constraints.int_lin_le import IntLinLe
from kindling.justify import Rup
from kindling.proof.encoding import define_proof_model
from kindling.proof.log import ProofLog
from kindling.search import solve
from tests.test_solver import random_model

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
        for name in ("pigeonhole", "agreement", "too-small", "cycle"):
            with self.subTest(instance=name):
                solution, opb, pbp, log = prove(INSTANCES[name]())
                self.assertIsNone(solution)
                self.assertEqual(log.assertions, [], "nothing should be asserted")
                self.assertEqual(veripb(opb, pbp), "s VERIFIED UNSATISFIABLE")

    def test_a_satisfiable_instance_claims_nothing_it_should_not(self):
        solution, opb, pbp, _ = prove(INSTANCES["latin"]())
        self.assertIsNotNone(solution)
        self.assertIn("conclusion NONE;", pbp)
        self.assertEqual(veripb(opb, pbp), "s VERIFIED NO CONCLUSION")


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

    def test_nothing_is_asserted_anywhere(self):
        for name in INSTANCES:
            with self.subTest(instance=name):
                pbp = prove(INSTANCES[name]())[2]
                self.assertNotIn("\na ", pbp)



@unittest.skipUnless(HAVE_VERIPB, "veripb is not on the path")
class TestRandomRefutations(unittest.TestCase):
    """Three instances chosen by the person who wrote the derivations is not
    much of a test of them.  Throw random models at it instead and make the
    checker rule on every refutation that comes out."""

    def test_random_unsatisfiable_models_are_refuted_checkably(self):
        rng = random.Random(7)
        refuted = 0
        for trial in range(250):
            model = random_model(rng)
            solution, opb, pbp, log = prove(model)
            if solution is not None:
                continue
            refuted += 1
            with self.subTest(trial=trial):
                self.assertEqual(log.assertions, [])
                self.assertEqual(veripb(opb, pbp), "s VERIFIED UNSATISFIABLE")
        self.assertGreater(refuted, 20, "hardly any of these were unsatisfiable")


@unittest.skipUnless(HAVE_VERIPB, "veripb is not on the path")
class TestTheWrongAnswerFails(unittest.TestCase):
    """An exercise nobody can fail is not an exercise.

    Reverse unit propagation is stronger than it looks here, because a decision
    pins a variable to one value and so pins its bits, and once enough bits are
    pinned the checker can finish a linear inference on its own.  On plenty of
    instances that means a student could write Rup() where cutting planes are
    called for, get a green light, and learn nothing.  These tests say that at
    least one shipped instance is not like that, for each derivation there is
    an exercise about.  If one of them ever starts passing, the instance has
    stopped doing its job and the exercise has quietly become free.
    """

    def rejects(self, instance: str) -> None:
        solution, opb, pbp, _ = prove(INSTANCES[instance]())
        self.assertIsNone(solution)
        self.assertNotIn("VERIFIED", veripb(opb, pbp))

    def test_int_lin_le_cannot_get_away_with_a_bare_rup(self):
        with mock.patch("kindling.constraints.int_lin_le.Pol", lambda steps: Rup()):
            self.rejects("tight-sum")

    def test_all_different_cannot_get_away_with_a_bare_rup(self):
        with mock.patch(
            "kindling.constraints.all_different_int.Pol", lambda steps: Rup()
        ):
            self.rejects("pigeonhole")

    def channelling_stuck(self, direction: str):
        """Every channelling row taken in the same direction, right or wrong."""
        original = IntLinLe.channelling
        other = "_up" if direction == "_dn" else "_dn"
        return mock.patch.object(
            IntLinLe,
            "channelling",
            lambda self, position, value: original(self, position, value).replace(
                other, direction
            ),
        )

    def test_a_positive_coefficient_needs_the_up_row(self):
        with self.channelling_stuck("_dn"):
            self.rejects("tight-sum")

    def test_a_negative_coefficient_needs_the_dn_row(self):
        with self.channelling_stuck("_up"):
            self.rejects("over-budget")

if __name__ == "__main__":
    unittest.main()
