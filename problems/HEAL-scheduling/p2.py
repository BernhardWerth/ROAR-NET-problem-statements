import math
import random

class StackingState:
    """
    Represents the current state of the stacks in the warehouse.
    """

    def __init__(self, stacks, max_height, warehouse_height, handover_time, time =0):
        """
        Initializes the StackingState with given stacks, maximum height, warehouse height, and handover time.

        :param stacks: Dictionary holding stacks and their blocks.
        :param max_height: Maximum height of each stack.
        :param warehouse_height: Maximum height of the warehouse.
        :param handover_time: Time required for the handover stack to be ready after a delivery.
        """
        self.stacks = stacks  # Dictionary to hold stacks and their blocks
        self.handover_ready_time = 0  # Time until the handover stack is ready
        self.handover_time = handover_time
        self.current_time = time
        self.overdueSqr = 0


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
        if to_stack is problem.handover_stack:
            delta = self.handover_ready_time- dur-self.current_time
            if delta > 0:
                self.current_time = self.current_time + delta
            self.handover_ready_time = self.current_time + dur + self.handover_time
        # Overflow check: to_stack must not exceed max height
        elif len(self.stacks[to_stack]) + 1 > problem.max_height[to_stack]:
            raise ValueError(f"Cannot move block: stack {to_stack} will exceed max height.")
        
        self.current_time = self.current_time + dur
        block = self.stacks[from_stack].pop()

        if to_stack is not problem.handover_stack:
            self.stacks[to_stack].append(block)
        else:
            ot = self.current_time - problem.due_dates[block]
            self.overdueSqr += ot*ot if ot > 0 else 0


    def is_empty(self):
        """
        Checks if all stacks are empty.

        :return: True if all stacks are empty, False otherwise.
        """
        return all(len(stack) == 0 for stack in self.stacks.values())

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
        vertical_distance = (problem.max_height[from_stack] - from_height) + (problem.max_height[to_stack] - to_height - 1)
        return (horizontal_distance / problem.horizontal_speed) + (vertical_distance / problem.vertical_speed)