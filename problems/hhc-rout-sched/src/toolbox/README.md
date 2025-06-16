<!--
SPDX-FileCopyrightText: 2025 Francesca Da Ros <francesca.daros@uniud.it>

SPDX-License-Identifier: CC-BY-4.0
-->

# HHCRSP validator

## Prerequisites

To install the tool, ensure you have Python 3.11 installed. The recommended approach is to use a [Conda environment](https://docs.conda.io/projects/conda/en/latest/user-guide/getting-started.html). See in the next paragraph how to setup your conda env.

## Installation

Follow these steps to set up the toolbox:

1. **Create and activate a Conda environment**
    ```sh
    conda create -n hhcrsp_school_env python=3.11
    conda activate hhcrsp_school_env
    ```

2. **Install Poetry**
    ```sh
    pip install poetry
    ```

3. **Set up dependencies using Poetry**
    - Generate the `poetry.lock` file:
      ```sh
      poetry lock
      ```
    - Install dependencies:
      ```sh
      poetry install
      ```
    
## Usage

To validate a solution, run the following command:
```sh
hhcrsp validator solution <instance> <solution>
```
