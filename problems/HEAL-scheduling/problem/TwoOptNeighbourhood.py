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

from .TwoOptMove import TwoOptMove
from .Problem import Problem    
from .Solution import Solution
import math
from collections.abc import Iterable, Sequence
import random


@final
class TwoOptNeighbourhood(
    SupportsMoves[Solution, TwoOptMove],
    SupportsRandomMovesWithoutReplacement[Solution, TwoOptMove],
    SupportsRandomMove[Solution, TwoOptMove],
):
    """
    Local neighbourhood for TSP using 2-opt moves.

    Provides all possible, random, and random-without-replacement 2-opt moves
    for a feasible solution.
    """

    def __init__(self, problem: Problem):
        self.problem = problem

    def moves(self, solution: Solution) -> Iterable[TwoOptMove]:
        assert self.problem == solution.problem
        n = self.problem.n
        # This is only meant to be used as a local neighbourhood, so solution should be feasible
        assert solution.is_feasible
        for ix in range(1, n - 1):
            for jx in range(ix + 2, n + (ix != 1)):
                yield TwoOptMove(self, ix, jx)

    def random_moves_without_replacement(
        self, solution: Solution
    ) -> Iterable[TwoOptMove]:
        assert self.problem == solution.problem
        n = self.problem.n
        # This is only meant to be used as a local neighbourhood, so solution should be feasible
        assert solution.is_feasible
        # Sample integers at random and convert them into moves. To that
        # end, start by mapping x = 0, 1, ..., onto pairs (a, b) as shown
        # in the following table:
        #
        #    b  0   1   2   3   4   5
        #  a +------------------------
        #  0 |  -   -   -   -   -   -
        #  1 |  0   -   -   -   -   -
        #  2 |  1   2   -   -   -   -
        #  3 |  3   4   5   -   -   -
        #  4 |  6   7   8   9   -   -
        #  5 | 10  11  12  13  14   -
        #  6 | 15   …   …   …   …   …
        #
        # Note how x = a*(a-1)/2 + b.
        # To solve for a given x, rewrite the expression as
        # a**2 - a + 2*b - 2*x = 0, which has one positive root:
        # a = (1 + sqrt(1 + 8*x - 8*b) / 2
        # Taking a = floor((1 + sqrt(1 + 8*x)) / 2) and
        # b = x - a*(a-1)/2 allows both the desired jx = a + 2 and
        # ix = b + 1 to be obtained.
        # Note: since pair (1, n) would not be a valid 2-opt move, it can
        # be skipped or simply replaced by (n-2, n) when generated, which
        # saves one iteration.
        for x in sparse_fisher_yates_iter(n * (n - 3) // 2):
            jx = (1 + math.isqrt(1 + 8 * x)) // 2
            ix = x - jx * (jx - 1) // 2 + 1
            jx += 2
            # Handle special case
            if ix == 1 and jx == n:
                ix = n - 2
            yield TwoOptMove(self, ix, jx)

    def random_move(self, solution: Solution) -> Optional[TwoOptMove]:
        return next(iter(self.random_moves_without_replacement(solution)), None)


def sparse_fisher_yates_iter(n: int) -> Iterable[int]:
    """Yields a random permutation of range(n) using a sparse Fisher-Yates shuffle."""
    p: dict[int, int] = {}
    for i in range(n - 1, -1, -1):
        r = random.randrange(i + 1)
        yield p.get(r, r)
        if i != r:
            # p[r] = p.pop(i, i) # saves memory, takes time
            p[r] = p.get(i, i)  # lazy, but faster
