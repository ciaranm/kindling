# kindling: the practical

Three inferences in this solver are asserted rather than justified. VeriPB will
tell you so:

```
$ python3 -m kindling pigeonhole --prove /tmp/ph --check
unsatisfiable
2 unjustified inferences: 2 x all_different_hall
veripb: UNDER ASSERTIONS -- everything checked except what we asserted
```

`UNDER ASSERTIONS` means the proof is structurally complete and the checker
agreed with every line except the ones that said "trust me". `REJECTED` means
something in it is *wrong*. Watch which one you get; they mean quite different
things and you will meet both.

Your feedback loop is:

```
python3 -m unittest discover -s tests -t .
```

Three tests fail to begin with, one per exercise, and each says which. Anything
else failing means the solver is broken rather than unfinished.

## Before you start

Have a look at what a proof looks like. This one is short enough to read in
full:

```
python3 -m kindling agreement --prove /tmp/ag
cat /tmp/ag.pbp
```

Two variables that a table says must agree and an `all_different` says must
differ. The proof has a preamble, two nodes, and a line at the bottom of each
saying the guesses that led there cannot all hold. That last shape is the
entire proof of the search: **one line per dead end**, and the root is a dead
end with nothing in it, so the line that finishes the proof is the same line as
all the others with nothing left in it.

Then look at `/tmp/ag.opb`, which says what the problem means. Most of it is
the encoding of the variables — every integer gets bits, an atom for each
`>= v`, and an atom for each `= v`, all written out in full.

## Exercise 1: table

`kindling/constraints/table_int.py` removes a value when no tuple can support
it any more, and asserts that it was allowed to. It is allowed to, and the
reason is reverse unit propagation: assume the value is still there, and the
selector atoms fall over one at a time until the row saying *some* tuple is in
use is contradicted.

Replace the two `Assert(...)` with `Rup()`.

That is the whole exercise, and it is one word, so spend the time you saved on
this: **try the same thing in `int_lin_le`.** Replace its `Pol(...)` with
`Rup()` and run

```
python3 -m kindling tight-sum --prove /tmp/t --check
python3 -m kindling too-small --prove /tmp/t --check
```

One of those still verifies and the other does not. Work out why before moving
on — the answer is the reason the next two exercises are harder than this one,
and it is a property of how integers are encoded rather than anything about
tables or sums.

## Exercise 2: negative coefficients

`int_lin_le` justifies a bound with cutting planes: take the row that says what
the constraint is, and add to it one *channelling* row per term — the row tying
that variable's bits to the order atom naming its bound. Every bit cancels, and
what is left is the clause we wanted.

The reference handles positive coefficients. A negative one needs the same sum
with one thing changed, because a term that counts downwards needs its variable
bounded from the other side. Look at `channelling`, and at the two rows any
variable has in the `.opb`:

```
@x1ge3_up 4 x1b2 2 x1b1 1 x1b0 3 ~x1ge3 >= 3 ;
@x1ge3_dn 4 ~x1b2 2 ~x1b1 1 ~x1b0 5 x1ge3 >= 5 ;
```

Make `over-budget` verify. Getting it wrong gives `REJECTED` rather than
`UNDER ASSERTIONS`, so you will know.

## Exercise 3: the Hall violator

`all_different_int` only ever fails — it never removes a value — and it fails
when it finds a set of variables with fewer values between them than there are
variables. That argument does not work by unit propagation. It needs adding
rows up.

Write `hall_steps` in `kindling/constraints/all_different_int.py`, and swap the
`Assert` in `propagate` for `Pol(self.hall_steps(variables, values))`.

The rows you have to work with, for a set `S` of variables and the set `U` of
values they are stuck inside:

* `@amo{c}_{v}` — for each value, at most one of these variables takes it.
* `@atleast{i}` — each variable takes at least one value. Derived in the
  proof's preamble rather than asserted in the `.opb`, since it is a
  consequence of what the atoms mean rather than something the model says.

Add up the at-most-one rows for the values in `U`, then the at-least-one rows
for the variables in `S`, and see what cancels. `pol` is reverse Polish, so
`@a @b + @c +` means add `b` to `a`, then add `c` to that.

You will also need `w`, which weakens a row by dropping a term: `@a x3eq1 w`.
Work out what needs dropping and why. (It turns out the checker will accept
the proof without it — try that too, and think about what the row you derived
actually says in each case.)

Make `pigeonhole` and `squeeze` verify.

## The bug hunt

Now the point of all this. `--bug` breaks a propagator on purpose:

```
python3 -m kindling puzzle --bug table-forgets-a-tuple --prove /tmp/p --check
```

`puzzle` has exactly one solution, sitting on the edge of all three
constraints. Run each of the four bugs against `puzzle`, `latin`, `tight-sum`
and `over-budget`, and fill in what happens. Some of it is not what you would
guess:

* Three of the bugs make the solver *lose the only solution* and report that
  there is none. That is a wrong answer, and the checker rejects the proof of
  it. No test of the answer alone would have caught this on an instance whose
  answer you did not already know.
* One of the bugs leaves the solver completely correct — right answer, every
  time — and only the derivation is wrong. Nothing about the search is broken.
  Nothing you could test for is broken. The proof still fails.
* And the one worth arguing about: run an unsound bug against an instance that
  really has no solution. The proof verifies. Think about why that is the
  correct behaviour rather than a hole.

## If you have more time

* `int_lin_le` refuses any coefficient other than `+1` and `-1`. Supporting a
  general one is one extra operation in the `pol` line. Which, and where?
* `justify.py` explains why every logged line is guarded by the conjunction of
  every guess, and what a real solver states instead. Making `table_int` state
  a proper reason is a small change with a measurable effect on proof size.
* `all_different` never prunes. Making it remove values as well as fail is a
  much bigger job — the propagation is standard, but what would the
  justification look like?
