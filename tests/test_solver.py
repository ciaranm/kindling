"""Does the solver get the right answer?

Mostly by cross-checking against an independent oracle: for a small enough
model you can enumerate every assignment and decide satisfiability by reading
the constraints' definitions directly, with none of the solver's machinery
involved.  Random models then compare the two.  A propagator that removes a
value it should not have will show up as a solution the brute force found and
the solver did not.
"""

import itertools
import random
import unittest

from kindling.constraints.all_different_int import AllDifferentInt
from kindling.constraints.int_lin_le import IntLinLe
from kindling.constraints.table_int import TableInt
from kindling.model import Model
from kindling.propagate import propagate
from kindling.search import solve
from kindling.state import Inference, State


def satisfies(constraint, assignment) -> bool:
    """The definitions, written out again and independently of the solver."""
    values = [assignment[x] for x in constraint.variables()]
    if isinstance(constraint, IntLinLe):
        return sum(c * v for c, v in zip(constraint.coefficients, values)) <= constraint.rhs
    if isinstance(constraint, AllDifferentInt):
        return len(set(values)) == len(values)
    if isinstance(constraint, TableInt):
        return tuple(values) in {tuple(t) for t in constraint.tuples}
    raise AssertionError(f"no oracle for {type(constraint).__name__}")


def brute_force(model):
    """Every solution, the slow and obvious way."""
    for combination in itertools.product(*(range(x.ub + 1) for x in model.variables)):
        assignment = dict(zip(model.variables, combination))
        if all(satisfies(c, assignment) for c in model.constraints):
            yield assignment


def random_model(rng: random.Random) -> Model:
    model = Model()
    variables = [
        model.add_variable(rng.randint(1, 3)) for _ in range(rng.randint(2, 4))
    ]
    for _ in range(rng.randint(1, 3)):
        kind = rng.choice(["lin", "alldiff", "table"])
        if kind == "lin":
            scope = rng.sample(variables, rng.randint(1, len(variables)))
            coefficients = [rng.choice([1, -1]) for _ in scope]
            model.add_constraint(
                IntLinLe(coefficients, scope, rng.randint(-2, 4))
            )
        elif kind == "alldiff":
            scope = rng.sample(variables, rng.randint(2, len(variables)))
            model.add_constraint(AllDifferentInt(scope))
        else:
            scope = rng.sample(variables, rng.randint(1, len(variables)))
            tuples = {
                tuple(rng.randint(0, x.ub) for x in scope)
                for _ in range(rng.randint(1, 5))
            }
            model.add_constraint(TableInt(scope, sorted(tuples)))
    return model


class TestAgainstBruteForce(unittest.TestCase):
    def test_random_models(self):
        rng = random.Random(0)
        for trial in range(300):
            model = random_model(rng)
            with self.subTest(trial=trial):
                expected = next(brute_force(model), None)
                solution = solve(model)
                self.assertEqual(
                    solution is not None,
                    expected is not None,
                    f"trial {trial}: solver says {solution}, brute force says {expected}",
                )
                if solution is not None:
                    for c in model.constraints:
                        self.assertTrue(
                            satisfies(c, solution),
                            f"trial {trial}: returned a non-solution",
                        )


class TestPropagation(unittest.TestCase):
    def pigeonhole(self, pigeons: int, holes: int) -> Model:
        model = Model()
        scope = [model.add_variable(holes - 1) for _ in range(pigeons)]
        model.add_constraint(AllDifferentInt(scope))
        return model

    def test_pigeonhole_needs_no_search_at_all(self):
        model = self.pigeonhole(4, 3)
        self.assertIs(propagate(model, State(model)), Inference.CONTRADICTION)

    def test_pigeonhole_that_fits_is_satisfiable(self):
        self.assertIsNotNone(solve(self.pigeonhole(3, 3)))

    def test_the_hall_violator_is_a_real_one(self):
        model = Model()
        a, b, c = (model.add_variable(2) for _ in range(3))
        alldiff = model.add_constraint(AllDifferentInt([a, b, c]))
        state = State(model)
        # squeeze a and b into {0, 1} and c is irrelevant to the violation
        state.domain(a).remove(2)
        state.domain(b).remove(2)
        state.domain(a).remove(1)
        state.domain(b).remove(1)
        variables, values = alldiff.hall_violator(state)
        self.assertGreater(len(variables), len(values))
        for x in variables:
            self.assertTrue(set(state.domain(x)) <= set(values))

    def test_propagation_reaches_a_fixpoint(self):
        """If a second run changes anything, the first did not finish, and if a
        propagator reports a change it did not make, this never terminates."""
        rng = random.Random(1)
        for trial in range(100):
            model = random_model(rng)
            state = State(model)
            with self.subTest(trial=trial):
                if propagate(model, state) is Inference.CONTRADICTION:
                    continue
                before = [sorted(d) for d in state.domains]
                propagate(model, state)
                self.assertEqual(before, [sorted(d) for d in state.domains])


class TestState(unittest.TestCase):
    def test_a_clone_cannot_disturb_its_parent(self):
        model = Model()
        a = model.add_variable(3)
        parent = State(model)
        child = parent.clone()
        child.assume_equal(a, 1)
        self.assertEqual(sorted(parent.domain(a)), [0, 1, 2, 3])
        self.assertEqual(sorted(child.domain(a)), [1])

    def test_decisions_are_recorded_for_the_proof(self):
        model = Model()
        a = model.add_variable(3)
        state = State(model)
        state.assume_equal(a, 2)
        child = state.clone()
        child.assume_not_equal(a, 2)
        self.assertEqual(state.decisions, ["x1eq2"])
        self.assertEqual(child.decisions, ["x1eq2", "~x1eq2"])

    def test_domains_come_out_in_order(self):
        model = Model()
        a = model.add_variable(5)
        state = State(model)
        state.domain(a).remove(3)
        self.assertEqual(list(state.domain(a)), [0, 1, 2, 4, 5])


if __name__ == "__main__":
    unittest.main()
