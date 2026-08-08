% A satisfiable one, so the solver is not only ever saying no.
include "globals.mzn";
int: n = 4;
array[1..n, 1..n] of var 0..n-1: square;
constraint forall(i in 1..n) (all_different([square[i, j] | j in 1..n]));
constraint forall(j in 1..n) (all_different([square[i, j] | i in 1..n]));
solve satisfy;
