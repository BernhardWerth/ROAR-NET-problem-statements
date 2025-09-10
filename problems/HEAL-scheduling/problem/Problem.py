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
from .AddNeighbourhood import AddNeighbourhood
from .TwoOptNeighbourhood import TwoOptNeighbourhood


class Problem(
    SupportsConstructionNeighbourhood[AddNeighbourhood],
    SupportsLocalNeighbourhood[TwoOptNeighbourhood],
    SupportsEmptySolution[Solution],
    SupportsRandomSolution[Solution],
):
    """
    Symmetric Traveling Salesman Problem (TSP) instance.

    Attributes:
        dist (tuple[tuple[int, ...], ...]): Distance matrix between cities.
        name (str): Name of the problem instance.
        n (int): Number of cities.
    """

    def __init__(self, dist: tuple[tuple[int, ...], ...], name: str):
        self.dist = tuple(tuple(t) for t in dist)
        self.name = name
        self.n = len(self.dist)
        self.c_nbhood: Optional[AddNeighbourhood] = None
        self.l_nbhood: Optional[TwoOptNeighbourhood] = None

    def __str__(self) -> str:
        out: list[str] = []
        for row in self.dist:
            out.append(" ".join(map(str, row)))
        return "\n".join(out)

    def construction_neighbourhood(self) -> AddNeighbourhood:
        if self.c_nbhood is None:
            self.c_nbhood = AddNeighbourhood(self)
        return self.c_nbhood

    def local_neighbourhood(self) -> TwoOptNeighbourhood:
        if self.l_nbhood is None:
            self.l_nbhood = TwoOptNeighbourhood(self)
        return self.l_nbhood

    @classmethod
    def from_textio(cls, f: TextIO) -> Self:
        """
        Create a problem from a text I/O source `f` in TSPLIB format
        """
        s = f.readline().strip()
        n = None
        dt = None
        name = "unnamed"
        print("This is in load")
        while s != ("NODE_COORD_SECTION", ""):
            line = s.split(":", 1)
            k = line[0].strip()
            if k == "DIMENSION":
                n = int(line[1])
            elif k == "EDGE_WEIGHT_TYPE":
                dt = line[1].strip()
            elif k == "NAME":
                name = line[1].strip()
            s = f.readline().strip()
        if n is not None and dt == "EUC_2D":
            kxy: list[tuple[float, ...]] = []
            for i in range(n):
                kxy.append(tuple(map(float, f.readline().split())))
            kxy = sorted(kxy)
            dist: list[tuple[int, ...]] = []
            for i in range(n):
                if kxy[i][0] != i + 1:
                    raise ValueError("Invalid instance")
                aux: list[int] = []
                for j in range(n):
                    aux.append(
                        int(
                            0.5
                            + math.sqrt(
                                (kxy[i][1] - kxy[j][1]) ** 2
                                + (kxy[i][2] - kxy[j][2]) ** 2
                            )
                        )
                    )
                dist.append(tuple(aux))
            return cls(tuple(dist), name)
        raise ValueError(f"Instance format {dt} not supported")

    def empty_solution(self) -> Solution:
        return Solution(self, [0], set(range(1, self.n)), 0)

    def random_solution(self) -> Solution:
        c = list(range(1, self.n))
        random.shuffle(c)
        c.insert(0, 0)
        obj = self.dist[c[-1]][c[0]]
        for ix in range(1, self.n):
            obj += self.dist[c[ix - 1]][c[ix]]
        return Solution(self, c, set(), obj)

