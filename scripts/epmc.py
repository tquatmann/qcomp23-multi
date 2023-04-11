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
        #epmc check  --property-input-files frw_pfpf.props --const delay=36,Unf=2,B=10 
        out.append(f"--model-input-files {benchmarks.model_filename(inst)}")
        assert cfg["id"] == "ach"
        out.append(f"--property-input-files {benchmarks.achievability_property_filename(inst)}")
        c = const_def_string(inst)
        if c is not None:
            out.append(f"--const {const_def_string(inst)}")
    out += cfg["cmd"]
    return " check " + " ".join(out)
        
name = "epmc"
description = "EPMC - An Extendible Probabilistic Model Checker (commit b1ba8ab)"
default_executable = "java -jar ~/ePMC/epmc-standard.jar"

# Configuration data
# IDs shall not have a "_" or "."
configs = []   
 
ach_cfg = OrderedDict()
ach_cfg["tool"] = name
ach_cfg["cmd"] = ["--graphsolver-iterative-stop-criterion absolute --graphsolver-iterative-tolerance 1e-6"]
ach_cfg["notes"] = ["EPMC default settings. Check achievability objectives."]
ach_cfg["supported-obj-types"] = ["Rt", "Rf", "Pf"]
ach_cfg["supported-model-types"] = ["mdp"]
ach_cfg["supported-model-formalisms"] = ["prism"]
ach_cfg["id"] = "ach"
ach_cfg["latex"] = r"\epmc"
ach_cfg["min-num-obj"] = 2

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
    #unsupported_messages.append("")
    inv["not-supported"] = contains_any_of(log, unsupported_messages)
    memout_messages = []
    memout_messages.append("java.lang.OutOfMemoryError")
    inv["memout"] = contains_any_of(log, memout_messages)
    known_error_messages = []
    known_error_messages.append("java.lang.NullPointerException: Cannot read the array length because \"<local5>\" is null")
    known_error_messages.append("java.lang.RuntimeException: java.lang.NegativeArraySizeException:")
    inv["expected-error"] = contains_any_of(log, known_error_messages)
    if inv["not-supported"] or inv["expected-error"]: return
    if len(inv["return-codes"]) != 1 or inv["return-codes"][0] != 0:
        if not inv["timeout"] and not inv["memout"]: print("WARN: Unexpected return code(s): {} in {}".format(inv["return-codes"], inv["id"]))
    pos = try_parse(log, 0, " Time for model exploration: ", " seconds.", inv, "model-building-time", lambda s : float(s.replace(",", "")))
    if pos == 0: 
        assert inv["timeout"] or inv["memout"], "WARN: unable to get model construction time for {}".format(inv["id"])
        return

    inv["has-result"] = log.find("Finished model checking. Time required: ", pos) >= pos
    if inv["has-result"]:
        pos = try_parse(log, pos, "Finished model checking. Time required: ", " seconds\n", inv, "model-checking-time", lambda s : float(s.replace(",", "")))
        pos += 1
        next_line = log[pos:log.find("\n",pos)]
        if ": true" in next_line:
            inv["achievable"] = True
        else:
            assert ": false" in next_line, "Unexpected result line \n\t> '{}'".format(next_line)
            inv["achievable"] = False
    if not inv["timeout"] and not inv["memout"] and "model-checking-time" not in inv:
        print("No model checking time obtained in {}".format(inv["id"]))

if __name__ == "__main__":
    print(json.dumps(configs,indent='\t'))
    print(f"{len(configs)} configs")

