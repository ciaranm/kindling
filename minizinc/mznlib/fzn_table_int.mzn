% Also native, but the tuples arrive as a two-dimensional array and kindling
% wants them flat, so flatten them here rather than in the reader.
predicate kindling_table_int(array[int] of var int: x, array[int] of int: t);
predicate fzn_table_int(array[int] of var int: x, array[int, int] of int: t) =
    kindling_table_int(x, array1d(t));
