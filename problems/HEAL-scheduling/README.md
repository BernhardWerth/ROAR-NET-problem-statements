<!--
SPDX-FileCopyrightText: 2024 Alexandre Jesus <me@adbjesus.com>

SPDX-License-Identifier: CC-BY-4.0
-->

<!-- Replace the comment above with your licence information for your problem
statement. Consider all copyright holders and contributors. -->

<!-- According to the copyright and licensing policy of ROAR-NET original
problem statements contributed to this repository shall be licensed under the
CC-BY-4.0 licence. In some cases CC-BY-SA-4.0 might be accepted, e.g., if the
problem is based upon an existing problem licensed under those terms. Please
provide a clear justification when opening the pull request if the problem is
not licensed under CC-BY-4.0 -->

<!-- Remove the section below before submitting -->

# Problem template


This folder provides a template for problem statements.

Replace the problem statement below according to the instructions within that
file (and remove this section).

Place any images and figures in the `images` folder.

Place instance data in the `data` folder. The organisation within that folder is
merely a suggestion and may be adapted according to the problem needs.

Place any support material (e.g., instance generators, solution evaluators,
solution visualisers) in the `support` folder.

Template follows below.

---

<!-- Remove the section above before submitting -->

# Container Stacking

Bernhard Werth, Universitiy of Applied Sciences Upper Austria, Austria  
Florian Holzinger, Universitiy of Applied Sciences Upper Austria, Austria  
Johannes Karder, Universitiy of Applied Sciences Upper Austria, Austria  
Florian Bruckner, Universitiy of Applied Sciences Upper Austria, Austria  
Stefan Wagner, Universitiy of Applied Sciences Upper Austria, Austria  

<!-- Put two empty spaces at the end of each author line except the last for
proper formatting -->

Copyright 2025 ... place copyright holders here.

This document is licensed under XXXX.

<!-- Complete the above accordingly. Copyright and licensing information must be
consistent with the comment at the beggining of the markdown file -->

## Introduction

Container Stacking Problems are found in warehouse and logistics operations where containers must be retrieved from storage stacks and moved to a handover location while minimizing overdueness. In typical warehouse scenarios, containers are stacked vertically in multiple columns, but only the topmost container in each stack can be accessed directly. When a container that is not at the top needs to be retrieved, relocations are used to move containers from one storage stack to another or to the handover stack to clear access paths.

The goal is to find a sequence of moves that leads to a feasible solution while keeping overdueness in check. This becomes particularly challenging when containers have different due dates for retrieval, as the timing of each relocation directly impacts whether containers are delivered on time. The problem requires balancing the immediate need to access specific containers against the long-term efficiency of the overall retrieval sequence, all while considering the physical constraints of crane movement speeds and stack capacities.

Common applications for this problem include container terminals, automated warehouses, and any storage system where items are stacked and must be retrieved in a time-sensitive manner while respecting physical access constraints.


## Task

Minimize the total overdue penalty by optimally sequencing container relocations from storage stacks to a handover area, subject to crane movement speeds, stack capacity limits, handover processing times, and container due dates.

## Detailed description

### Problem
A problem instance is characterized by:

- **Storage stacks**: A set of vertical stacks, each with a maximum height capacity
- **Containers**: Blocks with assigned due dates for retrieval
- **Crane parameters**: Horizontal and vertical movement speeds, and maximum crane height
- **Handover area**: A designated stack where containers are delivered for pickup
- **Handover time**: Processing time required at the handover area after delivery

### Solution
A solution consists of a sequence of relocation moves, where each move transfers the top container from one stack to another (including the handover stack). Only the topmost container of any stack can be accessed at any time.

### Objective function
Minimize the total overdue penalty:

$$
\text{minimize} \quad \sum_{i=1}^{n} f(C_i - d_i)
$$

where $n$ is the number of containers, $C_i$ is the completion time of container $i$, $d_i$ is the due date of container $i$, and $f(x)$ is defined as:

$$
f(x) = \begin{cases} 
x & \text{if } x > 0 \text{ (overdue penalty)} \\
0.00001 \cdot x & \text{if } x \leq 0 \text{ (early delivery reward)}
\end{cases}
$$


### Constraints
- Only the top container of a stack can be moved
- Destination stacks cannot exceed their maximum height capacity
- All containers must eventually be moved to the handover stack
- The crane cannot operate while the handover area is processing a previous delivery

### Move timing
Each move's duration depends on the horizontal distance between stacks and the vertical distances the crane must travel, divided by the respective crane speeds. When delivering to the handover area, additional processing time is added, during which no other containers can hand-overed.


## Instance data file


Problem instances are stored in JSON format with the following structure:

- `max_height`: Array specifying the maximum capacity for each stack (including handover stack)
- `due_dates`: Array of due dates for each container, indexed by container ID
- `handover_time`: Processing time required at the handover area after each delivery
- `horizontal_speed`: Crane horizontal movement speed (stacks per time unit)
- `vertical_speed`: Crane vertical movement speed (levels per time unit)  
- `crane_height`: Maximum height the crane can reach
- `handover_stack`: Index of the designated handover stack
- `initial_stacks`: Array of stacks, each containing container IDs in bottom-to-top order

## Solution file

Solutions are represented as JSON format with the following structure:

- `problem`: Identifier or name of the problem instance
- `relocations`: Array of move pairs `[from_stack, to_stack]` representing the solution sequence


## Example

### Instance

```json
{
  "max_height": [4, 8, 8, 8, 8, 8, 8, 1],
  "due_dates": [
    1575.686, 1315.151, 1535.035, 2064.676, 1470.069,
    1204.386, 1934.042, 1048.604, 1427.422, 1056.172,
    918.999, 762.065, 976.745, 1006.513, 867.015,
    1082.974, 1019.891, 670.219, 924.665, 815.906,
    995.417, 780.758, 1069.423, 539.129, 201.985,
    814.551, 427.279, 404.81, 1366.622, 523.248,
    1057.936, 944.107, 134.88, 345.313, 1466.904
  ],
  "handover_time": 2,
  "horizontal_speed": 0.25,
  "vertical_speed": 0.5,
  "crane_height": 9,
  "handover_stack": 7,
  "initial_stacks": [
    [34],
    [11, 7, 4],
    [29, 27, 17, 16, 13, 8, 1],
    [22, 15, 0],
    [32, 28, 25, 24, 20, 18, 10, 3],
    [33, 23, 19, 14, 5],
    [31, 30, 26, 21, 12, 9, 6, 2],
    []
  ]
}
```

This instance contains 8 stacks with varying capacities (4, 8, 8, 8, 8, 8, 8, 1), where stack 7 serves as the handover area. There are 35 containers distributed across the first 7 stacks, with due dates ranging from approximately 135 to 2065 time units. The crane moves at 0.25 stacks per time unit horizontally and 0.5 levels per time unit vertically, with a maximum reach of 9 levels.


### Solution

TODO

Provide a feasible solution to the example instance in the described format
(including its evaluation measure).

## Acknowledgements

This problem statement is based upon work from COST Action Randomised
Optimisation Algorithms Research Network (ROAR-NET), CA22137, is supported by
COST (European Cooperation in Science and Technology).

<!-- Please keep the above acknowledgement. Add any other acknowledgements as
relevant. -->

## References

Put any relevant references here.
