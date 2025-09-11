from __future__ import annotations

import json
import random
import time
from typing import List, TextIO, Optional
from collections.abc import Iterable
from enum import Enum
import numpy as np
import roar_net_api.algorithms as alg
from sortedcontainers import SortedSet




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


class StackingState:
    """
    Represents the current state of the stacks in the warehouse.
    """

    def __init__(self, stacks, problem, time=0, sorted_dues=None):
        """
        Initializes the StackingState with given stacks, maximum height, warehouse height, and handover time.
        """
        self.stacks = stacks  # list to hold stacks and their blocks
        self.handover_ready_time = time  # Time until the handover stack is ready
        self.current_time = time
        self.overdue_sqr = 0
        self.problem = problem
        self.block_lookup = {
            block: (stack_index, height)
            for stack_index, stack in enumerate(stacks)
            for height, block in enumerate(stack)
        }  # quick lookup for blocks in stacks
        self.move_durations = {b: self.calc_remove_dur(b) for s in stacks for b in s}
        if sorted_dues is None:
            self.sorted_dues = SortedSet(
                enumerate(problem.due_dates), key=lambda x: x[1]
            )
        else:
            self.sorted_dues = SortedSet(sorted_dues, key=lambda x: x[1])

    def calc_remove_dur(self, b):
        return self.get_relocation_duration(
            self.block_lookup[b][0],
            self.problem.handover_stack,
            self.block_lookup[b][1],
            0,
        )

    def apply_relocation(self, from_stack, to_stack, try_mode = False)-> bool:
        """
        Moves a block from one stack to another.

        :param from_stack: The stack to move the block from.
        :param to_stack: The stack to move the block to.
        """
        # Underflow check: from_stack must not be empty
        if not self.stacks[from_stack] or len(self.stacks[from_stack]) == 0:
            if try_mode:
                return False 
            else: 
                raise ValueError(f"Cannot move block: stack {from_stack} is empty.")

        if to_stack is not self.problem.handover_stack:
            # Index bounds check
            if (
                from_stack < 0
                or to_stack < 0
                or from_stack >= len(self.stacks)
                or to_stack >= len(self.stacks)
            ):
                if try_mode:
                    return False 
                else: 
                    raise ValueError(f"Stack index out of bounds: from_stack {from_stack}, to_stack {to_stack}.")
            # Overflow check: to_stack must not exceed its maximum height
            if len(self.stacks[to_stack]) + 1 > self.problem.max_height[to_stack]:
                if try_mode:
                    return False 
                else: 
                    raise ValueError(f"Cannot move block: stack {to_stack} will exceed max height.")

        # Update current time based on the move
        self.current_time = self.determine_time(from_stack, to_stack)

        block = self.stacks[from_stack].pop()
        if to_stack is not self.problem.handover_stack:
            self.stacks[to_stack].append(block)
            self.block_lookup[block] = (to_stack, len(self.stacks[to_stack]) - 1)
            self.move_durations[block] = self.calc_remove_dur(block)
        else:
            self.handover_ready_time = self.current_time + self.problem.handover_time
            ot = self.current_time - self.problem.due_dates[block]
            self.overdue_sqr += weigh_if_positive(ot)
            self.block_lookup.pop(block)
            self.move_durations.pop(block)
            self.sorted_dues.remove((block, self.problem.due_dates[block]))

    def determine_time(self, from_stack, to_stack):
        dur = self.__move_time(from_stack, to_stack)
        delta = 0
        if to_stack is self.problem.handover_stack:
            delta = self.handover_ready_time - dur - self.current_time
            if delta < 0:
                delta = 0
        return self.current_time + dur + delta

    def is_empty(self):
        """
        Checks if all stacks are empty.

        :return: True if all stacks are empty, False otherwise.
        """
        return all(len(stack) == 0 for stack in self.stacks)

    def __move_time(self, from_stack, to_stack):
        """
        Calculates the time required to move a block from one stack to another.

        :param from_stack: The stack to move the block from.
        :param to_stack: The stack to move the block to.
        :return: The time taken to move the block.
        """

        from_height = (
            len(self.stacks[from_stack]) - 1
        )  # Current height of the from_stack
        to_height = len(self.stacks[to_stack])  # Current height of the to_stack

        # Vertical distance: move from current height to max_height, then down to the target height
        return self.get_relocation_duration(
            from_stack, to_stack, from_height, to_height
        )

    def get_relocation_duration(self, from_pos, to_pos, from_height, to_height):
        horizontal_distance = abs(from_pos - to_pos)
        vertical_distance = (self.problem.crane_height - from_height) + (
            self.problem.crane_height - to_height
        )
        return (horizontal_distance / self.problem.horizontal_speed) + (
            vertical_distance / self.problem.vertical_speed
        )

    def copy(self):
        """
        Creates a deep copy of the current StackingState.

        :return: A new instance of StackingState with the same attributes.
        """
        new_state = StackingState(
            [stack.copy() for stack in self.stacks],
            self.problem,
            self.current_time,
            self.sorted_dues,
        )
        new_state.handover_ready_time = self.handover_ready_time
        new_state.overdue_sqr = self.overdue_sqr
        return new_state

    def __repr__(self):
        return f"StackingState(time={self.current_time}, handover_ready={self.handover_ready_time}, stacks={self.stacks}, overdue={self.overdue_sqr})"

def weigh_if_positive(x):
    return x if x > 0 else 0.000001 * x

class StackingSolution(SupportsCopySolution, SupportsObjectiveValue, SupportsLowerBound):
    """
    Represents a solution to the stacking scheduling problem.
    Attributes:
        state (StackingState): The current state of the stacking problem.
        problem: The problem instance containing relevant parameters and data.
        relocations (List[tuple], optional): A list of relocations performed to reach the current state.
    Methods:
        is_feasible():
            Checks if the current solution is feasible, i.e., if the state is empty.
        objective_value():
            Returns the objective value of the solution if feasible, calculated as the square root of the state's overdue squared value.
            Returns None if the solution is not feasible.
        lower_bound():
            Computes a lower bound on the objective value, considering both the current overdue squared value and lingering overdue for remaining blocks.
    """

    def __init__(self, state: StackingState, problem, relocations: List[tuple] = None):
        self.state = state
        self.problem = problem
        self.relocations = relocations if relocations else []
        self.lower_bound_cache = None

    def is_feasible(self):
        return self.state.is_empty()

    def objective_value(self):
        if not self.is_feasible():
            return None
        return self.lower_bound()

    def lower_bound(self):
        """Compute a lower bound on the objective value by assuming each block takes the lowest possible time to be relocated."""
        if self.lower_bound_cache is not None:
            return self.lower_bound_cache
        time = self.state.current_time
        forward = 0
        minmove = (
            min(self.state.move_durations.values())
            if len(self.state.move_durations) > 0
            else 0
        )
        handover_time = self.problem.handover_time
        for _, due in self.state.sorted_dues:
            relocation_duration = max(minmove, handover_time)
            time += relocation_duration
            forward += weigh_if_positive(time - due)
        self.lower_bound_cache = (
            self.state.overdue_sqr + forward
        )  # at least one move per block remaining
        return self.lower_bound_cache

    def __repr__(self):
        return f"Solution(feasible={self.is_feasible()}, objval={self.objective_value()}, lb={self.lower_bound()}, moves={len(self.relocations)},state={self.state})"

    def copy_solution(self):
        copy_solution = StackingSolution(
            self.state.copy(), self.problem, self.relocations.copy()
        )
        copy_solution.lower_bound_cache = self.lower_bound_cache
        return copy_solution

    def to_textio(self, f: TextIO) -> None:
        """Write the solution to a text I/O stream `f` in JSON format."""
        data = {
            "problem": getattr(self.problem, "name", None),
            "relocations": [list(r) for r in self.relocations],  # tuples -> lists for JSON
        }
        json.dump(data, f, ensure_ascii=False)
        f.write("\n")

    def __str__(self):
        return f"Solution(feasible={self.is_feasible()}, objval={self.objective_value()}, lb={self.lower_bound()}, moves={len(self.relocations)},state={self.state})"

class AddRelocationMove(
    SupportsApplyMove[StackingSolution],
    SupportsLowerBoundIncrement[StackingSolution],
    SupportsObjectiveValueIncrement[StackingSolution],
):
    def __init__(
        self, neihghbourhood: AddRelocationNeighbourhood, from_stack: int, to_stack: int
    ):
        self.neihghbourhood = neihghbourhood
        self.from_stack = from_stack
        self.to_stack = to_stack

    def try_apply_move(self, solution: StackingSolution) -> bool:
        if not solution.state.apply_relocation(self.from_stack, self.to_stack, try_mode=True):
            return False
        solution.relocations.append((self.from_stack, self.to_stack))
        solution.lower_bound_cache = None
        return True

    def apply_move(self, solution: StackingSolution) -> StackingSolution:
        solution.state.apply_relocation(self.from_stack, self.to_stack)
        solution.relocations.append((self.from_stack, self.to_stack))
        solution.lower_bound_cache = None
        return solution

    def objective_value_increment(self, solution: StackingSolution) -> float:
        return self.lower_bound_increment(solution)

    def lower_bound_increment(self, solution: StackingSolution) -> float:
        # todo this is not a valid incremental update, but a full recomputation
        nextstate = solution.copy_solution()
        self.apply_move(nextstate)
        return nextstate.lower_bound() - solution.lower_bound()

    def __repr__(self):
        return (
            f"AddRelocationMove(from_stack={self.from_stack}, to_stack={self.to_stack})"
        )

class AddRelocationNeighbourhood(SupportsMoves[StackingSolution, AddRelocationMove]):
    def __init__(self, problem):
        self.problem = problem

    def moves(self, solution: StackingSolution, only_handover=False):
        for from_stack,_ in enumerate(solution.state.stacks):
            if len(solution.state.stacks[from_stack]) == 0:
                continue
            if from_stack is self.problem.handover_stack:
                continue
            for to_stack,_ in enumerate(solution.state.stacks) if not only_handover else [(self.problem.handover_stack,_)]:
                if from_stack == to_stack:
                    continue
                if (to_stack is not self.problem.handover_stack
                    and len(solution.state.stacks[to_stack])
                    >= self.problem.max_height[to_stack]
                ):
                    continue
                yield AddRelocationMove(self, from_stack, to_stack)

class ChangeAndRepairMoveType(Enum):
    INSERT = 1
    REMOVE = 2
    SWITCH = 3

class ChangeAndRepairMove(SupportsApplyMove[StackingSolution], SupportsObjectiveValueIncrement[StackingSolution]):
    def __init__(
        self,
        neihghbourhood: ChangeAndRepairNeighborhood,
        move_type: ChangeAndRepairMoveType,
        move_index: int,
        from_stack: int=0,
        to_stack: int=0,
        swich_index: int = 0,
    ):
        self.neihghbourhood = neihghbourhood
        self.move_type = move_type
        self.move_index = move_index
        self.from_stack = from_stack
        self.to_stack = to_stack
        self.swich_index = swich_index

    def apply_move(self, solution: StackingSolution) -> StackingSolution:
        empty_solution = solution.problem.empty_solution()
        c_nbhood = solution.problem.construction_neighbourhood()

        switchMove = solution.relocations[self.swich_index]

        for i, (f, t) in enumerate(solution.relocations):
            if self.move_type == ChangeAndRepairMoveType.INSERT and i == self.move_index:
                if not AddRelocationMove(c_nbhood, self.from_stack, self.to_stack).try_apply_move(empty_solution):
                    break
            elif self.move_type == ChangeAndRepairMoveType.SWITCH and i == self.move_index:
                if not AddRelocationMove(c_nbhood, switchMove[0], switchMove[1]).try_apply_move(empty_solution):
                    break
            elif self.move_type == ChangeAndRepairMoveType.SWITCH and i == self.swich_index:
                continue
            elif self.move_type == ChangeAndRepairMoveType.REMOVE and i == self.move_index:
                continue
            if not AddRelocationMove(c_nbhood, f, t).try_apply_move(empty_solution):
                break

        if(self.move_index == len(solution.relocations) and self.move_type == ChangeAndRepairMoveType.INSERT):
            AddRelocationMove(c_nbhood, self.from_stack, self.to_stack).try_apply_move(empty_solution)
        elif(self.move_index == len(solution.relocations) and self.move_type == ChangeAndRepairMoveType.SWITCH):
            AddRelocationMove(c_nbhood, switchMove[0], switchMove[1]).try_apply_move(empty_solution)
        
        # use greedy construction to repair
        while not empty_solution.is_feasible():
            move = min(c_nbhood.moves(empty_solution,only_handover=True), key=lambda m: m.lower_bound_increment(empty_solution))
            move.apply_move(empty_solution)

        return empty_solution

    def objective_value_increment(self, solution: StackingSolution) -> float:
        new_solution = self.apply_move(solution.copy_solution())
        return new_solution.lower_bound() - solution.lower_bound()

def sparse_fisher_yates_iter(n: int) -> Iterable[int]:
    '''Yields a random permutation of range(n) using a sparse Fisher-Yates shuffle.'''
    p: dict[int, int] = {}
    for i in range(n - 1, -1, -1):
        r = random.randrange(i + 1)
        yield p.get(r, r)
        if i != r:
            # p[r] = p.pop(i, i) # saves memory, takes time
            p[r] = p.get(i, i)  # lazy, but faster

class ChangeAndRepairNeighborhood(
    SupportsMoves[StackingSolution, ChangeAndRepairMove],
    SupportsRandomMove[StackingSolution, ChangeAndRepairMove],
    SupportsRandomMovesWithoutReplacement[StackingSolution, ChangeAndRepairMove]
):
    def __init__(self, problem):
        self.problem = problem

    def random_moves_without_replacement(self, solution: StackingSolution):
        #TODO: the randomness in this fuction does not yet apply to move types, 
        # also since there are more add moves than remove moves this biases the search in bad directions 
        # (longer solutions are usually worse)
        for i in sparse_fisher_yates_iter(len(solution.relocations)):
            for from_loc in sparse_fisher_yates_iter(len(solution.state.stacks)):
                for to_loc in sparse_fisher_yates_iter(len(solution.state.stacks)):
                    if from_loc == to_loc:
                        continue
                    yield ChangeAndRepairMove(
                        self, ChangeAndRepairMoveType.INSERT, i, from_loc, to_loc
                    )
            yield ChangeAndRepairMove(self, ChangeAndRepairMoveType.REMOVE, i)
            for j in sparse_fisher_yates_iter(len(solution.relocations)):
                if i != j:
                    yield ChangeAndRepairMove(self, ChangeAndRepairMoveType.SWITCH, i, swich_index=j)

    def moves(self, solution: StackingSolution):
        for i, _ in enumerate(solution.relocations):
            for from_loc, _ in enumerate(solution.state.stacks):
                for to_loc, _ in enumerate(solution.state.stacks):
                    if from_loc == to_loc:
                        continue
                    yield ChangeAndRepairMove(
                        self, ChangeAndRepairMoveType.INSERT, i, from_loc, to_loc
                    )
            yield ChangeAndRepairMove(self, ChangeAndRepairMoveType.REMOVE, i)
            for j in range(len(solution.relocations)):
                if i != j:
                    yield ChangeAndRepairMove(self, ChangeAndRepairMoveType.SWITCH, i, swich_index=j)

    def random_move(self, solution: StackingSolution):
        movetpye = random.choice(list(ChangeAndRepairMoveType))
        i = (
            random.randint(0, len(solution.relocations))
            if len(solution.relocations) > 0
            else 0
        )
        if movetpye == ChangeAndRepairMoveType.INSERT:
            from_stack = random.choice(
                [
                    s
                    for s in range(len(solution.state.stacks))
                    if len(solution.state.stacks[s]) > 0
                    and s != self.problem.handover_stack
                ]
            )
            to_stack = random.choice(
                [s for s in range(len(solution.state.stacks)) if s != from_stack]
            )
            return ChangeAndRepairMove(
                self, ChangeAndRepairMoveType.INSERT, i, from_stack, to_stack
            )
        if movetpye == ChangeAndRepairMoveType.REMOVE:
            return ChangeAndRepairMove(self, ChangeAndRepairMoveType.REMOVE, i)
        j = (
            random.choice([s for s in range(len(solution.relocations)) if s != i])
            if len(solution.relocations) > 1
            else 0
        )
        return ChangeAndRepairMove(
            self, ChangeAndRepairMoveType.SWITCH, i, swich_index=j
        )

class StackingProblem(
    SupportsConstructionNeighbourhood[AddRelocationNeighbourhood],
    SupportsLocalNeighbourhood[ChangeAndRepairNeighborhood],
    SupportsEmptySolution[StackingSolution],
    SupportsRandomSolution[StackingSolution],
):
    """
    Represents a stacking problem instance.

    Attributes:
        num_stacks (int): Number of stacks in the warehouse.
        stack_capacity (List[int]): Maximum capacity of each stack.
        max_blocks (int): Maximum number of blocks that can be handled.
        due_dates (List[int]): Due dates for each block.
        handover_time (int): Time required for handover operations.
        horizontal_speed (float): Speed of horizontal crane movement.
        vertical_speed (float): Speed of vertical crane movement.
        crane_height (int): Height of the crane.
        handover_stack (int): Index of the handover stack.
    """

    def __init__(
        self,
        max_height: List[int],
        due_dates: List[float],
        handover_time: int,
        horizontal_speed: float,
        vertical_speed: float,
        crane_height: int,
        handover_stack: int,
        initial_stacks: List[List[int]],
        name: Optional[str] = None
    ):
        self.max_height = max_height
        self.due_dates = due_dates
        self.handover_time = handover_time
        self.horizontal_speed = horizontal_speed
        self.vertical_speed = vertical_speed
        self.crane_height = crane_height
        self.handover_stack = handover_stack
        self.initial_stacks = initial_stacks
        self.c_neighbourhood = AddRelocationNeighbourhood(self)
        self.l_nbhood = ChangeAndRepairNeighborhood(self)
        self.name = name if name is not None else "unnamed"

    def empty_solution(self) -> StackingSolution:
        """Create initial solution with blocks in their starting positions."""
        return StackingSolution(
            StackingState([s.copy() for s in self.initial_stacks], self, 0), self
        )

    def random_solution(self) -> StackingSolution:
        """Create a random solution by applying random handover moves to the empty solution."""
        solution = self.empty_solution()
        while not solution.is_feasible():
            move = random.choice(list(self.construction_neighbourhood().moves(solution,only_handover=True)))
            move.apply_move(solution)
        return solution

    def construction_neighbourhood(self):
        return self.c_neighbourhood

    def local_neighbourhood(self):
        return self.l_nbhood

    @staticmethod
    def generate_initial_stacks(
        max_height,
        num_blocks,
        num_stacks,
        handover_stack,
        vspeed,
        hspeed,
        handover_time,
    ):
        """
        Generates an initial configuration of stacks for a stacking problem.
        Parameters:
            max_height (int or list of int): Maximum height for each stack.
            num_blocks (int): Total number of blocks to distribute among stacks.
            num_stacks (int): Number of stacks to create.
            handover_stack (int): Index of the stack designated as the handover stack (excluded from initial block placement).
            vspeed (int): Vertical speed parameter for due date calculation.
            hspeed (int): Horizontal speed parameter for due date calculation.
            handover_time (int): Time required for handover operations.
        Returns:
            StackingProblem: An instance of the StackingProblem class initialized with the generated stacks, due dates, and parameters.
        Raises:
            ValueError: If the total stack capacity is insufficient for the number of blocks.
        """
        stacks = [[] for _ in range(num_stacks)]
        if max_height * num_stacks < num_blocks:
            raise ValueError(
                "Not enough total stack capacity for the number of blocks."
            )
        due_dates = np.zeros(num_blocks)
        for block_id in range(num_blocks):
            stack_id = random.choice(
                [
                    i
                    for i in range(num_stacks)
                    if i != handover_stack and len(stacks[i]) < max_height
                ]
            )
            stacks[stack_id].append(block_id)
            due_dates[block_id] = np.random.uniform(
                1, (vspeed * num_blocks + hspeed * max_height) * num_blocks
            )

        return StackingProblem(
            max_height=[max_height] * num_stacks,
            due_dates=list(due_dates),
            handover_time=handover_time,
            horizontal_speed=hspeed,
            vertical_speed=vspeed,
            crane_height=max_height + 1,
            handover_stack=handover_stack,
            initial_stacks=stacks,
        )

    def __repr__(self):
        return (
            f"StackingProblem(num_stacks={len(self.max_height)}, "
            f"max_height={self.max_height}, "
            f"num_blocks={len(self.due_dates)}, "
            f"handover_stack={self.handover_stack}, "
            f"horizontal_speed={self.horizontal_speed}, "
            f"vertical_speed={self.vertical_speed}, "
            f"handover_time={self.handover_time})"
        )

    def to_json(self) -> str:
        """Serialize the problem instance to a JSON string."""
        obj = {
            "max_height": self.max_height,
            "due_dates": self.due_dates,
            "handover_time": self.handover_time,
            "horizontal_speed": self.horizontal_speed,
            "vertical_speed": self.vertical_speed,
            "crane_height": self.crane_height,
            "handover_stack": self.handover_stack,
            "initial_stacks": self.initial_stacks,
        }
        return json.dumps(obj, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "StackingProblem":
        """Deserialize a problem instance from a JSON string."""
        obj = json.loads(json_str)
        return cls(
            max_height=obj["max_height"],
            due_dates=obj["due_dates"],
            handover_time=obj["handover_time"],
            horizontal_speed=obj["horizontal_speed"],
            vertical_speed=obj["vertical_speed"],
            crane_height=obj["crane_height"],
            handover_stack=obj["handover_stack"],
            initial_stacks=obj["initial_stacks"],
        )

    @classmethod
    def from_textio(cls, f: str):
        with open(f, "r", encoding="utf-8") as file:
            data_str = file.read()
        return cls.from_json(data_str)

if __name__ == "__main__":
    # Example usage
    problem = StackingProblem.generate_initial_stacks(
        max_height=3,
        num_blocks=2,
        num_stacks=3,
        handover_stack=0,
        vspeed=1,
        hspeed=1,
        handover_time=0,
    )

    problem = StackingProblem([3, 3, 3], [0.0, 0.0, 0.0], 0, 1, 1, 3, 0, [[], [0], [1, 2]])

    # solution = problem.empty_solution()
    # print(solution)
    # for move in problem.construction_neighbourhood().moves(solution):
    #     print(f"Move from {move.from_stack} to {move.to_stack}, obj increment: {move.objective_value_increment(solution)}, lb increment: {move.lower_bound_increment(solution)}")

    # Generate a random problem instance (matching your parameters)
    # results = {}

    # Construction Algorithms
    # print("Running construction algorithms...")

    # # Greedy Construction
    # start_time = time.time()
    # solution_greedy = alg.greedy_construction(problem)
    # results["Greedy Construction"] = {
    #     "objective": solution_greedy.objective_value(),
    #     "time": time.time() - start_time,
    #     "feasible": solution_greedy.is_feasible,
    # }

    # print(problem.initial_stacks)
    # print(solution_greedy.relocations)

    random_sol = problem.random_solution()
    with open("my_sol.json", "w", encoding="utf-8") as f:
        random_sol.to_textio(f)
    print("done")

