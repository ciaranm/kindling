"""Reading flattened models.

Two things matter here.  The shipped instances have to load and give the right
answer, and everything else has to be refused out loud -- a reader that drops a
constraint it did not recognise would hand the checker a perfectly good
refutation of a problem nobody posed.
"""

import pathlib
import unittest

from kindling.fzn import Unsupported, read
from kindling.search import solve
from tests.test_solver import brute_force

INSTANCES = pathlib.Path(__file__).parent.parent / "instances"


def document(variables, constraints, arrays=None, method="satisfy"):
    return {
        "variables": variables,
        "arrays": arrays or {},
        "constraints": constraints,
        "solve": {"method": method},
    }


class TestShippedInstances(unittest.TestCase):
    def test_they_all_load_and_agree_with_brute_force(self):
        for path in sorted(INSTANCES.glob("*.fzn.json")):
            with self.subTest(instance=path.name):
                model = read(path)
                if len(model.variables) > 8:
                    continue  # latin is too big to enumerate, and is solved below
                self.assertEqual(
                    solve(model) is not None, next(brute_force(model), None) is not None
                )

    def test_the_satisfiable_one_is_solved(self):
        self.assertIsNotNone(solve(read(INSTANCES / "latin.fzn.json")))

    def test_the_unsatisfiable_ones_are_refuted(self):
        for name in ("pigeonhole", "agreement", "over_budget"):
            with self.subTest(instance=name):
                self.assertIsNone(solve(read(INSTANCES / f"{name}.fzn.json")))


@unittest.skipUnless(
    __import__("shutil").which("veripb") is not None, "veripb is not on the path"
)
class TestShippedInstancesProve(unittest.TestCase):
    def test_the_refutations_check(self):
        from tests.test_proof_end_to_end import prove, veripb

        for name in ("pigeonhole", "agreement", "over_budget"):
            with self.subTest(instance=name):
                solution, opb, pbp, log = prove(read(INSTANCES / f"{name}.fzn.json"))
                self.assertIsNone(solution)
                self.assertEqual(log.assertions, [])
                self.assertEqual(veripb(opb, pbp), "s VERIFIED UNSATISFIABLE")


class TestRefusals(unittest.TestCase):
    def refuses(self, doc, expected):
        with self.assertRaises(Unsupported) as caught:
            read(doc)
        self.assertIn(expected, str(caught.exception))

    def test_a_constraint_we_do_not_have(self):
        self.refuses(
            document(
                {"x": {"type": "int", "domain": [[0, 3]]}},
                [{"id": "int_lin_ne", "args": [[1], ["x"], 2]}],
            ),
            "does not have int_lin_ne",
        )

    def test_a_variable_that_is_not_an_integer(self):
        self.refuses(
            document({"b": {"type": "bool"}}, []), "kindling only has integers"
        )

    def test_a_variable_that_can_be_negative(self):
        self.refuses(
            document({"x": {"type": "int", "domain": [[-2, 2]]}}, []),
            "variables start at zero",
        )

    def test_a_variable_with_no_domain_at_all(self):
        self.refuses(document({"x": {"type": "int"}}, []), "kindling needs bounds")

    def test_being_asked_to_optimise(self):
        self.refuses(
            document({}, [], method="minimize"), "kindling only satisfies"
        )

    def test_an_array_that_is_not_there(self):
        self.refuses(
            document(
                {"x": {"type": "int", "domain": [[0, 3]]}},
                [{"id": "int_lin_le", "args": ["missing", ["x"], 2]}],
            ),
            "no array called missing",
        )


class TestTranslation(unittest.TestCase):
    def solutions(self, model):
        return {
            tuple(sorted((x.name, v) for x, v in a.items()))
            for a in brute_force(model)
        }

    def test_a_domain_with_a_hole_in_it_keeps_the_hole(self):
        model = read(
            document({"x": {"type": "int", "domain": [[0, 1], [3, 4]]}}, [])
        )
        self.assertEqual(model.variables[0].ub, 4)
        values = {v for a in brute_force(model) for v in a.values()}
        self.assertEqual(values, {0, 1, 3, 4})

    def test_a_domain_that_starts_late_keeps_its_lower_bound(self):
        model = read(document({"x": {"type": "int", "domain": [[2, 4]]}}, []))
        values = {v for a in brute_force(model) for v in a.values()}
        self.assertEqual(values, {2, 3, 4})

    def test_an_equality_becomes_two_inequalities(self):
        model = read(
            document(
                {
                    "x": {"type": "int", "domain": [[0, 3]]},
                    "y": {"type": "int", "domain": [[0, 3]]},
                },
                [{"id": "int_lin_eq", "args": [[1, -1], ["x", "y"], 0]}],
            )
        )
        self.assertEqual(len(model.constraints), 2)
        for assignment in brute_force(model):
            self.assertEqual(len(set(assignment.values())), 1)

    def test_a_constant_among_the_variables_moves_to_the_other_side(self):
        model = read(
            document(
                {"x": {"type": "int", "domain": [[0, 5]]}},
                [{"id": "int_lin_le", "args": [[1], ["x", 2], 4]}],
            )
        )
        self.assertEqual(model.constraints[0].rhs, 2)

    def test_a_table_recovers_its_tuples_from_one_long_list(self):
        model = read(
            document(
                {
                    "x": {"type": "int", "domain": [[0, 3]]},
                    "y": {"type": "int", "domain": [[0, 3]]},
                },
                [{"id": "fzn_table_int", "args": [["x", "y"], [0, 1, 2, 3]]}],
            )
        )
        self.assertEqual(model.constraints[0].tuples, [(0, 1), (2, 3)])

    def test_a_table_whose_values_do_not_divide_evenly(self):
        with self.assertRaisesRegex(Unsupported, "3 values in it"):
            read(
                document(
                    {
                        "x": {"type": "int", "domain": [[0, 3]]},
                        "y": {"type": "int", "domain": [[0, 3]]},
                    },
                    [{"id": "fzn_table_int", "args": [["x", "y"], [0, 1, 2]]}],
                )
            )


if __name__ == "__main__":
    unittest.main()


REPOSITORY = pathlib.Path(__file__).parent.parent
HAVE_MINIZINC = __import__("shutil").which("minizinc") is not None


@unittest.skipUnless(HAVE_MINIZINC, "minizinc is not installed")
class TestMiniZincBackend(unittest.TestCase):
    """kindling is a MiniZinc solver, so the whole path from a model to an
    answer should work with one command and no intermediate files.  If the
    solver configuration or the library of native constraints is wrong, this is
    what notices."""

    def run_minizinc(self, model: str, *extra: str) -> str:
        import subprocess

        result = subprocess.run(
            ["minizinc", "--solver", str(REPOSITORY / "minizinc" / "kindling.msc"),
             *extra, str(INSTANCES / model)],
            capture_output=True, text=True, cwd=REPOSITORY,
        )
        return result.stdout + result.stderr

    def test_an_unsatisfiable_model(self):
        self.assertIn("=====UNSATISFIABLE=====", self.run_minizinc("pigeonhole.mzn"))

    def test_a_satisfiable_model_comes_back_as_minizinc_wrote_it(self):
        out = self.run_minizinc("latin.mzn")
        self.assertIn("----------", out)
        self.assertNotIn("UNSATISFIABLE", out)

    def test_all_different_survives_flattening(self):
        """If mznlib stopped declaring it native, MiniZinc would decompose it
        into disequalities and the reader would refuse the whole model."""
        self.assertNotIn("does not have", self.run_minizinc("pigeonhole.mzn"))

    def test_table_survives_flattening(self):
        self.assertNotIn("does not have", self.run_minizinc("agreement.mzn"))
