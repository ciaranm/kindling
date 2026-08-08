% Three tasks that each need at least two, sharing a budget of at most five.
% The budget enters the sum with a negative coefficient, so its justification
% is the one that runs the other way round.
array[1..3] of var 0..7: task;
var 0..7: budget;
constraint sum(task) <= budget;
constraint budget <= 5;
constraint forall(i in 1..3) (task[i] >= 2);
solve satisfy;
