from __future__ import annotations

import json
import random
import time
from typing import List
import numpy as np
import roar_net_api.algorithms as alg
from sortedcontainers import SortedSet


class StackingState:

    """
    Represents the current state of the stacks in the warehouse.
    """

    def __init__(self, stacks, problem, time =0):
        """
        Initializes the StackingState with given stacks, maximum height, warehouse height, and handover time.
        """
        self.stacks = stacks  # list to hold stacks and their blocks
        self.handover_ready_time = time  # Time until the handover stack is ready
        self.current_time = time
        self.overdue_sqr = 0
        self.problem = problem
        self.block_lookup = {block:(stack_index, height) for stack_index, stack in enumerate(stacks) for height, block in enumerate(stack) }  # quick lookup for blocks in stacks
        self.move_durations = {b: self.calc_remove_dur(b) for s in stacks for b in s}
        self.sorted_dues = SortedSet(enumerate(problem.due_dates), key=lambda x: x[1])
        

    def calc_remove_dur(self, b):
        return self.get_relocation_duration(self.block_lookup[b][0], self.problem.handover_stack,self.block_lookup[b][1], 0)
    
    def apply_relocation(self, from_stack, to_stack):
        """
        Moves a block from one stack to another.

        :param from_stack: The stack to move the block from.
        :param to_stack: The stack to move the block to.
        """
        # Underflow check: from_stack must not be empty
        if not self.stacks[from_stack] or len(self.stacks[from_stack]) == 0:
            raise ValueError(f"Cannot move block: stack {from_stack} is empty.")
       
        if to_stack is not self.problem.handover_stack:
            # Index bounds check
            if(from_stack<0 or to_stack<0 or from_stack>= len(self.stacks) or to_stack>= len(self.stacks)):
                raise ValueError(f"Stack index out of bounds: from_stack {from_stack}, to_stack {to_stack}.")
            # Overflow check: to_stack must not exceed its maximum height
            if len(self.stacks[to_stack]) + 1 > self.problem.max_height[to_stack]:
                raise ValueError(f"Cannot move block: stack {to_stack} will exceed max height.")

        # Update current time based on the move
        self.current_time = self.determine_time(from_stack, to_stack)

        block = self.stacks[from_stack].pop()
        if to_stack is not self.problem.handover_stack:
            self.stacks[to_stack].append(block)
            self.block_lookup[block] = (to_stack, len(self.stacks[to_stack])-1)
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
                delta =0
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

        from_height = len(self.stacks[from_stack])-1  # Current height of the from_stack
        to_height = len(self.stacks[to_stack])      # Current height of the to_stack

        # Vertical distance: move from current height to max_height, then down to the target height
        return self.get_relocation_duration(from_stack, to_stack, from_height, to_height)

    def get_relocation_duration(self, from_pos, to_pos, from_height, to_height):
        horizontal_distance = abs(from_pos - to_pos)
        vertical_distance = (self.problem.crane_height - from_height) + (self.problem.crane_height - to_height)
        return (horizontal_distance / self.problem.horizontal_speed) + (vertical_distance / self.problem.vertical_speed)
    
    def copy(self):
        """
        Creates a deep copy of the current StackingState.

        :return: A new instance of StackingState with the same attributes.
        """
        new_state = StackingState([stack.copy() for stack in self.stacks],self.problem, self.current_time)
        new_state.handover_ready_time = self.handover_ready_time
        new_state.overdue_sqr = self.overdue_sqr
        return new_state
    
    def __repr__(self):
        return f"StackingState(time={self.current_time}, handover_ready={self.handover_ready_time}, stacks={self.stacks}, overdue={self.overdue_sqr})"


def weigh_if_positive(x):
    return x if x > 0 else 0.00001*x

#SupportsCopySolution, SupportsObjectiveValue, SupportsLowerBound 
class Solution:
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
    def __init__(self, state: StackingState, problem, relocations: List[tuple]=None):
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
        '''Compute a lower bound on the objective value by assuming each block takes the lowest possible time to be relocated.'''
        if self.lower_bound_cache is not None:
            return self.lower_bound_cache
        time = self.state.current_time
        forward = 0
        minmove = min(self.state.move_durations.values()) if len(self.state.move_durations)>0 else 0
        handover_time = self.problem.handover_time
        for _, due in self.state.sorted_dues:
            relocation_duration= max(minmove, handover_time)
            time += relocation_duration
            forward += weigh_if_positive(time - due)
        self.lower_bound_cache = self.state.overdue_sqr + forward # at least one move per block remaining
        return self.lower_bound_cache
    def __repr__(self):
        return f"Solution(feasible={self.is_feasible()}, objval={self.objective_value()}, lb={self.lower_bound()}, moves={len(self.relocations)},state={self.state})"    
    
    def copy_solution(self):
        copy_solution = Solution(self.state.copy(), self.problem, self.relocations.copy())
        copy_solution.lower_bound_cache = self.lower_bound_cache
        return copy_solution
    
    def __str__(self):
        return f"Solution(feasible={self.is_feasible()}, objval={self.objective_value()}, lb={self.lower_bound()}, moves={len(self.relocations)},state={self.state})"

# SupportsConstructionNeighbourhood[DeliverBlockNeighbourhood],
#    SupportsLocalNeighbourhood[CombinedNeighbourhood],
#    SupportsEmptySolution[Solution],
#    SupportsRandomSolution[Solution], 
class StackingProblem:
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
        initial_stacks: List[List[int]] 
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
        
    def empty_solution(self) -> Solution:
        """Create initial solution with blocks in their starting positions."""
        return Solution(StackingState([s.copy() for s in self.initial_stacks],self, 0), self)
    
    def construction_neighbourhood(self):
        return self.c_neighbourhood

    @staticmethod
    def generate_initial_stacks(max_height, num_blocks, num_stacks, handover_stack, vspeed, hspeed, handover_time):
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
        if max_height*num_stacks < num_blocks:
            raise ValueError("Not enough total stack capacity for the number of blocks.")
        due_dates = np.zeros(num_blocks)
        for block_id in range(num_blocks):
            stack_id = random.choice([i for i in range(num_stacks) if i != handover_stack and len(stacks[i]) < max_height])
            stacks[stack_id].append(block_id)
            due_dates[block_id] = np.random.uniform(1,(vspeed*num_blocks + hspeed*max_height)*num_blocks)
        
        return StackingProblem(
            max_height=[max_height]*num_stacks,
            due_dates=list(due_dates),
            handover_time=handover_time,
            horizontal_speed=hspeed,
            vertical_speed=vspeed,
            crane_height=max_height+1,
            handover_stack=handover_stack,
            initial_stacks=stacks
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
    def from_textio(cls, f:str):
        with open(f, "r", encoding="utf-8") as file:
            data_str = file.read()  
        return cls.from_json(data_str)

#(SupportsApplyMove[Solution], SupportsLowerBoundIncrement[Solution], SupportsObjectiveValueIncrement[Solution])   
class AddRelocationMove:

    def __init__(self, neihghbourhood: AddRelocationNeighbourhood, from_stack: int, to_stack: int):
        self.neihghbourhood = neihghbourhood
        self.from_stack = from_stack   
        self.to_stack = to_stack   
    
    def apply_move(self, solution: Solution) -> Solution:
        solution.state.apply_relocation(self.from_stack, self.to_stack)
        solution.relocations.append((self.from_stack, self.to_stack))
        solution.lower_bound_cache = None
        return solution
    
    
    def objective_value_increment(self, solution: Solution) -> float:
        return self.lower_bound_increment(solution)

    def lower_bound_increment(self, solution: Solution) -> float:
        #todo this is not a valid incremental update, but a full recomputation
        nextstate = solution.copy_solution()
        self.apply_move(nextstate)
        return nextstate.lower_bound()-solution.lower_bound()
    
    def __repr__(self):
        return f"AddRelocationMove(from_stack={self.from_stack}, to_stack={self.to_stack})"

#SupportsMoves[Solution, AddRelocationMove]
class AddRelocationNeighbourhood:
    def __init__(self, problem):
        self.problem = problem

    def moves(self, solution: Solution):
        print(f"Generating moves... for{solution}")
        for from_stack in range(len(solution.state.stacks)):
            if len(solution.state.stacks[from_stack])==0:
                continue
            if from_stack is self.problem.handover_stack:
                continue
            for to_stack in range(len(solution.state.stacks)):
                if from_stack==to_stack:
                    continue
                if to_stack is not self.problem.handover_stack and len(solution.state.stacks[to_stack]) >= self.problem.max_height[to_stack]:
                    continue
                yield AddRelocationMove(self, from_stack, to_stack)

if __name__ == "__main__":
    # Example usage
    problem = StackingProblem.generate_initial_stacks(
        max_height=3,
        num_blocks=2,
        num_stacks=3,
        handover_stack=0,
        vspeed=1,
        hspeed=1,
        handover_time=0
    )


    problem = StackingProblem([3,3,3],[0.0,0.0,0.0],0,1,1,3,0,[[],[0],[1,2]])

    solution = problem.empty_solution()
    # print(solution)
    # AddRelocationMove(AddRelocationNeighbourhood(problem), 1, 0).apply_move(solution)
    # print(solution)
    # AddRelocationMove(AddRelocationNeighbourhood(problem), 2, 0).apply_move(solution)
    # print(solution)
    # AddRelocationMove(AddRelocationNeighbourhood(problem), 2, 0).apply_move(solution)
    # print(solution)


    print(solution)
    for move in problem.construction_neighbourhood().moves(solution):
        print(f"Move from {move.from_stack} to {move.to_stack}, obj increment: {move.objective_value_increment(solution)}, lb increment: {move.lower_bound_increment(solution)}")


    # Generate a random problem instance (matching your parameters)
    results = {}
    
    # Construction Algorithms
    print("Running construction algorithms...")
    
    # Greedy Construction
    start_time = time.time()
    solution_greedy = alg.greedy_construction(problem)
    results['Greedy Construction'] = {
        'objective': solution_greedy.objective_value(),
        'time': time.time() - start_time,
        'feasible': solution_greedy.is_feasible
    }

    print(problem.initial_stacks)
    print(solution_greedy.relocations)