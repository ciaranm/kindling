#!/usr/bin/env python3
"""Writes the .opb file for each stage-0 spike example."""

import pathlib

from gen import all_different, linear_le, render, table

HERE = pathlib.Path(__file__).parent

EXAMPLES = {}

# 01: a linear bound inference that reverse unit propagation cannot check.
# x1 + x2 + x3 <= 9 with x2 >= 3 and x3 >= 3 forces x1 <= 3.  No single bit is
# determined by any of the three bounds, so unit propagation sees nothing.
EXAMPLES["01-linear"] = render(
    "x1, x2, x3 in [0,7]; x1 + x2 + x3 <= 9",
    {1: 7, 2: 7, 3: 7},
    [linear_le(1, [(1, 1), (1, 2), (1, 3)], [7, 7, 7], 9)],
)

# 02: the same shape with a negative coefficient.  x1 + x2 - x3 <= 0 with
# x1 >= 3 and x3 <= 4 forces x2 <= 1.  The reason for x3 is an upper bound, so
# its channelling constraint is the one going the other way.
EXAMPLES["02-linear-neg"] = render(
    "x1, x2, x3 in [0,7]; x1 + x2 - x3 <= 0",
    {1: 7, 2: 7, 3: 7},
    [linear_le(1, [(1, 1), (1, 2), (-1, 3)], [7, 7, 7], 0)],
)

# 03: pigeonhole.  Four variables over three values, all different.  The whole
# refutation is one cutting-planes addition and needs no search at all.
EXAMPLES["03-pigeonhole"] = render(
    "x1..x4 in [0,2]; all_different(x1, x2, x3, x4)",
    {1: 2, 2: 2, 3: 2, 4: 2},
    [all_different(1, [1, 2, 3, 4], [0, 1, 2])],
)

# 04/05: table support removal, then the same instance end to end.
# table(x1, x2) in {(0,0), (1,1)} plus all_different(x1, x2) is unsatisfiable,
# but neither propagator sees it at the root -- it takes two nodes.
_INSTANCE = (
    "x1, x2 in [0,1]; table(x1,x2) in {(0,0),(1,1)}; all_different(x1,x2)",
    {1: 1, 2: 1},
    [
        table(1, [1, 2], [(0, 0), (1, 1)]),
        all_different(2, [1, 2], [0, 1]),
    ],
)
EXAMPLES["04-table"] = render(*_INSTANCE)
EXAMPLES["05-search"] = render(*_INSTANCE)

if __name__ == "__main__":
    for name, text in EXAMPLES.items():
        d = HERE / name
        d.mkdir(exist_ok=True)
        (d / f"{name.split('-', 1)[1]}.opb").write_text(text)
        print(f"{name}: {len(text.splitlines())} lines")
