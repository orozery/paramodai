# Overview

paramodai is a paramodulation based abstract interpretation framework.

For more details please refer to the paper:
Ozeri O., Padon O., Rinetzky N., Sagiv M. (2017) Conjunctive Abstract Interpretation Using Paramodulation. In: Bouajjani A., Monniaux D. (eds) Verification, Model Checking, and Abstract Interpretation. VMCAI 2017. Lecture Notes in Computer Science, vol 10145. Springer, Cham

# Installation

paramodai is set to run on python 2.7.

This tool requires uses the python interface of the Z3 theorem prover.
It can be obtained from [here](https://github.com/Z3Prover/z3).

install paramodai by going to the root folder of the code and run `python setup.py install`.

# Benchmarks

You can run the benchmarks mentioned in the paper by going the the respective benchmark folder in the `benchmarks` directory and running `python test.py <k_max_clause> <d_max_rank>`. Use -1 to set an infinite value to a parameter.
You can also use `python benchmarks/run_all.py` to run all benchmarks, with the different parameters mentioned in the paper.
The framework is currently hard-coded set to use **ordered paramodulation**.

# Compiling new benchmarks

paramodai analyzes Intel x86 binary code, given as linux ELF files, or windows PE files.
When using gcc, you can use the `-m32` flag to output x86 binary (and not, for example, x64 binary).
Note that the tools is not sound for using variables of different widths. Please use only `int`, `int*` (and not `char`, `char*` for example).

To disable compiler function inlining, use gcc flags `-fno-optimize-sibling-calls -fno-inline -fno-inline-functions`.

# Command-line usage

You can use the framework to prove a function always return a zero as its return code:
`python scripts/test_null_rc.py <executable_path> <function_name> <k_max_clause> <d_max_rank>`

# Interactive python usage

in a python shell, use:

```python
from paramodai.forward_analysis import ForwardAnalyzer
a = ForwardAnalyzer(<path_to_your_binary>)
a.run_from_func(<function_name_to_analyze>)
```

If your binary does not contain debug symbols, you can also use a binary address to specify the function:

```python
from paramodai.forward_analysis import ForwardAnalyzer
a = ForwardAnalyzer(<path_to_your_binary>)
a.init(<start_address>)
a.run()
```

The analysis will run and will print the list of "killed" symbols along the way (where None stands for a join operation).
When done, you can then examine the calculated abstract states for every basic block of the function:

```python
abstract_state = a.get_state(<basic_block_start_address>)
```

To get the abstract state for the function exit point, use:

```python
from paramodai.instruction import RETURN_ADDR
abstract_state = a.get_state(RETURN_ADDR)
```

You can `print abstract_state` to see a formatted list of the clauses composing the CNF formula for the abstract state.
Function arguments and local variables are named according to their stack offset.
Usually: stk_4 (first argument), stk_8 (second argument), ..., stk_-4 (first local variable), stk_-8 (second local variable), ...

You can easily convert the state to a Z3 CNF formula (given by a Z3 solver), using `abstract_state.get_solver()`.

The default values for k (max-clause) and d (max-rank) are both 2.
To change them, use:

```python
from paramodai.state import AbstractState
AbstractState.MAX_CLAUSE_SIZE = your_value
AbstractState.MAX_CLAUSE_RANK = your_value
```

To switch the tool to preform connection analysis, use:

```python
from paramodai.state import AbstractState
AbstractState.CONNECTION_ANALYSIS = True
```

# License

Copyright (C) 2017 Or Ozeri

Licensed under the Apache License, Version 2.0