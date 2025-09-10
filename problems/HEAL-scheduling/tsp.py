#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: © 2025 Authors of the roar-net-api-py project <https://github.com/roar-net/roar-net-api-py/blob/main/AUTHORS>
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import logging
import math
import random
import sys
from collections.abc import Iterable, Sequence
from logging import getLogger
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
    SupportsRandomSolution,
)

log = getLogger(__name__)


class _SupportsLT(Protocol):
    def __lt__(self, other: Self) -> bool: ...


_T = TypeVar("_T", bound=_SupportsLT)


def argmin(seq: Sequence[_T]) -> int:
    """custom argmin??"""
    return min(range(len(seq)), key=seq.__getitem__)




@final

def generate_random_tsp_problem(n: int, name: str = "random") -> Problem:
    coords = [(i + 1, random.uniform(0, 100), random.uniform(0, 100)) for i in range(n)]
    dist = []
    for i in range(n):
        aux = []
        for j in range(n):
            aux.append(
                int(
                    0.5
                    + math.sqrt(
                        (coords[i][1] - coords[j][1]) ** 2
                        + (coords[i][2] - coords[j][2]) ** 2
                    )
                )
            )
        dist.append(tuple(aux))
    return Problem(tuple(dist), name)

if __name__ == "__main__":
    import roar_net_api.algorithms as alg
    print("This is the TSP problem module. Running a demo...")
    logging.basicConfig(
        stream=sys.stderr, level="INFO", format="%(levelname)s;%(asctime)s;%(message)s"
    )

    # instance_file = r"D:\Projekte\ROAR-NET\ROAR-NET-problem-statements\problems\HEAL-scheduling\tsp\berlin52.tsp"
    # with open(instance_file, "r", encoding="utf-8") as f:
    #     problem1 = Problem.from_textio(f)
    # print("This is tafter load")


    problem1 = generate_random_tsp_problem(10)
    # Run greedy construction to get an initial solution
    solution1 = alg.greedy_construction(problem1)
    # solution = alg.beam_search(problem, bw=10)
    # solution = alg.grasp(problem, 30.0)
    log.info(
        "Objective value after constructive search: %s", solution1.objective_value()
    )

    # Run simulated annealing to improve the previous solution
    solution2 = alg.sa(problem1, solution1, 10.0, 30.0)
    # solution = alg.rls(problem, solution, 10.0)
    # solution = alg.best_improvement(problem, solution)
    # solution = alg.first_improvement(problem, solution)
    log.info("Objective value after local search: %s", solution2.objective_value())

    # Print the final solution to stdout
    solution2.to_textio(sys.stdout)
