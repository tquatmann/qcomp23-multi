# Experimental Data for Multi-Objective Analysis (QComp 2023)

## Overview of Contents

This package contains the experimental data for the category `Multi-Objective Analysis` of QComp 2023 

- `models` contains all benchmark models and verification queries
- `results` contains the obtained log-files and processed data
- `scripts` contains a set of python scripts used to invoke the tools and process their output

## Browsing the Results

The directory `results` contains all raw logfiles and the derived data, including browsable html tables.
The `data` directory was generated using the commands

```console
cd path/to/results/
python3 ../scripts/postprocess.py logs
```

## Generating Replication Scripts

To run custom experiments, `cd` into an empty directory and run `python3 path/to/scripts/run.py`.
The script guides the user to generate the command lines and stores them in an invocations file in `.json` format.
These command lines can then be executed using `python3 path/to/scripts/run.py inv*.json`


## Considered Tool Versions

We considered the following tool versions:

- EPMC obtained from <https://github.com/iscas-tis/ePMC>, commit `b1ba8ab`
- Prism obtained from <https://github.com/prismmodelchecker/prism>, commit `3a632e2`
- MultiGain obtained from <http://qav.cs.ox.ac.uk/multigain/> version `1.0.2`, using Gurobi `9.5` as LP Solver
  - Remark: The authors of MultiGain v2 confirmed that the newer version is expected to have similar runtimes on the exercised benchmarks
- Storm obtained from <https://doi.org/10.5281/zenodo.7766202>, based on version `1.7.0`
  - Remark: The considered version of Storm contains revised code that---at the time of writing---has not yet been merged back into the main release.
