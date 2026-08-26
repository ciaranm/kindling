# Proofs shown on the slides

One `.opb` / `.pbp` pair per example, named after the stamp at the right of the
slide's footer, so that

    veripb <name>.opb <name>.pbp

runs what is on screen. The `.opb` files are duplicated rather than shared, so
that no example needs a second filename to be remembered on the day.

| name | slide | what `veripb` says |
| --- | --- | --- |
| `encoding` | That Is the Entire Encoding | `s VERIFIED UNSATISFIABLE` |
| `backtracking` | Backtracking Search | `s VERIFIED UNSATISFIABLE` |
| `not-rup` | Propagations Aren't Necessarily RUP | rejected at line 10 |
| `everything-rup` | Justifying Every Propagation | rejected at line 13 |
| `debugging` | Debugging a Failed Proof | rejected at line 13 |
| `assertions` | Assertions for Propagations | `s UNDER ASSERTIONS UNSATISFIABLE` |
| `table` | Justifying Table Constraint Inferences | `s VERIFIED NO CONCLUSION` |
| `linear` | Justifying Linear Inequalities | `s VERIFIED NO CONCLUSION` |
| `justified` | The Same Proof, With Nothing Asserted | `s VERIFIED UNSATISFIABLE` |

`debugging` is a copy of `everything-rup`, for

    veripb --trace-failed debugging.opb debugging.pbp

which prints the trail on that slide.

Everything except `table` and `linear` is the whole refutation of

    X1 in {0,1},  X2, X3, X4 in {0,1,2}
    X2 != X3, X2 != X4, X3 != X4     % encoding, backtracking
    all_different(X2, X3, X4)        % everything else
    X1 + X2 + X3 + X4 <= 2
    X2 + X3 + X4 <= 1 + X1

written by `kindling` with the propagators' justifications turned down to
whatever that slide is illustrating: on the `ash` branch, except for
`assertions`, which comes from `main`, where all-different still asserts and so
still writes the hint naming the set that would not fit. The two encodings differ
only in all-different: three pairwise constraints give nine two-variable
at-most-ones and number the inequalities `@lin4` and `@lin5`, and the global one
gives three three-variable at-most-ones and `@lin2` and `@lin3`.

`table` is one `table_int` over `x1 in 0..2`, `x2 in 0..3`, `x3 in 0..5` with
the three tuples on the slide, and `linear` is a bare `X1 + X2 + X3 <= 9` over
`0..7`; both `.pbp` files are the one inference on the slide, so they end in
`conclusion NONE`.
