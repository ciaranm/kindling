# Stage 0: what the proofs actually have to look like

Hand-written `.opb`/`.pbp` pairs, checked against VeriPB 3.0.2, written before
any solver exists so that the encoding and the derivation shapes are settled
against the real checker rather than against my expectations. `python3 check.py`
regenerates the `.opb` files and checks every proof, including the ones that are
supposed to be rejected.

## The examples

| | what it pins down |
|---|---|
| `01-linear` | a linear bound inference as one `pol`, plus the same thing as a bare `rup`, which fails |
| `02-linear-neg` | the negative-coefficient case: identical recipe, other channelling constraint |
| `03-pigeonhole` | the whole refutation as two cutting-planes additions, no search |
| `04-table` | table support removal, which really is plain `rup` |
| `05-search` | an end-to-end two-node refutation, and the same proof with the propagators left as assertions |

## Findings

**The linear recipe.** One `pol`: `@lin{c}`, which is what the model said,
plus one channelling constraint per literal in the clause — one for each
reason literal and one for the literal being inferred — then `s`. Every bit
cancels against its own negation, leaving only the big-M coefficients, and
saturation turns those into the clause. With coefficients restricted to ±1
everything enters the sum with multiplier 1, so the whole derivation is `+` and
`s`. A negative coefficient changes exactly one thing: the reason is an upper
bound, so the `_dn` constraint is added instead of the `_up` one.

**RUP sometimes works by accident, and that is a trap.** The claim "linear
inference is not RUP under a bits encoding" is true but not unconditionally. A
bound propagates a bit whenever the bound is large enough to force it: with a
3-bit variable, `x >= 5` forces the top bit, and then `@lin{c}` can cascade and
unit propagation finds the conflict on its own. The inference is only genuinely
out of reach of RUP when no reason pins a bit, which needs several reason
variables and bounds that fall inside a power of two. Both
`01-linear` and `02-linear-neg` are built to be in that regime, and both ship
with a `-rup-only.pbp` that is expected to be rejected. **Instances for the
worked example and the exercises have to be chosen deliberately**, or a student
who tries `rup` first will find it works and the motivation for `pol` evaporates.
This is worth turning into a discussion point rather than hiding.

**The Hall violator, and the general idiom.** Summing the at-most-one
constraints for the values in the violated set with the at-least-one ones for
the variables in it cancels every literal inside the set and leaves "one of
these variables takes a value outside this set". That is unconditionally true,
so it can be derived without reference to the trail; it is the node's own
logged inferences that make it false. The pattern generalises and is the thing
to teach: **`pol` derives something true at the root, `rup` consumes it in
context.** Students never have to reason about decisions inside a `pol`.

**At-least-one is derived, not assumed.** `sum over v of x{i}eq{v} >= 1` is a
consequence of the direct literals' definitions, not an axiom, and summing
the `_dn` constraints derives it in one `pol` — every order literal cancels
against its own negation and the telescope collapses. Cheap, honest, and it
makes a good warm-up because it is mechanical.

**Search scaffolding is tiny.** One `rup` per failed node, saying that node's
decisions lead to a contradiction, and one `rup >= 1` at the end. `05-search` is
the whole thing, and it stays honest even when every propagator is asserted.

**Everything conditional is written with an arrow.** Every line either a
propagator or the search contributes is of the form "if these literals hold
then that", and `guesses ==> consequent` says so where `1 ~guess ... >= 1` made
the reader normalise it in their head. The two forms are the same constraint —
`generate_constraints` carries each antecedent's negation at the degree, and
with a clause the degree is one — so this is presentation and nothing else, and
`01-linear` fails identically in either notation without its `pol`. A backtrack
constraint is the case with nothing on the right: `x1eq0 ==> >= 1` is "that
decision cannot hold", and the root's version of it, with nothing on the left
either, is the line that closes the proof.

**The assertion form works exactly as hoped.** `search-assertions.pbp` is
`search.pbp` with the four propagator justifications replaced by `a`, and the
scaffolding untouched. VeriPB reports `s UNDER ASSERTIONS UNSATISFIABLE` rather
than `s VERIFIED UNSATISFIABLE`. Each exercise turns one `a` into a real
derivation and nothing else moves. Assertions take annotations — `a <constraint>
: <antecedent ids> : <name> : <hints> ;` — so `a ... : : alldifferent_hall ;`
tags each one for the burn-down tool.

The stub for a *failure*-detecting propagator asserts the same unconditional
lemma the real derivation would produce, so the node `rup` stays honest either
way. That keeps the exercise shape uniform: the propagator always states the
constraint it wants, and the exercise is deriving it instead of asserting it.

## VeriPB syntax, as found

- Comments are `*` in `.opb` and `%` in `.pbp`. They are not interchangeable.
- Labels (`@name`) work in both files. Equality constraints cannot be labelled
  in the `.opb`, so write two inequalities.
- `pol` is reverse Polish: `pol @a @b + @c + s ;`.
- Variable names must be at least two characters, must start with a letter or
  `_`, and may then contain `a-zA-Z0-9_-^[]{}`. `-` is legal, so `x1eq-3` parses,
  but it reads like subtraction — another reason for non-negative domains.
- `conclusion UNSAT;` needs no explicit contradiction reference.
- `rup >= 1 ;` — an empty sum — is how you close the proof.
- The `* #variable= ... #constraint= ...` line older pseudo-Boolean tooling
  wants at the top of an `.opb` is not needed: veripb 3 reads the file without
  it. The `f` rule survives, but only as an optional check that the expected
  number of constraints was loaded, and since nothing here ever refers to a
  constraint by number there is nothing for it to protect. So the first line
  of a `.pbp` after the version is whatever you wanted to derive first.
- `g1 g2 ==> 1 xx >= 1` works in a `.pbp` in every position we need: after `rup`,
  after `a` (annotations and all, `a g1 ==> >= 1 : : name ;`), and with a
  labelled result. The antecedent may be negated (`~x3ge5`), and the consequent
  may be empty, which is how a contradiction is stated conditionally.

## Two upstream bugs found

1. **Reification shorthands do not work in `.opb` files** — *fixed upstream on
   2026-08-20, VeriPB `main` `89281e15`; kindling's `.opb` uses the arrows now.*
   Though
   `proof_format_overview.md` says they "can be used anywhere an OPB-style
   constraint is expected". The doc's own example, `z1 z2 ~z3 ==> +1 x1 +2 x2 >= 2;`,
   is rejected verbatim in a `.opb` and accepted in a `.pbp`. `OPBToken` has no
   arrow token and the OPB line dispatcher has no arm for a leading literal;
   the `.pbp` has a separate lexer that does. Confirmed on `main` (f8c29244).
2. **`docs/grammar.tex` describes the `==>` antecedent as a "disjunction of
   literals"**. It is a conjunction, as `proof_format_overview.md` says, as the
   CHANGELOG's "Fix right implication is conjunction of literals" implies, and as
   the implementation does: given `z1 z2 ==> 1 x1 >= 1`, the clause `~z1 x1` is
   not implied but `~z1 ~z2 x1` is. A disjunctive antecedent could not be one PB
   constraint anyway.

The spike's own files keep the big-M forms, which is what they were checked
with; the solver writes the arrows. Nothing is lost by either choice, because
the arrow normalises to exactly the same constraint: deriving the `01-linear`
clause entirely through arrow-introduced channelling constraints gives the
identical result, and fails identically without the `pol`. The split was never
between two notations, only between two files, and it has now closed.
