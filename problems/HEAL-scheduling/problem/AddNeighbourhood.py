from typing import Optional, Protocol, Self, TextIO, TypeVar, final
from roar_net_api.operations import (
    SupportsApplyMove,
    SupportsConstructionNeighbourhood,
    SupportsCopySolution,
    SupportsEmptySolution,
    SupportsLocalNeighbourhood,
    SupportsLowerBound,
    SupportsLowerBoundIncrement,
    SupportsMoves,
    SupportsObjectiveValue,
    SupportsObjectiveValueIncrement,
    SupportsRandomMove,
    SupportsRandomMovesWithoutReplacement,
    SupportsRandomSolution)

from .AddMove import AddMove
from .Problem import Problem
from .Solution import Solution
from collections.abc import Iterable, Sequence

@final
class AddNeighbourhood(SupportsMoves[Solution, AddMove]):
    """
    Construction neighbourhood for TSP.

    Generates all possible AddMove moves for the current partial solution.
    """

    def __init__(self, problem: Problem):
        self.problem = problem

    def moves(self, solution: Solution) -> Iterable[AddMove]:
        assert self.problem == solution.problem
        i = solution.tour[-1]
        for j in solution.not_visited:
            yield AddMove(self, i, j)