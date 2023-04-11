import os, copy, itertools, json
from collections import OrderedDict

import benchmarks


def const_def_string(inst):
    if "parameters" in inst["model"]:
        pars = inst["model"]["parameters"]
        return ",".join([f"{p}={pars[p]}" for p in pars ])

def get_command_line_args(cfg, inst = None):
    out = []
    if inst is not None:
        if inst["model"]["formalism"] == "prism":
            out.append(f"--prism {benchmarks.model_filename(inst)}")
            if cfg["id"] == "split":
                out.append(f"--prop {benchmarks.split_property_filename(inst)}")
            elif cfg["id"] == "ach":
                out.append(f"--prop {benchmarks.achievability_property_filename(inst)}")
            else:
                out.append(f"--prop {benchmarks.property_filename(inst)} {inst['query']['id']}")
        else:
            assert inst["model"]["formalism"] == "jani"
            assert cfg["id"] not in ["split", "ach"]
            out.append(f"--jani {benchmarks.model_filename(inst)}")
            out.append(f"-jprop {inst['query']['jani']}")
            if inst["query"]["counts"]["all"] >= 2:
                out.append("--propsasmulti")
        c = const_def_string(inst)
        if c is not None:
            out.append(f"-const {const_def_string(inst)}")
    out += cfg["cmd"]
    return " ".join(out)
        
name = "storm"
description = "Storm model checker"
default_executable = "~/storm/build/bin/storm"

# Configuration data
# IDs shall not have a "_" or "."
configs = []   
 
base_cfg = OrderedDict()
base_cfg["tool"] = name
base_cfg["cmd"] = ["--timemem", "--statistics"]
base_cfg["notes"] = ["Storm"]
base_cfg["supported-obj-types"] = list(benchmarks.obj_types.keys())
base_cfg["supported-model-types"] = ["ctmc", "dtmc", "ma", "mdp"]
base_cfg["supported-model-formalisms"] = ["prism", "jani"]

split_cfg = copy.deepcopy(base_cfg)
split_cfg["id"] = 'split'
split_cfg["cmd"] += ["--sound"]
split_cfg["notes"] += ["check each objective in isolation"]
configs.append(split_cfg)

ach_cfg = copy.deepcopy(base_cfg)
ach_cfg["id"] = 'ach'
ach_cfg["cmd"] += ["--sound", "--topological:minmax svi", "--native:method svi", "--topological:relevant-values", "--absolute"]
ach_cfg["notes"] += ["check achievability objectives using sound value iteration"]
ach_cfg["latex"] = r"\storm"
configs.append(ach_cfg)

def config_from_id(identifier):
    for c in configs:
        if c["id"] == identifier: return c
    assert False, f"Configuration identifier {identifier} is not known."
    
# LOGFILE Parsing
def contains_any_of(log, msg): 
    for m in msg:
        if m in log: return True
    return False

def try_parse(log, start, before, after, out_dict, out_key, out_type):
    pos1 = log.find(before, start)
    if pos1 >= 0:
        pos1 += len(before)
        pos2 = log.find(after, pos1)
        if pos2 >= 0:
            out_dict[out_key] = out_type(log[pos1:pos2])
            return pos2 + len(after)
    return start

def parse_logfile(log, inv):
    unsupported_messages = []
    unsupported_messages.append("Flow encoding only applicable if all objectives are (transformable to) total reward objectives.")
    inv["not-supported"] = contains_any_of(log, unsupported_messages)
    memout_messages = []
    memout_messages.append("BDD Unique table full")
    memout_messages.append("An unexpected exception occurred and caused Storm to terminate. The message of this exception is: std::bad_alloc")
    memout_messages.append("An unexpected exception occurred and caused Storm to terminate. The message of this exception is: cannot create std::vector larger than max_size()")
    memout_messages.append("Return code:\t-9")
    inv["memout"] = contains_any_of(log, memout_messages)
    known_error_messages = []
    known_error_messages.append("Could not assert constraint (Element 0 of a double array is Nan or Inf.") # Constant in LP is too large
    known_error_messages.append("Return code:\t11") # known issue with gurobi 9.5 on rov with classicIndicator
    inv["expected-error"] = contains_any_of(log, known_error_messages)
    if inv["not-supported"] or inv["expected-error"]: return
    if len(inv["return-codes"]) != 1 or inv["return-codes"][0] != 0:
        if not inv["timeout"] and not inv["memout"]: print("WARN: Unexpected return code(s): {} in {}".format(inv["return-codes"], inv["id"]))
    pos = try_parse(log, 0, "Time for model construction: ", "s.", inv, "model-building-time", float)
    if pos == 0: 
        assert inv["timeout"] or inv["memout"], "WARN: unable to get model construction time for {}".format(inv["id"])
        return
    inv["input-model"] = OrderedDict()
    if inv["configuration"]["id"] in ["dd", "dd28", "hyb"]:
        pos = try_parse(log, pos, "States: \t", " (", inv["input-model"], "states", int)
        pos = try_parse(log, pos, "Transitions: \t", " (", inv["input-model"], "transitions", int)
    else:
        pos = try_parse(log, pos, "States: \t", "\n", inv["input-model"], "states", int)
        pos = try_parse(log, pos, "Transitions: \t", "\n", inv["input-model"], "transitions", int)
    pos = try_parse(log, pos, "Choices: \t", "\n", inv["input-model"], "choices", int)
    pos = log.find("Model checking property")
    if pos < 0:
        assert inv["memout"] or inv["timeout"], "Unable to find query output in {}".format(inv["id"])
        return
    pos_tmp = log.find("Preprocessed Model Information:", pos)
    if pos_tmp >= 0:
        pos = pos_tmp
        inv["preprocessed-model"] = OrderedDict()
        pos = try_parse(log, pos, "States: \t", "\n", inv["preprocessed-model"], "states", int)
        pos = try_parse(log, pos, "Transitions: \t", "\n", inv["preprocessed-model"], "transitions", int)
        pos = try_parse(log, pos, "Choices: \t", "\n", inv["preprocessed-model"], "choices", int)
    pos = try_parse(log, pos, " actions.\nFound ", " end components that are relevant for LRA-analysis", inv, "lra-ecs", int)
    pos = try_parse(log, pos, "\n", " states lie on such an end component", inv, "lra-states", int)
    pos = try_parse(log, pos, "Pareto Curve Approximation Algorithm terminated after ", " refinement steps.", inv, "wso-iterations", int)
    pos = try_parse(log, pos, "#checked epochs: ", ".\n", inv, "num-epochs", int)
    pos = try_parse(log, pos, "#checked epochs overall: ", ".\n", inv, "num-epochs", int)
    pos = try_parse(log, pos, "Number of checked epochs: ", ".\n", inv, "num-epochs", int)
    pos = try_parse(log, pos, "transitions in unfolded-model\n#STATS 10^", " memoryless deterministic schedulers in unfolded-model", inv, "log10-stratspm", float)
    pos = try_parse(log, pos, "#STATS ", " MECS in unfolded-model", inv, "mecs", int)
    pos = try_parse(log, pos, "#STATS ", " MEC States in unfolded-model", inv, "mec-states", int)
    inv["has-result"] = log.find("Result (for initial states)", pos) >= pos
    if inv["has-result"]:
        if "Result (for initial states): false" in log:
            inv["achievable"] = False
        if "Result (for initial states): true" in log:
            inv["achievable"] = True
        pos_tmp = log.find(" Pareto optimal points found:", pos)
        if pos_tmp >= 0:
            pos = log.rfind("\n",pos,pos_tmp)
            pos = try_parse(log, pos, ""," Pareto optimal points found:", inv, "pareto-points", int)
        pos = try_parse(log, pos, "Time for model checking: ", "s.", inv, "model-checking-time", float)
    
    if not inv["timeout"] and not inv["memout"] and "model-checking-time" not in inv:
        print("No model checking time obtained in {}".format(inv["id"]))

if __name__ == "__main__":
    print(json.dumps(configs,indent='\t'))
    print(f"{len(configs)} configs")

