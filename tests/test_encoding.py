"""The variable encoding is either exactly right or it is worthless, so check
it exhaustively rather than by eyeballing a few rows.

For a small variable there are few enough assignments to its atoms that we can
try all of them, and demand that the rows are satisfied by exactly the
assignments where every atom means what its name says.
"""

import itertools
import unittest

from kindling.proof.encoding import define_variable
from kindling.proof.names import bit, eq, ge, nbits
from kindling.proof.opb import OpbFile


class TestVariableEncoding(unittest.TestCase):
    def test_rows_hold_exactly_when_the_atoms_mean_what_they_say(self):
        for ub in range(0, 6):
            with self.subTest(ub=ub):
                opb = OpbFile()
                define_variable(opb, 1, ub)
                rows = opb.rows()
                atoms = sorted(opb.atoms())

                for values in itertools.product([False, True], repeat=len(atoms)):
                    assignment = dict(zip(atoms, values))
                    x = sum(
                        2**k for k in range(nbits(ub)) if assignment[bit(1, k)]
                    )
                    intended = (
                        x <= ub
                        and all(
                            assignment[ge(1, v)] == (x >= v) for v in range(1, ub + 1)
                        )
                        and all(
                            assignment[eq(1, v)] == (x == v) for v in range(0, ub + 1)
                        )
                    )
                    actual = all(row.holds_under(assignment) for row in rows)
                    self.assertEqual(
                        intended,
                        actual,
                        f"ub={ub}, x={x}, {assignment}",
                    )

    def test_every_atom_a_propagator_might_use_exists(self):
        opb = OpbFile()
        define_variable(opb, 1, 3)
        atoms = opb.atoms()
        for v in range(0, 4):
            self.assertIn(eq(1, v), atoms)
        for v in range(1, 4):
            self.assertIn(ge(1, v), atoms)

    def test_every_row_is_labelled(self):
        opb = OpbFile()
        define_variable(opb, 1, 4)
        self.assertTrue(all(row.label for row in opb.rows()))
        labels = [row.label for row in opb.rows()]
        self.assertEqual(len(labels), len(set(labels)), "labels must be unique")


if __name__ == "__main__":
    unittest.main()
