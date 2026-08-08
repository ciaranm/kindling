% A table that insists two variables agree and an all_different that insists
% they differ.  Neither propagator sees it at the root; it takes two nodes.
include "globals.mzn";
array[1..2] of var 0..1: x;
constraint table(x, [| 0, 0 | 1, 1 |]);
constraint all_different(x);
solve satisfy;
