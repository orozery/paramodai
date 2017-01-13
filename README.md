# Overview

paramodai is a paramodulation based abstract interpretation framework.

# Installation

paramodai is set to run on python 2.7.

This tool requires uses the python interface of the Z3 theorem prover.
It can be obtained from [here](https://github.com/Z3Prover/z3).

install paramodai by going to the root folder of the code and run `python setup.py install`.

# Benchmarks

You can run the benchmarks mentioned in the paper by going the the respective benchmark folder in the `benchmarks` directory and running `python test.py <k_max_clause> <d_max_rank>`. Use -1 to set an infinite value to a parameter.

# Compiling new benchmarks

paramodai analyzes Intel x86 binary code, given as linux ELF files, or windows PE files.
When using gcc, you can use the `-m32` flag to output x86 binary (and not, for example, x64 binary).

# Usage

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

# License

Copyright (C) 2017 Or Ozeri

Licensed under the Apache License, Version 2.0