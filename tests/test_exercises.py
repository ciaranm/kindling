"""Have the exercises been done?

These three are the only tests that fail on a fresh clone, and each one names
the exercise it is waiting for.  Everything else in tests/ checks that the
solver and the proof scaffolding are right, and passes either way -- so if
something other than these breaks, you have broken the solver rather than not
finished the exercises yet.

Run them with

    python3 -m unittest discover -s tests -t .

An exercise is done when its instance verifies with nothing asserted.  Watch
for UNDER ASSERTIONS rather than REJECTED: the first means the proof is
structurally fine and something in it has not been justified yet, the second
means something in it is wrong.
"""

import unittest

from tests.test_proof_end_to_end import HAVE_VERIPB, INSTANCES, prove, veripb


@unittest.skipUnless(HAVE_VERIPB, "veripb is not on the path")
class TestExercises(unittest.TestCase):
    def verifies(self, instance: str, exercise: str) -> None:
        solution, opb, pbp, log = prove(INSTANCES[instance]())
        self.assertIsNone(solution, f"{instance} should have no solution")
        verdict = veripb(opb, pbp)
        self.assertNotIn(
            "REJECTED",
            verdict,
            f"the proof of {instance} was rejected, which means something is "
            f"wrong rather than missing:\n{verdict}",
        )
        self.assertEqual(
            log.assertions,
            [],
            f"{exercise}: {instance} still asserts "
            + ", ".join(sorted(set(log.assertions))),
        )
        self.assertEqual(verdict, "s VERIFIED UNSATISFIABLE")

    def test_exercise_1_table_support_removal_is_justified(self):
        self.verifies("agreement", "exercise 1")

    def test_exercise_2_negative_coefficients_are_justified(self):
        self.verifies("over-budget", "exercise 2")

    def test_exercise_3_the_hall_violator_is_derived(self):
        self.verifies("squeeze", "exercise 3")

    def test_and_then_everything_else_verifies_too(self):
        for instance in ("pigeonhole", "too-small", "cycle", "tight-sum"):
            with self.subTest(instance=instance):
                self.verifies(instance, "some exercise")


if __name__ == "__main__":
    unittest.main()
