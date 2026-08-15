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

The failures to begin with are all in `tests/test_exercises.py`, one per
exercise, each naming what is still unjustified. Anything else failing means
the solver is broken rather than unfinished.

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

Everything the solver claims conditionally is written with an arrow.
`x1eq0 ==> 1 ~x2eq1 >= 1` is "if x1 = 0 then x2 is not 1", and it is one
pseudo-Boolean constraint and not two: VeriPB carries each literal on the left
of the arrow into the constraint negated, so what gets stored is the
`1 ~x1eq0 1 ~x2eq1 >= 1` you would otherwise have written out yourself. With
nothing on the right of it, `x1eq0 ==> >= 1` says that guess leads to a
contradiction — which is exactly what the line at the bottom of a dead node
needs to say, and `rup >= 1 ;` is that line with the last guess gone too.

Then look at `/tmp/ag.opb`, which says what the problem means. Most of it is
the encoding of the variables — every integer gets bits, a literal for each
`>= v`, and a literal for each `= v`, all written out in full.

There is a switch for leaving the propagators out of the proof altogether:

```
python3 -m kindling agreement --no-justifications --prove /tmp/ag --check
python3 -m kindling tight-sum --no-justifications --prove /tmp/t --check
```

The first still verifies. Everything the solver worked out, the checker worked
out again by itself, so a proof that never mentions any of it is still a proof.
The second does not verify, and `veripb --trace-failed /tmp/t.opb /tmp/t.pbp`
will show you how far the checker got before it ran out of things to propagate.
The gap between those two runs is what the rest of this is about.

## Exercise 1: table

`kindling/constraints/table_int.py` removes a value when no tuple can support
it any more, and asserts that it was allowed to. It is allowed to, and the
reason is reverse unit propagation: assume the value is still there, and the
selector literals fall over one at a time until the constraint saying *some*
tuple is in use is contradicted.

Replace the two `Assert(...)` with `Rup()`, and make `two-tables` verify.

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

`int_lin_le` justifies a bound with cutting planes: take `@lin{c}`, the
pseudo-Boolean constraint saying what the `int_lin_le` is, and add to it one
*channelling* constraint per term — the one tying that variable's bits to the
order literal naming its bound. Every bit cancels, and what is left is the
clause we wanted.

The reference handles positive coefficients. A negative one needs the same sum
with one thing changed, because a term that counts downwards needs its variable
bounded from the other side. Look at `channelling`, and at the two constraints
any variable has in the `.opb`:

```
@x1ge3_up 4 x1b2 2 x1b1 1 x1b0 3 ~x1ge3 >= 3 ;
@x1ge3_dn 4 ~x1b2 2 ~x1b1 1 ~x1b0 5 x1ge3 >= 5 ;
```

Those two are the arrow constraints

```
x1ge3 ==> 4 x1b2 2 x1b1 1 x1b0 >= 3
x1ge3 <== 4 x1b2 2 x1b1 1 x1b0 >= 3
```

spelled out the long way round, because VeriPB implements the arrow in proof
files but not in `.opb` files yet. Read them as the definitions they are: the
literal being true forces the bits up, and the bits being big enough forces
the literal. The `.opb` says so in a comment above every variable's block.

Make `over-budget` verify. Getting it wrong gives `REJECTED` rather than
`UNDER ASSERTIONS`, so you will know.

## Exercise 3: the Hall violator

`all_different_int` only ever fails — it never removes a value — and it fails
when it finds a set of variables with fewer values between them than there are
variables. That argument does not work by unit propagation. It needs adding
constraints up.

Write `hall_steps` in `kindling/constraints/all_different_int.py`, and swap the
`Assert` in `propagate` for `Pol(self.hall_steps(variables, values))`.

The constraints you have to work with, for a set `S` of variables and the set
`U` of values they are stuck inside:

* `@amo{c}_{v}` — for each value, at most one of these variables takes it.
* `@atleast{i}` — each variable takes at least one value. Derived in the
  proof's preamble rather than asserted in the `.opb`, since it is a
  consequence of what the literals mean rather than something the model says.

Add up the at-most-one constraints for the values in `U`, then the
at-least-one ones for the variables in `S`, and see what cancels. `pol` is
reverse Polish, so `@a @b + @c +` means add `b` to `a`, then add `c` to that.

You will also need `w`, which weakens a constraint by dropping a term:
`@a x3eq1 w`. Work out what needs dropping and why. (It turns out the checker
will accept the proof without it — try that too, and think about what the
constraint you derived actually says in each case.)

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
