import os, copy, itertools, json, copy
from collections import OrderedDict
from datetime import date

import benchmarks
import storm, epmc, multigain, prism
from input import *
from executing import execute_command_line

def check_execution(command):
    command_exp = os.path.expanduser(command)
    print(f"\tTesting execution of {command_exp} ... ", end="")
    try:
        test_out, test_time, test_code = execute_command_line(command_exp, 10)
        if test_code == 0:
            print("success!")
            return True
        else:
            print(f"WARN: Non-zero return code '{test_code}'. Output:\n{'-'*80}\n{test_out}{'-'*80}")
    except KeyboardInterrupt:
        print("Aborted.")
    except Exception as e:
        print(f"WARN: unable to execute:\n\t\t{e}")
    return ask_user_yn("Continue?")

def is_in_cfg_set(cfg_set, cfg):
    if cfg["id"] == "split":
        return cfg_set == "split"
    elif cfg["id"].startswith("simple-"):
        return cfg_set == "simple"
    elif cfg["id"].startswith("ach"):
        return cfg_set == "ach"
    else:
        return cfg_set == "standard"
            
def get_cfg_sets(tool_configs):
    cfg_sets = OrderedDict()
    cfg_set_description = OrderedDict()
    cfg_set_description["ach"] = ["Standard property interpretation, Achievability Queries"]
    # cfg_set_description["split"] = ["Check each objective independently"]
    for cfg_set in cfg_set_description:
        cfg_sets[cfg_set] = [cfg for cfg in tool_configs if is_in_cfg_set(cfg_set, cfg)]
        cfg_set_description[cfg_set].append(f"{len(cfg_sets[cfg_set])} config(s)")
    return cfg_sets, cfg_set_description

def is_supported(inst, cfg):
    if cfg["id"] == "split" and benchmarks.split_property_filename(inst) is None: return False
    if cfg["id"].startswith("ach") and benchmarks.achievability_property_filename(inst) is None: return False
    if inst["model"]["formalism"] not in cfg["supported-model-formalisms"]: return False
    if inst["model"]["type"] not in cfg["supported-model-types"]: return False
    obj_counts = inst["query"]["counts"]
    if "min-num-obj" in cfg and obj_counts["all"] < cfg["min-num-obj"]: return False
    if "max-num-obj" in cfg and obj_counts["all"] > cfg["max-num-obj"]: return False
    for obj in obj_counts.keys():
        if obj != "all" and obj not in cfg["supported-obj-types"]: return False
    return True


def get_invocation_id(inst, cfg):
    return f"{cfg['tool']}.{cfg['id']}.{inst['id']}"

def get_invocations(cfgs):
    result = []
    for inst,cfg in itertools.product(benchmarks.instances, cfgs):
        if is_supported(inst, cfg):
            result.append(OrderedDict(id=get_invocation_id(inst,cfg), instance=inst, configuration=cfg))
    return result
    
def get_command_lines(tool_binaries, cfg, inst = None):
    if cfg['tool'] == storm.name:
        return [f"{tool_binaries[storm.name]} {storm.get_command_line_args(cfg, inst)}"]
    elif cfg['tool'] == epmc.name:
        return [f"{tool_binaries[epmc.name]} {epmc.get_command_line_args(cfg, inst)}"]
    elif cfg['tool'] == multigain.name:
        return [f"{tool_binaries[multigain.name]} {multigain.get_command_line_args(cfg, inst)}"]
    elif cfg['tool'] == prism.name:
        return [f"{tool_binaries[prism.name]} {prism.get_command_line_args(cfg, inst)}"]
    else:
        assert False
    
def create_invocations():
    tool_options = OrderedDict()
    tool_options[storm.name] = [storm.description]
    tool_options[epmc.name] = [epmc.description]
    tool_options[prism.name] = [prism.description]
    tool_options[multigain.name] = [multigain.description]
    tool_selection = input_selection("Tools", tool_options)
    tool_configs = []
    tool_binaries = dict()
    for t in tool_selection:
        if t == storm.name:
            tool_binaries[t] = ask_user_for_info(f"Enter path to {t} binary:", storm.default_executable, check_execution)
            tool_configs += storm.configs
        elif t == epmc.name:
            tool_binaries[t] = ask_user_for_info(f"Enter path to {t} binary:", epmc.default_executable, check_execution)
            tool_configs += epmc.configs
        elif t == prism.name:
            tool_binaries[t] = ask_user_for_info(f"Enter path to {t} binary:", prism.default_executable, check_execution)
            tool_configs += prism.configs
        elif t == multigain.name:
            tool_binaries[t] = ask_user_for_info(f"Enter path to {t} binary:", multigain.default_executable, check_execution)
            tool_configs += multigain.configs
    
    cfg_sets, cfg_set_description = get_cfg_sets(tool_configs)
    cfg_set_selection = input_selection("Tool Configurations", cfg_set_description)
    cfgs = []
    for c in cfg_set_selection: cfgs += cfg_sets[c]
    print(f"Selected {len(cfgs)} Tool configurations.")
    for cfg in cfgs:
        for cmd in get_command_lines(tool_binaries, cfg):
            if not check_execution(cmd): exit(-1)
    
    invocations = get_invocations(cfgs)
    print(f"Considering {len(invocations)} invocations.")
    
    time_limit = int(ask_user_for_info(f"Enter a time limit (in seconds):", "7200", lambda usr_in : usr_in.isdigit()))
    log_dir =  ask_user_for_info(f"Enter a logfile directory ", f"logs{date.today()}")
    if not os.path.exists(log_dir): os.makedirs(log_dir)
    inv_name =  ask_user_for_info(f"Enter a file for storing the invocation information ", f"inv{date.today()}.json", ask_user_overwrite_file)
    print(f"Storing information for {len(invocations)} invocations ... ", end="")
    invocations_json = []
    for inv in invocations:
        inv_json = OrderedDict()
        inv_json["id"] = inv["id"]
        inv_json["benchmark-id"] = inv["instance"]["id"]
        inv_json["tool"] = inv["configuration"]["tool"]
        inv_json["configuration-id"] = inv["configuration"]["id"]
        inv_json["invocation-note"] = ". ".join(inv["configuration"]["notes"])        
        inv_json["commands"] = get_command_lines(tool_binaries, inv["configuration"], inv["instance"])
        inv_json["time-limit"] = time_limit
        inv_json["log-dir"] = log_dir
        inv_json["log"] = f"{inv['id']}.log"
        invocations_json.append(inv_json)
    with open(inv_name, 'w') as json_file:
        json.dump(invocations_json, json_file, ensure_ascii=False, indent='\t')
    print("done.")
    
    
