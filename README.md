# kindling

A very small constraint solver that shows its working.

It has bounded integer variables, three constraints, no cleverness anywhere,
and it writes a proof of everything it does in a format a separate program can
check. It exists to be read and hacked on, not to be fast — a serious solver
would do almost all of this differently, and where that matters the code says
so.

```
python3 -m kindling pigeonhole
python3 -m kindling pigeonhole --prove /tmp/ph --check
veripb /tmp/ph.opb /tmp/ph.pbp
```

Nothing needs installing. There are no dependencies, the tests use only what
comes with Python, and the only external program involved is
[VeriPB](https://gitlab.com/MIAOresearch/software/VeriPB), which checks the
proofs and which you will already have.

If you have MiniZinc, kindling is a solver it can drive:

```
minizinc --solver minizinc/kindling.msc instances/pigeonhole.mzn
minizinc --solver minizinc/kindling.msc --prove /tmp/ph instances/pigeonhole.mzn
```

## What is where

| | |
|---|---|
| `kindling/model.py` | variables and constraints, before anything happens to them |
| `kindling/domain.py` `state.py` | what changes during search, and the only place it can change |
| `kindling/propagate.py` `search.py` | the queue, and depth-first search by cloning |
| `kindling/constraints/` | one file per constraint: how it propagates *and* how it justifies |
| `kindling/justify.py` | what a justification is, and why we use the crude kind |
| `kindling/proof/` | the `.opb` (what the problem means) and the `.pbp` (what we did) |
| `kindling/fzn.py` | reading flattened MiniZinc, and nothing else knows this exists |
| `kindling/bugs.py` | propagators with things wrong with them, on purpose |
| `spike/` | proofs written by hand before any of this, and what they settled |

## The practical

See [docs/practical.md](docs/practical.md). Briefly: three inferences in this
solver are asserted rather than justified, so VeriPB says `UNDER ASSERTIONS`
instead of `VERIFIED`, and the exercises are to replace them one at a time.

```
python3 -m unittest discover -s tests -t .
```

On a fresh clone the only failures are in `tests/test_exercises.py`: one per
exercise, each naming what is still unjustified, plus one for everything that
is waiting on all three. If anything *else* fails, you have broken the solver
rather than not finished yet.

Solutions are on the `ash` branch.

## Reading it

Start with `spike/NOTES.md`, which is the hand-written proofs this was built
from and the shape of every derivation in it. Then `kindling/proof/encoding.py`
for how an integer becomes pseudo-Boolean, then any one file under
`constraints/`.

The two things most worth understanding are in `justify.py` (what a solver owes
a checker, and the difference between the answer being right and the reasoning
being sound) and `proof/log.py` (why the entire proof of the search is one line
per dead end).
