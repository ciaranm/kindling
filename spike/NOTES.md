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
| `02-linear-neg` | the negative-coefficient case: identical recipe, other channelling row |
| `03-pigeonhole` | the whole refutation as two cutting-planes additions, no search |
| `04-table` | table support removal, which really is plain `rup` |
| `05-search` | an end-to-end two-node refutation, and the same proof with the propagators left as assertions |

## Findings

**The linear recipe.** One `pol`: the constraint row, plus one channelling row
per atom in the clause — one for each reason atom and one for the atom being
inferred — then `s`. Every bit cancels against its own negation, leaving only
the big-M coefficients, and saturation turns those into the clause. With
coefficients restricted to ±1 every row enters with multiplier 1, so the whole
derivation is `+` and `s`. A negative coefficient changes exactly one thing: the
reason is an upper bound, so its `_dn` row is added instead of its `_up` row.

**RUP sometimes works by accident, and that is a trap.** The claim "linear
inference is not RUP under a bits encoding" is true but not unconditionally. A
bound propagates a bit whenever the bound is large enough to force it: with a
3-bit variable, `x >= 5` forces the top bit, and then the constraint row can
cascade and unit propagation finds the conflict on its own. The inference is
only genuinely out of reach of RUP when no reason pins a bit, which needs
several reason variables and bounds that fall inside a power of two. Both
`01-linear` and `02-linear-neg` are built to be in that regime, and both ship
with a `-rup-only.pbp` that is expected to be rejected. **Instances for the
worked example and the exercises have to be chosen deliberately**, or a student
who tries `rup` first will find it works and the motivation for `pol` evaporates.
This is worth turning into a discussion point rather than hiding.

**The Hall violator, and the general idiom.** Summing the at-most-one rows for
the values in the violated set with the at-least-one rows for the variables in
it cancels every atom inside the set and leaves "one of these variables takes a
value outside this set". That row is unconditionally true, so it can be derived
without reference to the trail; it is the node's own logged inferences that make
it false. The pattern generalises and is the thing to teach: **`pol` derives
something true at the root, `rup` consumes it in context.** Students never have
to reason about decisions inside a `pol`.

**At-least-one is derived, not assumed.** `sum over v of x{i}eq{v} >= 1` is a
consequence of the direct-atom definitions, not an axiom, and summing the
`_dn` rows derives it in one `pol` — every order atom cancels against its own
negation and the telescope collapses. Cheap, honest, and it makes a good warm-up
because it is mechanical.

**Search scaffolding is tiny.** One `rup` per failed node, negating that node's
decisions, and one `rup >= 1` at the end. `05-search` is the whole thing, and it
stays honest even when every propagator is asserted.

**The assertion form works exactly as hoped.** `search-assertions.pbp` is
`search.pbp` with the four propagator justifications replaced by `a`, and the
scaffolding untouched. VeriPB reports `s UNDER ASSERTIONS UNSATISFIABLE` rather
than `s VERIFIED UNSATISFIABLE`. Each exercise turns one `a` into a real
derivation and nothing else moves. Assertions take annotations — `a <constraint>
: <antecedent ids> : <name> : <hints> ;` — so `a ... : : alldifferent_hall ;`
tags each one for the burn-down tool.

The stub for a *failure*-detecting propagator asserts the same unconditional
lemma the real derivation would produce, so the node `rup` stays honest either
way. That keeps the exercise shape uniform: the propagator always states the row
it wants, and the exercise is deriving it instead of asserting it.

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

## Two upstream bugs found

1. **Reification shorthands do not work in `.opb` files**, though
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

Until (1) is fixed the channelling rows are written as their big-M forms, with
the arrow form they stand for in a comment above each variable's block. The
arrow form in the `.pbp` normalises to exactly the same row: deriving the
`01-linear` clause entirely through arrow-introduced channelling rows gives the
identical result, and fails identically without the `pol`.
