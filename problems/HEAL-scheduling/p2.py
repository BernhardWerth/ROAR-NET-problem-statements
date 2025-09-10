import math
import random
from typing import List

class StackingState:

    """
    Represents the current state of the stacks in the warehouse.
    """

    def __init__(self, stacks, time =0):
        """
        Initializes the StackingState with given stacks, maximum height, warehouse height, and handover time.
        """
        self.stacks = stacks  # list to hold stacks and their blocks
        self.handover_ready_time = time  # Time until the handover stack is ready
        self.current_time = time
        self.overdue_sqr = 0


    def move_block(self, from_stack, to_stack, problem):
        """
        Moves a block from one stack to another.

        :param from_stack: The stack to move the block from.
        :param to_stack: The stack to move the block to.
        """
        # Underflow check: from_stack must not be empty
        if not self.stacks[from_stack] or len(self.stacks[from_stack]) == 0:
            raise ValueError(f"Cannot move block: stack {from_stack} is empty.")
       
        dur = self.__move_time(from_stack, to_stack, problem)

        # If moving to handover stack, ensure handover is ready
        if to_stack is problem.handover_stack:
            delta = self.handover_ready_time- dur-self.current_time
            if delta > 0:
                self.current_time += delta
            
        # Overflow check: to_stack must not exceed max height
        elif len(self.stacks[to_stack]) + 1 > problem.max_height[to_stack]:
            raise ValueError(f"Cannot move block: stack {to_stack} will exceed max height.")
       
        self.current_time = self.current_time + dur
        block = self.stacks[from_stack].pop()

        if to_stack is not problem.handover_stack:
            self.stacks[to_stack].append(block)
        else:
            self.handover_ready_time = self.current_time + problem.handover_time
            ot = self.current_time - problem.due_dates[block]
            self.overdue_sqr += ot*ot if ot > 0 else 0

    def is_empty(self):
        """
        Checks if all stacks are empty.

        :return: True if all stacks are empty, False otherwise.
        """
        return all(len(stack) == 0 for stack in self.stacks)

    def __move_time(self, from_stack, to_stack, problem):
        
        """
        Calculates the time required to move a block from one stack to another.

        :param from_stack: The stack to move the block from.
        :param to_stack: The stack to move the block to.
        :return: The time taken to move the block.
        """

        horizontal_distance = abs(from_stack - to_stack)
        from_height = len(self.stacks[from_stack])  # Current height of the from_stack
        to_height = len(self.stacks[to_stack])      # Current height of the to_stack

        # Vertical distance: move from current height to max_height, then down to the target height
        vertical_distance = (problem.crane_height - from_height) + (problem.crane_height - to_height - 1)
        return (horizontal_distance / problem.horizontal_speed) + (vertical_distance / problem.vertical_speed)
    
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
        due_dates: List[int],
        handover_time: int,
        horizontal_speed: float,
        vertical_speed: float,
        crane_height: int,
        handover_stack: int,
    ):
        self.max_height = max_height
        self.due_dates = due_dates
        self.handover_time = handover_time
        self.horizontal_speed = horizontal_speed
        self.vertical_speed = vertical_speed
        self.crane_height = crane_height
        self.handover_stack = handover_stack
        if len(max_height)!= len(due_dates): 
            raise ValueError("max_height and due_dates must have the same length.")
        
        