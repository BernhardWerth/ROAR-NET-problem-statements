from p2 import *
import pytest

def test_lower_bound_property(problem, construction_algorithm):
    """Test that the lower bound is always <= final objective value at every step."""
    final_solution = construction_algorithm(problem)
    final_objective = final_solution.objective_value()
    moves_sequence = final_solution.relocations
    
    # Start with empty solution and replay each move
    current_solution = problem.empty_solution()
    
    # Test initial state: lower bound should <= final objective
    assert current_solution.lower_bound() <= final_objective, \
        f"Step 0: Lower bound {current_solution.lower_bound()} > final objective {final_objective}"
    
    # Apply each move and validate bounds against final objective
    for step, (from_stack, to_stack) in enumerate(moves_sequence, 1):
        neighbourhood = problem.construction_neighbourhood()
        move = AddRelocationMove(neighbourhood, from_stack, to_stack)
        move.apply_move(current_solution)
        
        # Lower bound should always be <= final objective
        assert current_solution.lower_bound() <= final_objective, \
            f"Step {step}: Lower bound {current_solution.lower_bound()} > final objective {final_objective}"
    
    # Final validation
    assert current_solution.is_feasible(), "Final solution should be feasible"
    assert abs(current_solution.objective_value() - final_objective) < 1e-10, \
        f"Replayed objective {current_solution.objective_value()} != original final objective {final_objective}"
    
    return current_solution

def test_lower_bound_increment_accuracy(problem, construction_algorithm):
    """Test that lower bound increment predictions are accurate."""
    solution = problem.empty_solution()
    
    steps = 0
    while not solution.is_feasible() and steps < 100:
        moves = list(problem.construction_neighbourhood().moves(solution))
        if not moves:
            break
            
        # Test increment prediction for first available move
        move = moves[0]
        old_lb = solution.lower_bound()
        predicted_increment = move.lower_bound_increment(solution)
        move.apply_move(solution)
        new_lb = solution.lower_bound()
        actual_increment = new_lb - old_lb
        
        # Predicted increment should match actual increment
        assert abs(actual_increment - predicted_increment) < 1e-10, \
            f"Step {steps}: Predicted increment {predicted_increment} != actual increment {actual_increment}"
        
        steps += 1

def test_state_copy_independence(problem):
    """Test that copied states are truly independent"""
    original = problem.empty_solution()
    moves = list(problem.construction_neighbourhood().moves(original))
    if moves:
        moves[0].apply_move(original)
    
    copied = original.state.copy()
    remaining_moves = list(problem.construction_neighbourhood().moves(original))
    if remaining_moves:
        remaining_moves[0].apply_move(original)
    else:
        return  # No further moves possible, skip test
    
    # Copied state should be unchanged
    assert copied.current_time != original.state.current_time
    assert copied.stacks != original.state.stacks
    assert copied.overdue_sqr != original.state.overdue_sqr

def test_solution_copy_independence(problem):
    """Test that copied solutions are truly independent"""
    original = problem.empty_solution()
    moves = list(problem.construction_neighbourhood().moves(original))
    if moves:
        moves[0].apply_move(original)

    copied = original.copy_solution()
    remaining_moves = list(problem.construction_neighbourhood().moves(original))
    if remaining_moves:
        remaining_moves[0].apply_move(original)
    else:
        return  # No further moves possible, skip test
    
    # Copies should be independent
    assert len(copied.relocations) != len(original.relocations)
    assert copied.state.current_time != original.state.current_time

def test_deep_copy_collections(problem):
    """Test that nested collections are properly deep copied"""
    original = problem.empty_solution()
    copied = original.copy_solution()
    
    # Modify original stacks
    if original.state.stacks[1]:
        original.state.stacks[1].append(999)
    assert 999 not in copied.state.stacks[1]
    
    # Test relocations list independence
    original.relocations.append((99, 99))
    assert (99, 99) not in copied.relocations

def test_copy_preserves_values(problem):
    """Test that copying preserves all important values exactly"""
    original = problem.empty_solution()
    for i in range(2): # Apply a couple of moves
        moves = list(problem.construction_neighbourhood().moves(original))
        if not moves:
            break
        moves[0].apply_move(original)  # Apply first available move
    
    # Copy and compare all fields
    copied = original.copy_solution()
    
    assert copied.state.current_time == original.state.current_time
    assert copied.state.handover_ready_time == original.state.handover_ready_time
    assert copied.state.overdue_sqr == original.state.overdue_sqr
    assert copied.state.stacks == original.state.stacks
    assert copied.relocations == original.relocations
    assert copied.lower_bound() == original.lower_bound()

def test_copy_after_handover_moves(problem):
    """Test copying after blocks have been moved to handover stack"""
    solution = problem.empty_solution()
    
    handover_moves = []
    while len(handover_moves) < 2 and not solution.is_feasible():
        moves = list(problem.construction_neighbourhood().moves(solution))
        handover_move = next((m for m in moves if m.to_stack == problem.handover_stack), None)
        if handover_move:
            handover_move.apply_move(solution)
            handover_moves.append(handover_move)
        else:
            break
    
    copied = solution.copy_solution()
    # Both should have same remaining blocks
    assert list(copied.state.sorted_dues) == list(solution.state.sorted_dues)
    assert copied.state.block_lookup == solution.state.block_lookup
    assert copied.state.move_durations == solution.state.move_durations

def test_copy_preserves_sorted_dues_order(problem):
    """Test that sorted_dues maintains correct order after copying"""
    solution = problem.empty_solution()
    
    # Check initial order
    initial_order = list(solution.state.sorted_dues)
    print(f"Initial sorted dues: {initial_order}")
    
    # Copy and check order preserved
    copied = solution.copy_solution()
    copied_order = list(copied.state.sorted_dues)
    
    assert initial_order == copied_order
    
    # Apply move and copy again
    moves = list(problem.construction_neighbourhood().moves(solution))
    if moves:
        moves[0].apply_move(solution)
        copied_after_move = solution.copy_solution()
        
        # Order should still be correct
        current_order = list(solution.state.sorted_dues)
        copied_after_order = list(copied_after_move.state.sorted_dues)
        assert current_order == copied_after_order

def test_multiple_copy_levels(problem):
    """Test copying copies (copy of copy)"""
    original = problem.empty_solution()
    
    # Apply a move
    moves = list(problem.construction_neighbourhood().moves(original))
    if moves:
        moves[0].apply_move(original)
    
    # Create copy chain: original -> copy1 -> copy2
    copy1 = original.copy_solution()
    copy2 = copy1.copy_solution()
    
    # Modify original and copy1
    remaining_moves = list(problem.construction_neighbourhood().moves(original))
    if remaining_moves:
        remaining_moves[0].apply_move(original)
    else:
        return  # No further moves possible, skip test
        
    copy1_moves = list(problem.construction_neighbourhood().moves(copy1))
    if copy1_moves:
        copy1_moves[0].apply_move(copy1)
    
    # copy2 should be unaffected by changes to original and copy1
    assert len(copy2.relocations) < len(original.relocations)
    assert len(copy2.relocations) < len(copy1.relocations)

if __name__ == "__main__":
    scenarios = [
        StackingProblem([3,3,3], [0.0,0.0,0.0], 0, 1, 1, 3, 0, [[], [0], [1, 2]]),
        StackingProblem([2,2], [5.0], 0, 1, 1, 2, 0, [[], [0]]),
        StackingProblem([4,4,4], [1.0, 5.0, 3.0, 7.0], 2, 1, 1, 4, 0, [[], [0, 1], [2, 3]])
    ]
    
    # test lower bound
    for i, problem in enumerate(scenarios):
        print(f"Testing scenario {i+1}")
        test_lower_bound_property(problem, alg.greedy_construction)
        test_lower_bound_increment_accuracy(problem, alg.greedy_construction)
        print(f"✓ Scenario {i+1} passed")


    # Test cloning and copying functionalities
    cloning_test_functions = [
        test_state_copy_independence,
        test_solution_copy_independence, 
        test_deep_copy_collections,
        test_copy_preserves_values,
        test_copy_after_handover_moves,
        test_copy_preserves_sorted_dues_order,
        test_multiple_copy_levels
    ]
    
    for i, problem in enumerate(scenarios):
        print(f"\n=== Testing scenario {i+1} ===")
        for test_func in cloning_test_functions:
            print(f"Running {test_func.__name__}...")
            test_func(problem)
            print(f"✓ {test_func.__name__} passed")
        print(f"✓ Scenario {i+1} completed")