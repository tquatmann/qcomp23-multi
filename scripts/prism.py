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
        assert inst["model"]["formalism"] == "prism"
        out.append(benchmarks.model_filename(inst))
        if cfg["id"].startswith("ach"):
            out.append(benchmarks.achievability_property_filename(inst))
        else:
            out.append(benchmarks.separated_property_filename(inst))
        c = const_def_string(inst)
        if c is not None:
            out.append(f"-const {const_def_string(inst)}")
    out += cfg["cmd"]
    return " ".join(out)
        
name = "prism"
description = "PRISM - Probabilistic Symbolic Model Checker"
default_executable = "~/prism/prism/bin/prism"

# Configuration data
# IDs shall not have a "_" or "."
base_cfg = OrderedDict()
base_cfg["tool"] = name
base_cfg["cmd"] = ["-sparse -cuddmaxmem 4g"]
base_cfg["notes"] = ["Prism."]
base_cfg["supported-obj-types"] = ["Rt", "Pf", "Bs"]
base_cfg["supported-model-types"] = ["mdp"]
base_cfg["supported-model-formalisms"] = ["prism"]
base_cfg["id"] = 'default'
base_cfg["min-num-obj"] = 2

ach_cfg = copy.deepcopy(base_cfg)
ach_cfg["id"] = 'ach'
ach_cfg["cmd"] += ["-gs -maxiters 1000000000 -multimaxpoints 1000000", "-absolute"]
ach_cfg["notes"] += ["Achievability queries. Gauss-Seidl VI."]
ach_cfg["latex"] = r"\prism"



configs = [ach_cfg]

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
    #unsupported_messages.append("Error: Only the C and C>=k reward operators are currently supported for multi-objective properties (not F).") # TODO: SHOULD not happen anymore since we filter those in the config settings
    #unsupported_messages.append("Error: Step-bounded objectives are not currently supported with linear programming.") # TODO: should not happen anymore as well
    #unsupported_messages.append("Error: Pareto curve generation is currently only supported for 2 objectives.") # TODO: should not happen anymore as well
    inv["not-supported"] = contains_any_of(log, unsupported_messages)
    memout_messages = []
    memout_messages.append("java.lang.OutOfMemoryError")
    memout_messages.append("Return code:\t-9")
    inv["memout"] = contains_any_of(log, memout_messages)
    known_error_messages = []
    #known_error_messages.append("Error: Iterative method did not converge within 10000 iterations.") # TODO
    known_error_messages.append('java.lang.NullPointerException: Cannot invoke "jdd.JDDNode.ptr()" because "<parameter1>" is null') # This is likely an issue with using insufficient cudd memory
    # known_error_messages.append('Error: The computation did not finish in 50 target point iterations, try increasing this number using the -multimaxpoints switch..') # TODO: remove, we set the switch
    inv["expected-error"] = contains_any_of(log, known_error_messages)
    if inv["not-supported"] or inv["expected-error"]: return
    if len(inv["return-codes"]) != 1 or inv["return-codes"][0] != 0:
        if not inv["timeout"] and not inv["memout"]: print("WARN: Unexpected return code(s): {} in {}".format(inv["return-codes"], inv["id"]))
    pos = try_parse(log, 0, "Time for model construction: ", "seconds.", inv, "model-building-time", float)
    if pos == 0: 
        assert inv["timeout"] or inv["memout"], "WARN: unable to get model construction time for {}".format(inv["id"])
        return

    inv["has-result"] = log.find("Time for model checking:", pos) >= pos
    if inv["has-result"]:
        pos = try_parse(log, pos, "Time for model checking: ", "seconds.", inv, "model-checking-time", float)
        assert "Result: " in log[pos:]
        if "Result: false" in log:
            inv["achievable"] = False
        elif "Result: true" in log:
            inv["achievable"] = True
        else:
            pos1 = log.find("Result: ", pos) + len("Result: ")
            pos2 = log.find("\n", pos1)
            inv["pareto-points"] = log[pos1:pos2].count("(")
    if not inv["timeout"] and not inv["memout"] and "model-checking-time" not in inv:
        print("No model checking time obtained in {}".format(inv["id"]))

if __name__ == "__main__":
    print(json.dumps(configs,indent='\t'))
    print(f"{len(configs)} configs")

