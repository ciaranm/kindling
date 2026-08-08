"""The deliberately broken propagators, and what the checker makes of them.

This is the demonstration the whole module is for, so it had better keep
working.  It comes after the exercises -- a broken propagator is only
interesting once the working ones are justified -- so these skip until then.

Each bug has to be caught somewhere, and the interesting part is that *where*
differs, in ways that say something true about what proof logging does and does
not do for you.
"""

import subprocess
import sys
import unittest

from tests.test_proof_end_to_end import EXERCISES_DONE, FINISH_FIRST


def run(instance: str, bug: str) -> tuple[str, str]:
    """Returns (what the solver said, what veripb said)."""
    import pathlib
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        result = subprocess.run(
            [
                sys.executable, "-m", "kindling", instance,
                "--prove", str(pathlib.Path(d) / "p"), "--check", "--bug", bug,
            ],
            capture_output=True, text=True, timeout=120,
            cwd=pathlib.Path(__file__).parent.parent,
        )
    text = result.stdout + result.stderr
    answer = "unsatisfiable" if "unsatisfiable" in text else "solution"
    for verdict in ("REJECTED", "UNDER ASSERTIONS", "VERIFIED"):
        if verdict in text:
            return answer, verdict
    return answer, f"?? {text[:200]}"


@unittest.skipUnless(EXERCISES_DONE, FINISH_FIRST)
class TestBugsAreCaught(unittest.TestCase):
    def test_an_unsound_propagator_loses_the_only_solution_and_is_caught(self):
        """puzzle has exactly one solution and it sits on the edge of all three
        constraints, so a propagator that removes one value too many throws it
        away.  The solver then claims there is no solution, and that claim is
        false, so the proof of it cannot be checked."""
        for bug in (
            "table-forgets-a-tuple",
            "all-different-too-eager",
            "linear-off-by-one",
        ):
            with self.subTest(bug=bug):
                answer, verdict = run("puzzle", bug)
                self.assertEqual(answer, "unsatisfiable", "expected a wrong answer")
                self.assertEqual(verdict, "REJECTED")

    def test_a_correct_propagator_with_a_bad_derivation_is_caught(self):
        """The other kind.  Nothing is wrong with the search -- the answer is
        right and no test of the solver's behaviour would notice -- but the
        proof cannot support what it claims."""
        for instance in ("tight-sum", "over-budget"):
            with self.subTest(instance=instance):
                answer, verdict = run(instance, "linear-forgets-a-row")
                self.assertEqual(answer, "unsatisfiable", "the answer is still right")
                self.assertEqual(verdict, "REJECTED")

    def test_a_wrong_propagator_on_an_unsatisfiable_instance_is_not_caught(self):
        """And the case worth arguing about in the lecture.  On an instance
        with no solutions, everything is implied, so a claim the propagator had
        no business making can still be perfectly derivable.  The proof is
        correct, because the answer is correct -- proof logging certifies what
        the solver concluded, not how it got there."""
        answer, verdict = run("tight-sum", "table-forgets-a-tuple")
        self.assertEqual(answer, "unsatisfiable")
        self.assertEqual(verdict, "VERIFIED")


if __name__ == "__main__":
    unittest.main()
