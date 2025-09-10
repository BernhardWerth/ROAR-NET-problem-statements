
from .Solution import Solution
from .AddNeighbourhood import AddNeighbourhood

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


@final
class AddMove(SupportsApplyMove[Solution], SupportsLowerBoundIncrement[Solution]):
    """
    Represents a move that adds a city to the current tour in the construction phase.

    Attributes:
        neighbourhood (AddNeighbourhood): The neighbourhood this move belongs to.
        i (int): The last city in the current tour.
        j (int): The city to be added.
    """

    def __init__(self, neighbourhood: AddNeighbourhood, i: int, j: int):
        self.neighbourhood = neighbourhood
        # i and j are cities
        self.i = i
        self.j = j

    def apply_move(self, solution: Solution) -> Solution:
        assert solution.tour[-1] == self.i
        prob = solution.problem
        # Update lower bound
        solution.lb += prob.dist[self.i][self.j]
        if len(solution.not_visited) == 1:
            solution.lb += prob.dist[self.j][solution.tour[0]]
        # Tighter, but *not* better!
        # solution.lb += prob.dist[self.j][solution.tour[0]] - prob.dist[self.i][solution.tour[0]]
        # Update solution
        solution.tour.append(self.j)
        solution.not_visited.remove(self.j)
        return solution

    def lower_bound_increment(self, solution: Solution) -> float:
        assert solution.tour[-1] == self.i
        prob = solution.problem
        incr = prob.dist[self.i][self.j]
        if len(solution.not_visited) == 1:
            incr += prob.dist[self.j][solution.tour[0]]
        # Tighter, but *not* better!
        # incr += prob.dist[self.j][solution.tour[0]] - prob.dist[self.i][solution.tour[0]]
        return incr
