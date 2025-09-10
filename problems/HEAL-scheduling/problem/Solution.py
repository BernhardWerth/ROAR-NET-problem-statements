
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

from .Problem import Problem

@final
class Solution(SupportsCopySolution, SupportsObjectiveValue, SupportsLowerBound):
    """
    Represents a solution to the TSP problem.

    Attributes:
        problem (Problem): The associated TSP problem instance.
        tour (list[int]): The current tour (sequence of visited cities).
        not_visited (set[int]): Set of cities not yet visited.
        lb (int): The current lower bound (objective value).
    """

    def __init__(
        self, problem: Problem, tour: list[int], not_visited: set[int], lb: int
    ):
        self.problem = problem
        self.tour = tour
        self.not_visited = not_visited
        self.lb = lb

    def __str__(self) -> str:
        return " ".join(map(str, self.tour))

    @property
    def is_feasible(self) -> bool:
        """Check if the solution is feasible (all cities visited)."""
        return len(self.not_visited) == 0

    def to_textio(self, f: TextIO) -> None:
        """Write the solution to a text I/O stream `f` in TSPLIB format."""
        f.write(f"NAME : {self.problem.name}.tour\nTYPE : TOUR\n")
        f.write(f"DIMENSION : {self.problem.n}\nTOUR_SECTION\n")
        f.write("\n".join(map(lambda x: str(x + 1), self.tour)))
        f.write("\nEOF\n")

    def copy_solution(self) -> Self:
        return self.__class__(
            self.problem, self.tour.copy(), self.not_visited.copy(), self.lb
        )

    def objective_value(self) -> Optional[int]:
        if self.is_feasible:
            return self.lb
        return None

    def lower_bound(self) -> int:
        return self.lb
