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

from .Solution import Solution
from .TwoOptNeighbourhood import TwoOptNeighbourhood    
@final
class TwoOptMove(
    SupportsApplyMove[Solution], SupportsObjectiveValueIncrement[Solution]
):
    """
    Represents a 2-opt move for local search in TSP.

    Attributes:
        neighbourhood (TwoOptNeighbourhood): The neighbourhood this move belongs to.
        ix (int): Start index of the segment to reverse.
        jx (int): End index of the segment to reverse.
    """

    def __init__(self, neighbourhood: TwoOptNeighbourhood, ix: int, jx: int):
        self.neighbourhood = neighbourhood
        # ix and jx are indices
        self.ix = ix
        self.jx = jx

    def apply_move(self, solution: Solution) -> Solution:
        prob = solution.problem
        n, ix, jx = prob.n, self.ix, self.jx
        # Update tour length
        t = solution.tour
        solution.lb -= prob.dist[t[ix - 1]][t[ix]] + prob.dist[t[jx - 1]][t[jx % n]]
        solution.lb += prob.dist[t[ix - 1]][t[jx - 1]] + prob.dist[t[ix]][t[jx % n]]
        # Update solution
        solution.tour[ix:jx] = solution.tour[ix:jx][::-1]
        return solution

    def objective_value_increment(self, solution: Solution) -> float:
        prob = solution.problem
        n, ix, jx = prob.n, self.ix, self.jx
        # Tour length increment
        t = solution.tour
        incr = prob.dist[t[ix - 1]][t[jx - 1]] + prob.dist[t[ix]][t[jx % n]]
        incr -= prob.dist[t[ix - 1]][t[ix]] + prob.dist[t[jx - 1]][t[jx % n]]
        return incr
