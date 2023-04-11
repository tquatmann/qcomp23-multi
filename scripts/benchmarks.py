import itertools, os, sys
import json
from collections import Counter,OrderedDict

models_dir = os.path.realpath(os.path.join(sys.path[0], "../models/"))
assert os.path.isdir(models_dir), f"Models directory {models_dir} apparently does not exist."

# identifier encodes kinds of properties: 
obj_types = OrderedDict()
obj_types["Lr"] = "LRA reward"
obj_types["Lp"] = "LRA probability"
obj_types["Rt"] = "total reward"
obj_types["Rf"] = "Reachability reward"
obj_types["Pf"] = "reachability probability"
obj_types["Bt"] = "time bounded (MA)"
obj_types["Bs"] = "step bounded (MDP)"
obj_types["Br"] = "reward bounded"
obj_types["Qp"] = "Quantile involving probabilities"

def model_filename(inst):
    res = os.path.join(models_dir, inst["name"], inst["model"]["file"])
    assert os.path.isfile(res), f"Model file {res} does not exist."
    return res

def property_filename(inst):
    res = os.path.join(models_dir, inst["name"], inst["query"]["file"])
    assert os.path.isfile(res), f"Property file {res} does not exist."
    return res
    
def achievability_property_filename(inst, check_exists = True):
    res = os.path.join(models_dir, inst["name"], inst["id"] + "achievability.props")
    if not check_exists or os.path.isfile(res):
        return res
     
def get_category(inst):
    counts = inst["query"]["counts"]
    if counts["Lr"] + counts["Lp"] > 0:
        return "lra"
    elif counts["Br"] > 0:
        return "bnd" # reward bounded
    elif counts["Qp"] > 0:
        return "qu" # quantile
    elif counts["Bt"] + counts["Bs"] > 0:
        # print("Right now, we assume that there is no instance in category 'other' but {} violates this".format(inst["id"]))
        return "other"
    else:
        return "tot"
    
def separated_property_filename(inst):
    res = os.path.join(models_dir, inst["name"], inst["query"]["file"])
    name,ext = os.path.splitext(res)
    res = "{}-{}{}".format(name,inst["query"]["id"],ext)
    assert os.path.isfile(res), f"Property file {res} does not exist."
    return res

def split_property_filename(inst):
    if "file" not in inst["query"]: return None
    res = os.path.join(models_dir, inst["name"], inst["query"]["file"])
    name,ext = os.path.splitext(res)
    res = "{}-{}-split{}".format(name,inst["query"]["id"],ext)
    if os.path.isfile(res):
        return res
       
def get_query_prism(property_file, property_id):
    with open(property_file, 'r') as prFile:
        found = False
        for line in prFile:
            if '"{}":'.format(property_id) in line:
                assert not found, "Query id {} found multiple times".format(b["id"])
                found = True
                objectives_str = line
        assert found, "Query id {} not found".format(b["id"])
    if "//" in objectives_str: objectives_str = objectives_str[:objectives_str.find("//")]
    return objectives_str
    
def get_query_jani(jani_file, property_names):
    res = []
    with open(jani_file, 'r',  encoding='utf-8-sig') as jfile:
        jani_json = json.load(jfile)
        return [p for p in jani_json["properties"] if p["name"] in property_names]    
    

def is_mixed_multi(inst):
    if inst["query"]["counts"]["all"] < 2: return False
    if inst["model"]["formalism"] == "prism":
        objectives_str = get_query_prism(property_filename(inst), inst["query"]["id"])
        if objectives_str.find("multi(") < 0: return False
        objectives_str = objectives_str[objectives_str.find("multi(")+6:objectives_str.rfind(")")]
        has_min, has_max = False, False
        for obj in objectives_str.split(", "):
            assert "min=?" in obj or "max=?" in obj, f"{obj} doesn't say if its min or max ({objectives_str})"
            has_min = has_min or "min=?" in obj
            has_max = has_max or "max=?" in obj
        return has_min and has_max
    else:
        objectives = get_query_jani(model_filename(inst), inst["query"]["jani"])
        has_min, has_max = False, False
        for obj in objectives:
            operator = obj["expression"]["values"]["op"]
            assert operator in ["Emin", "Emax", "Pmin", "Pmax", "Smin", "Smax"]
            has_min = has_min or operator.endswith("min")
            has_max = has_max or operator.endswith("max")
        return has_min and has_max
        
        
    
# if last two characters of id are numeric, they encode the number of different reward assignments involved in reward bounds and the dimension of epochs
# Either a file_name or a jani_name shall be given
def create_query(identifier, file_name = None, jani_names = None):
    q = OrderedDict()
    q["id"] = identifier
    if file_name is not None:
        q["file"] = file_name
    elif jani_names is not None:
        q["jani"] = jani_names
    counts = Counter()
    objs = [identifier[i:i+2] for i in range(0,len(identifier),2)]
    for obj in objs:
        if obj.isnumeric():
            q["epoch-dim"] = int(obj[1])
            q["num-bnd-rew-structures"] = int(obj[0])
        else:
            assert obj in obj_types, f"{obj} not a known objective type" 
            counts[obj] += 1
    counts["all"] = sum(counts.values())
    q["counts"] = counts
    return q

def create_instance(inst_id, benchmark_name, formalism, model_type, query_id, model_parameters = None,  model_filename = None, query_filename = None, query_names = None):
    inst = OrderedDict()
    inst["id"] = inst_id
    inst["name"] = benchmark_name
    inst["model"] = OrderedDict()
    inst["model"]["formalism"] = formalism
    inst["model"]["type"] = model_type
    if model_parameters is not None:
        inst["model"]["parameters"] = model_parameters
    if formalism == "prism":
        inst["model"]["file"] = f"{benchmark_name}.prism" if model_filename is None else model_filename
        inst["query"] = create_query(query_id, file_name=f"{benchmark_name}.props" if query_filename is None else query_filename)
    elif formalism == "jani":
        inst["model"]["file"] = f"{benchmark_name}.jani" if model_filename is None else model_filename
        inst["query"] = create_query(query_id, jani_names = query_names)
    inst["query"]["mixed"] = is_mixed_multi(inst)
    return inst

def create_parameter_assignment(parameter_names, parameter_values):
    if type(parameter_values) is not tuple:
        return create_parameter_assignment(parameter_names, (parameter_values,))
    return OrderedDict(zip(parameter_names, parameter_values))

def create_inst_id(model_name, query_id, par_names, par_values, par_fill = None):
    # instance IDs shall not include "_"
    if type(par_values) is not tuple:
        return create_inst_id(model_name, query_id, par_names, (par_values,), par_fill)
    
    if par_fill is None:
        par_id = "".join(["{}{}".format(n,v) for n,v in zip(par_names, par_values)])
    else:
        par_id = "".join(["{}{:0{}}".format(n,v,f) for (n,v,f) in zip(par_names, par_values, par_fill)])
    result = "{}-{}-{}".format(model_name, par_id, query_id)
    assert "_" not in result
    assert "." not in result
    return result


instances = []

name = "csn"
parameter_names = ["N"]
parameter_values = [3,4,5]
for p in parameter_values:
    q = p*"Lr"
    inst_id = create_inst_id(name, q, parameter_names, p)
    instances.append(create_instance(inst_id, name, "prism", "mdp", q, None, f"{name}{p}.prism", f"{name}{p}.props"))    

name = "ejs"
parameter_names = ["N", "B", "Unf"]
parameter_zero_padding = ["1","3", "1"]
parameter_values = [(2,3),(3,5),(4,6),(5,8)]
queries = ["RtRt", "PfPf"]
for nb,q in itertools.product(parameter_values, queries):
    if q == "RtRt": unf = 1 # unfold global utility
    elif q == "Pf": unf = 2 # unfold global utility and global energy
    elif q == "PfPf": unf = 3 # unfold all
    else: unf = 0 # unfold nothing
    p = nb + (unf,)
    inst_id = create_inst_id(name, q, parameter_names, p, parameter_zero_padding)
    pars = create_parameter_assignment(parameter_names[1:], p[1:])
    instances.append(create_instance(inst_id, name, "prism", "mdp", q, pars, f"{name}{p[0]}.prism"))

name = "frw"
parameter_names = ["B", "Unf"]
parameter_zero_padding = ["5","1"]
queries = ["PfPf"]
for q in queries:
    if q == "Qp22":
        unf=0
        bnds=[0]
    else:
        unf = 1 if q in ["Pf", "PfPf"] else 0
        bnds = [500,10000]
    for b in bnds:
        pars = create_parameter_assignment(parameter_names + ["delay"], (b,unf,36))
        inst_id = create_inst_id(name, q, parameter_names, (b,unf), parameter_zero_padding)
        instances.append(create_instance(inst_id, name, "prism", "mdp", q, pars))

name = "phi"
parameter_names = ["N"]
parameter_values = [4,5,6]
queries = ["LrLr"]
for p,q in itertools.product(parameter_values, queries):
    inst_id = create_inst_id(name, q, parameter_names, p)
    instances.append(create_instance(inst_id, name, "prism", "mdp", q, None, f"{name}{p}.prism", f"{name}{p}.props"))    
    
name = "pow" # dpm in DKQR20
parameter_names = ["Q", "K"]
parameter_zero_padding = ["4", "4"]
parameter_values = [2,4,100,1000] # K value depends on query
queries1 = ["RtRt", "RtRtRt"]
queries2 = []
for p,q in itertools.product(parameter_values, queries1 + queries2):
    p2 = (p,0) if q in queries1 else (p,1000)
    inst_id = create_inst_id(name, q, parameter_names, p2, parameter_zero_padding)
    pars = create_parameter_assignment(parameter_names, p2)
    instances.append(create_instance(inst_id, name, "prism", "mdp", q, pars))

name = "rab" # mutex in QK21
parameter_names = ["N"]
parameter_values = [3,4,5]
queries = ["LrLr"]
for p,q in itertools.product(parameter_values, queries):
    inst_id = create_inst_id(name, q, parameter_names, p)
    instances.append(create_instance(inst_id, name, "prism", "mdp", q, None, f"{name}{p}.prism", f"{name}{p}.props"))    


name = "res" 
parameter_names = ["B", "CAP", "M", "Unf"]
parameter_zero_padding = ["3","1", "1", "1"]
for b,unf in itertools.product([5,10,100], [0,1]):
    p = (b, 1, 1, unf)
    pars = create_parameter_assignment(parameter_names, p)
    for q in ["PfPf"] if unf == 1 else []:
        inst_id = create_inst_id(name, q, parameter_names, p, parameter_zero_padding)
        instances.append(create_instance(inst_id, name, "prism", "mdp", q, pars))
for c in [5,15,20]:
    p = (100, c, c, 0)
    pars = create_parameter_assignment(parameter_names, p)
    for q in ["LrLr"]:
        inst_id = create_inst_id(name, q, parameter_names, p, parameter_zero_padding)
        instances.append(create_instance(inst_id, name, "prism", "mdp", q, pars))

name = "rov" 
parameter_names = ["B", "Unf"]
parameter_zero_padding = ["4","1"]
queries = ["RtRt", "PfPf"]
for b,q in itertools.product([10,20,30,100,500,1000], queries):
    if q == "RtRt": unf = 1 # unfold value
    elif q in ["Pf", "PfPf"]: unf = 2 # unfold value, time, energy
    else: unf = 0 # unfold nothing
    p = (b, unf)
    pars = create_parameter_assignment(parameter_names, p)
    inst_id = create_inst_id(name, q, parameter_names, p, parameter_zero_padding)
    instances.append(create_instance(inst_id, name, "prism", "mdp", q, pars))

name = "sen"
parameter_names = ["N"]
parameter_values = [1,2,3,4,5]
queries = ["LrLrLr"]
for p,q in itertools.product(parameter_values, queries):
    inst_id = create_inst_id(name, q, parameter_names, p)
    instances.append(create_instance(inst_id, name, "prism", "mdp", q, None, f"{name}{p}.prism", f"{name}{p}.props"))    

name = "srv"
parameter_names = ["B", "Unf"]
parameter_zero_padding = ["3","1"]
for p,q in [[(0,0), "RtRt"]]:
    pars = create_parameter_assignment(parameter_names, p)
    inst_id = create_inst_id(name, q, parameter_names, p, parameter_zero_padding)
    instances.append(create_instance(inst_id, name, "prism", "mdp", q, pars))

name = "tea"
parameter_names = ["N"]
parameter_values = [2,3,4,5]
queries = ["PfRt", "PfRtPf"]
for p,q in itertools.product(parameter_values, queries):
    inst_id = create_inst_id(name, q, parameter_names, p)
    instances.append(create_instance(inst_id, name, "prism", "mdp", q, None, f"{name}{p}.prism"))

name = "uav"
parameter_names = ["B", "Unf"]
parameter_zero_padding = ["4","1"]
parameter_values = [500,750,1000,1500]
queries = ["PfRt"]
for b,q in itertools.product(parameter_values, queries):
    if q in ["Pf", "PfRt"]: unf = 1
    else: unf = 0 
    pars = create_parameter_assignment(parameter_names + ["COUNTER"], (b,unf,0))
    inst_id = create_inst_id(name, q, parameter_names, (b,unf), parameter_zero_padding)
    instances.append(create_instance(inst_id, name, "prism", "mdp", q, pars))

name = "vir"
parameter_names = ["N"]
parameter_values = [2,3,4]
queries = ["LrLr"]
for p,q in itertools.product(parameter_values, queries):
    inst_id = create_inst_id(name, q, parameter_names, p)
    instances.append(create_instance(inst_id, name, "prism", "mdp", q, None, f"{name}{p}.prism", f"{name}{p}.props"))    


names = list(dict.fromkeys([i["name"] for i in instances]).keys())

def from_id(identifier):
    for b in instances:
        if b["id"] == identifier: return b

def get_unfolded_instance(inst):
    if "Br" not in inst["query"]["counts"]: return None
    matchingInstances = []
    for inst2 in instances:
        if inst2["name"] != inst["name"]: continue
        if "Br" in inst2["query"]["counts"]: continue
        if "Lr" in inst2["query"]["counts"]: continue
        if "Lp" in inst2["query"]["counts"]: continue
        if inst2["query"]["counts"]["all"] != inst["query"]["counts"]["all"]: continue
        matchingPars = True
        for p,v in inst2["model"]["parameters"].items():
            if p == "Unf" and v == 0: matchingPars = False
            if p != "Unf" and v != inst["model"]["parameters"][p]: matchingPars = False
        if not matchingPars: continue
        if inst["id"][:inst["id"].find("Unf")] != inst2["id"][:inst2["id"].find("Unf")]: continue
        if inst["name"] in ["ejs", "rov"] and inst2["query"]["id"] == "RtRt": continue
        matchingInstances.append(inst2)
    for inst2 in matchingInstances[1:]:
        assert matchingInstances[0]["id"] == inst2["id"], "{} has {} matching instances:\n\t{}".format(inst["id"], len(matchingInstances), "\n\t".join([inst2["id"] for inst2 in matchingInstances]))
    return matchingInstances[0]

def create_separated_property_files(): # creates one file for each property. Useful if tools can not parse all kinds of properties
    for b in instances:
        if "file" in b["query"]:
            objectives = get_query_prism(property_filename(b), b["query"]["id"])
            name,ext = os.path.splitext(property_filename(b))
            with open("{}-{}{}".format(name,b["query"]["id"],ext), 'w') as newfile:
                newfile.write(objectives)

def get_prism_instances_with_mixed_rewards(): # returns the instances where both a maximizing and a minimizing reward objective is checked. Doesn't include jani models.
    res = []
    for b in instances:
        num_rew_obj = sum([b["query"]["counts"][qid] for qid in ["Rt", "Rf"]])
        if num_rew_obj < 2: continue
        if "file" in b["query"]: # prism model
            objectives_str = get_query_prism(property_filename(b), b["query"]["id"])
            assert objectives_str.find("multi(") >= 0, f"{objectives_str} doesn't contain a multi operator"
            objectives_str = objectives_str[objectives_str.find("multi(")+6:objectives_str.rfind(")")]
            objectives = objectives_str.split(", ")
            assert len(objectives) == b["query"]["counts"]["all"], b["id"] + "{}".format(objectives)
            num_min, num_max = 0,0
            for obj in objectives:
                if (obj.startswith(r"R") or obj.startswith("T")) and not "LRA" in obj:
                    if "min=?" in obj: num_min += 1
                    elif "max=?" in obj: num_max += 1
            assert num_min + num_max == num_rew_obj, f"Weird objectives '{objectives_str}': found {num_min} minimizing, {num_max} maximizing, and {num_rew_obj} overall."
            if num_min > 0 and num_max > 0: res.append(b["id"])
    return res


def create_separated_property_files_split(): # creates one file for each multi property but splits the objectives into individual properties.
    for b in instances:
        if "file" in b["query"] and b["query"]["counts"]["all"] >= 2 and "Br" not in b["query"]["counts"]: #skip single objective or reward bounded objectives. The following code is broken for the latter as they may contain a ,
            objectives_str = get_query_prism(property_filename(b), b["query"]["id"])
            name,ext = os.path.splitext(property_filename(b))
            assert objectives_str.find("multi(") >= 0, line
            objectives_str = objectives_str[objectives_str.find("multi(")+6:objectives_str.rfind(")")]
            objectives = objectives_str.split(", ")
            assert len(objectives) == b["query"]["counts"]["all"], b["id"] + "{}".format(objectives)
            file_content = ";\n".join(objectives) + ";\n"
            with open("{}-{}-split{}".format(name,b["query"]["id"],ext), 'w') as newfile:
                newfile.write(file_content)

if __name__ == "__main__":
    #for b in instances:
    #    unf_b = get_unfolded_instance(b)
    #    if unf_b is not None:
    #        print(f"{b['id']} -> {unf_b['id']}")
    # print(json.dumps(instances,indent='\t'))
    # create_separated_property_files_split()
    print(f"{len(instances)} benchmarks")
    #print(get_prism_instances_with_mixed_rewards())
    
