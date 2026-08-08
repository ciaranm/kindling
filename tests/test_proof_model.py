"""The .opb we generate has to be the one the stage-0 proofs were written
against.  Those proofs were checked by hand against a throwaway generator; if
the real writer produces something they still verify against, both agree.
"""

import pathlib
import shutil
import subprocess
import tempfile
import unittest

from kindling.constraints.all_different_int import AllDifferentInt
from kindling.constraints.int_lin_le import IntLinLe
from kindling.constraints.table_int import TableInt
from kindling.model import Model
from kindling.proof.encoding import define_proof_model

SPIKE = pathlib.Path(__file__).parent.parent / "spike"
HAVE_VERIPB = shutil.which("veripb") is not None


def pigeonhole() -> Model:
    model = Model()
    for i in range(4):
        model.add_variable(2, f"pigeon{i}")
    model.add_constraint(AllDifferentInt([1, 2, 3, 4]))
    return model


def table_and_all_different() -> Model:
    model = Model()
    model.add_variable(1)
    model.add_variable(1)
    model.add_constraint(TableInt([1, 2], [(0, 0), (1, 1)]))
    model.add_constraint(AllDifferentInt([1, 2]))
    return model


def check(model: Model, proof: pathlib.Path) -> str:
    with tempfile.TemporaryDirectory() as d:
        opb = pathlib.Path(d) / "model.opb"
        opb.write_text(define_proof_model(model).render())
        r = subprocess.run(
            ["veripb", str(opb), str(proof)], capture_output=True, text=True
        )
        text = r.stdout + r.stderr
        if "s UNDER ASSERTIONS" in text:
            return "UNDER ASSERTIONS"
        return "VERIFIED" if "s VERIFIED" in text else f"REJECTED\n{text}"


@unittest.skipUnless(HAVE_VERIPB, "veripb is not on the path")
class TestAgainstStageZeroProofs(unittest.TestCase):
    def test_pigeonhole(self):
        self.assertEqual(
            check(pigeonhole(), SPIKE / "03-pigeonhole" / "pigeonhole.pbp"), "VERIFIED"
        )

    def test_table_support_removal(self):
        self.assertEqual(
            check(table_and_all_different(), SPIKE / "04-table" / "table.pbp"),
            "VERIFIED",
        )

    def test_two_node_refutation(self):
        self.assertEqual(
            check(table_and_all_different(), SPIKE / "05-search" / "search.pbp"),
            "VERIFIED",
        )

    def test_the_same_refutation_with_the_propagators_asserted(self):
        self.assertEqual(
            check(
                table_and_all_different(),
                SPIKE / "05-search" / "search-assertions.pbp",
            ),
            "UNDER ASSERTIONS",
        )


def rup_holds(model: Model, constraint: str) -> bool:
    """Whether veripb accepts this constraint as reverse unit propagation from
    the model alone."""
    proof = (
        "pseudo-Boolean proof version 3.0\n"
        f"rup {constraint} ;\n"
        "output NONE;\nconclusion NONE;\nend pseudo-Boolean proof;\n"
    )
    with tempfile.TemporaryDirectory() as d:
        opb = pathlib.Path(d) / "model.opb"
        pbp = pathlib.Path(d) / "check.pbp"
        opb.write_text(define_proof_model(model).render())
        pbp.write_text(proof)
        r = subprocess.run(
            ["veripb", str(opb), str(pbp)], capture_output=True, text=True
        )
        return "s VERIFIED" in r.stdout + r.stderr


@unittest.skipUnless(HAVE_VERIPB, "veripb is not on the path")
class TestUnitPropagationReach(unittest.TestCase):
    """Propagators reason about one variable's atoms all the time -- this value
    is gone because the lower bound moved past it, this bound follows from that
    one -- and every such step has to be something the checker can do by unit
    propagation, or the node it happens at will not check.  The encoding has no
    order chain rows and does not need any; this is the test that says so.

    Do not cherry-pick the bounds.  Whether unit propagation gets from one atom
    to another depends on whether the bound in question pins an individual bit,
    and hand-picked examples have an awkward habit of being ones that work for
    the wrong reason.  Check every pair, at several domain sizes, including
    ones where the bits can represent more than the domain allows.
    """

    UBS = (3, 5, 7, 8, 12)

    def variable(self, ub: int) -> Model:
        model = Model()
        model.add_variable(ub)
        return model

    def test_a_bound_implies_every_weaker_bound(self):
        for ub in self.UBS:
            for v in range(2, ub + 1):
                for w in range(1, v):
                    with self.subTest(ub=ub, v=v, w=w):
                        self.assertTrue(
                            rup_holds(self.variable(ub), f"1 ~x1ge{v} 1 x1ge{w} >= 1")
                        )

    def test_a_bound_rules_out_every_value_below_it(self):
        for ub in self.UBS:
            for v in range(1, ub + 1):
                for w in range(0, v):
                    with self.subTest(ub=ub, v=v, w=w):
                        self.assertTrue(
                            rup_holds(self.variable(ub), f"1 ~x1ge{v} 1 ~x1eq{w} >= 1")
                        )

    def test_a_value_rules_out_every_other_value(self):
        for ub in self.UBS:
            for v in range(0, ub + 1):
                for w in range(0, v):
                    with self.subTest(ub=ub, v=v, w=w):
                        self.assertTrue(
                            rup_holds(self.variable(ub), f"1 ~x1eq{v} 1 ~x1eq{w} >= 1")
                        )

    def test_and_it_does_not_prove_things_that_are_false(self):
        self.assertFalse(rup_holds(self.variable(7), "1 ~x1ge5 1 x1ge6 >= 1"))
        self.assertFalse(rup_holds(self.variable(7), "1 ~x1ge3 1 x1eq3 >= 1"))
        self.assertFalse(rup_holds(self.variable(7), "1 ~x1eq3 1 x1ge5 >= 1"))


class TestModel(unittest.TestCase):
    def test_negative_domains_are_refused(self):
        with self.assertRaisesRegex(ValueError, "negative domains"):
            Model().add_variable(-1)

    def test_coefficients_other_than_plus_or_minus_one_are_refused(self):
        with self.assertRaisesRegex(ValueError, "one of the exercises"):
            IntLinLe([2], [1], 3)

    def test_constraints_must_refer_to_variables_that_exist(self):
        model = Model()
        model.add_variable(3)
        with self.assertRaisesRegex(ValueError, "unknown variable x2"):
            model.add_constraint(AllDifferentInt([1, 2]))

    def test_a_tuple_outside_the_domains_is_killed_not_dropped(self):
        model = Model()
        model.add_variable(1)
        model.add_variable(1)
        model.add_constraint(TableInt([1, 2], [(0, 0), (1, 9)]))
        labels = [row.label for row in define_proof_model(model).rows()]
        self.assertIn("tbl1t1_dead", labels)


if __name__ == "__main__":
    unittest.main()
