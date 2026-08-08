% More pigeons than holes.  One Hall violator refutes it at the root, with no
% search at all, and the whole proof is a couple of cutting-planes additions.
include "globals.mzn";
int: pigeons = 4;
int: holes = 3;
array[1..pigeons] of var 0..holes-1: pigeon;
constraint all_different(pigeon);
solve satisfy;
