# Draft issue for VeriPB — not yet filed

Written against `main` @ `f8c29244`, checked with the `veripb 3.0.2` binary.
Intended to be actionable enough for a first implementation pass.

---

## Title

Reification shorthands (`==>` / `<==`) are documented for OPB files but only implemented for proof files

## Summary

`proof_format_overview.md` documents reification shorthands as an OPB extension
and says they "can be used anywhere an OPB-style constraint is expected". They
work in `.pbp` files but are rejected in `.opb` files — the example given in the
documentation fails verbatim. The `.opb` and `.pbp` paths have separate lexers
and only the `.pbp` one learned the syntax.

## Reproduction

`doc.opb` — the example from `proof_format_overview.md` § Reification
Shorthands, copied verbatim:

```
z1 z2 ~z3 ==> +1 x1 +2 x2 >= 2;
```

`doc.pbp`:

```
pseudo-Boolean proof version 3.0
output NONE;
conclusion NONE;
end pseudo-Boolean proof;
```

```
$ veripb doc.opb doc.pbp
Running VeriPB version 3.0.2
Error: Unexpected token starting at doc.opb:1:1! Expected '*', 'min:', 'preserved:', '>=', '<=', '=', or integer!
```

The identical constraint is accepted in the proof file:

```
pseudo-Boolean proof version 3.0
@r a z1 z2 ~z3 ==> +1 x1 +2 x2 >= 2 ;
output NONE;
conclusion NONE;
end pseudo-Boolean proof;
```

```
$ veripb trivial.opb arrow.pbp
s UNDER ASSERTIONS NO CONCLUSION
```

## Where the gap is

- `veripb-parser/src/opb_token.rs:8-56` — `OPBToken` has no token for `==>` or
  `<==`. The `.pbp` lexer has both, as `Token::RightImplication` and
  `Token::LeftImplication` (`veripb-parser/src/pbp_parser/utils.rs:67-68`,
  lexed at `lexer.rs:484-524`).
- `veripb-parser/src/opb_parser.rs:68-180` — the per-line dispatch in
  `parse_opb_from_file_given_var_manager` matches on `Comment`, `Label`,
  `Minimize`, `Maximize`, `Preserved`, `Integer`, `GreaterEqual`, `LessEqual`
  and `Equal`. There is no arm for a line beginning with a literal, which is
  what a reified constraint starts with, hence the error above.

## Suggested fix

The semantics are already settled by the proof-file path, so this should be
wiring rather than design. The conversion from (literals, operator, terms,
direction) to PB constraints is
`Parser::generate_constraints` at
`veripb-parser/src/pbp_parser/parser.rs:1013-1091`. It already handles both
directions and all three operators.

1. Add `RightImplication` / `LeftImplication` tokens to `OPBToken`.
2. Add a dispatch arm for a line starting with `Var` or `Negation`: collect the
   antecedent literals up to the arrow, then parse the consequent with the
   existing constraint machinery.
3. Reuse `generate_constraints` rather than reimplementing the big-M
   construction. The main structural decision is that it is currently a method
   on the `.pbp` `Parser` while the OPB parser is line-based with a fresh
   `logos` lexer per line, so it likely wants extracting to a free function over
   `GenericTerms`.

Things the OPB path needs to preserve, since the `.pbp` path enforces them:

- `<==` takes exactly one literal on the left; `==>` takes one or more.
- Overflow safety is checked before generation via
  `GenericTerms::is_overflow_safe` (`utils.rs:240-291`); the OPB path should do
  the same rather than trusting the input.
- A reified equality generates two constraints. That interacts with the existing
  rule that equality constraints cannot be labelled in the OPB — the check at
  `opb_parser.rs:115-122` already rejects a label on anything producing a
  constraint pair, so a labelled reified equality should fall out correctly, but
  it is worth a test.
- Reified constraints must count correctly toward the `#constraint=` header.

## Test coverage

No `.opb` file in `tests/` uses the syntax — `grep -rl '==>\|<==' --include=*.opb tests/`
returns nothing. The `tests/instances/correct/version3/implication_*.opb` files
are empty shells with all the syntax in the matching `.pbp`, which is presumably
how the gap went unnoticed. Worth adding `.opb`-side counterparts, including a
labelled reified constraint and a reified equality.

## Two smaller things noticed nearby

**`docs/grammar.tex` describes the `==>` antecedent as a disjunction.** The
3.0 changes list says "the right implication is a (non-empty) disjuction of
literals". It is a conjunction — as `proof_format_overview.md` says, as the
CHANGELOG entry "Fix right implication is conjunction of literals" implies, and
as the implementation does. Given `z1 z2 ==> 1 x1 >= 1`, the clause
`1 ~z1 1 x1 >= 1` is not RUP-implied but `1 ~z1 1 ~z2 1 x1 >= 1` is. A
disjunctive antecedent could not be a single PB constraint in any case.

**`veripb-parser/src/pbp_parser/utils.rs:191` has a botched `Display` arm:**

```rust
Token::RightImplication => write!(f, "`==>`write!(f,"),
```

so any parse error mentioning `==>` prints the fragment of a nearby line.

## Note on normalisation

If there is a concern about reopening the normalisation problems that made this
unpopular in VeriPB 2: the proof-file path already produces the natural form.
For `x1ge4 ==> 4 x1b2 2 x1b1 1 x1b0 >= 4` it yields exactly
`4 x1b2 2 x1b1 1 x1b0 4 ~x1ge4 >= 4`, i.e. the antecedent's negation carried at
the degree as coefficient — which is what `generate_constraints` does at
`parser.rs:1036-1043`. Deriving a clause through arrow-introduced constraints
and through hand-written big-M ones gives identical results. Adding the same
code path to the OPB parser should not introduce a new normalisation question.

## Why this matters to us

We are building a small certifying constraint solver for teaching. Its OPB file
is the first thing a student reads, and it is almost entirely channelling
constraints between an integer's bit representation and its order literals —
that is, reified constraints, several per variable per value. In arrow form
they read as the definitions they are; in big-M form they need a comment
explaining what they mean. It is a workaround rather than a blocker, but the
readability gap is the whole difference for the audience.
