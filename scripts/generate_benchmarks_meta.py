import json,sys
import benchmarks
from collections import OrderedDict, Counter
import math

def load_json(path : str):
    with open(path, 'r', encoding='utf-8-sig') as json_file:
        return json.load(json_file, object_pairs_hook=OrderedDict)
        


categories = OrderedDict()
categories["Network protocols"] = ["csn", "frw", "sen", "tea", "wla"]
categories["Randomized algorithms"] = ["nnd", "phi"]
categories["Queueing systems"] = ["pol", "rqs", "str"]
categories["Planning"] = ["res", "rov", "srv", "uav"]
categories["Scheduling"] = ["clu", "dpm", "ejs", "mut", "pow", "rab"]
categories["Biology"] = ["vir"]

long_names = OrderedDict(
clu="Workstation cluster",
csn="Client-server mutex with $N$ fails",
dpm="Dynamic power management",
ejs="Energy-aware job scheduling",
frw="FireWire root contention protocol",
mut="Randomized mutex",
nnd="NAND multiplexing",
phi="Randomized dining philosophers",
pol="Polling system",
pow="Power management",
rab="Rabin randomized mutex",
res="Ressource gathering",
rov="Mars rover",
rqs="Reentrant queueing system",
sen="Sensor network",
srv="Service robot",
str="Video streaming client",
tea="Team formation protocols",
uav="UAV mission planning",
vir="Network virus infection",
wla="Wireless LAN"
)    

cites = OrderedDict(
clu="KNP12,HKPQR19,QK21",
csn="KPC12,KM17",
dpm="QWP99,HKPQR19",
ejs="BDDKK14,HKPQR19",
frw="KNP12,HKPQR19",
mut="TKPS12,QJK21",
nnd="KNP12,HKPQR19",
phi="LR81,BCFK15",
pol="TKPS12,QJK21",
pow="FKNPQ11",
rab="Rab82,BCFK15",
res="BN08,HKPQR19",
rov="HJKQ20",
rqs="HH12,HKPQR19",
sen="KPC12,KM17",
srv="LPH17,HJKQ20",
str="QJK21",
tea="CKPS11,FKP12",
uav="FWHT15",
vir="KNPV09,BCFK15",
wla="KNP12,HKPQR19"
)

num_instances = OrderedDict([(n, [0,0,0,0,0,0]) for n in benchmarks.names]) # all / with tot / with lra / with bnd-multi / with bnd-single / with quant
num_obj = OrderedDict([(n, []) for n in benchmarks.names]) 
formalism = OrderedDict()
model_type = OrderedDict()
for inst in benchmarks.instances:
    c = benchmarks.get_category(inst)
    if c == "tot" and inst["query"]["counts"]["all"] == 1: continue # skip single-obj total reward instances
    formalism[inst["name"]] = inst["model"]["formalism"]
    model_type[inst["name"]] = inst["model"]["type"]
    num_obj[inst["name"]].append(inst["query"]["counts"]["all"])
    num_instances[inst["name"]][0] += 1
    if c == "tot": num_instances[inst["name"]][1] += 1
    if c == "lra": num_instances[inst["name"]][2] += 1
    if c == "bnd":
        if inst["query"]["counts"]["all"] > 1:
            num_instances[inst["name"]][3] += 1
        else:
            num_instances[inst["name"]][4] += 1
    if c == "qu": num_instances[inst["name"]][5] += 1
    


print("Total number of instances: {}".format(sum([x[0] for x in num_instances.values()])))
num_states = OrderedDict([(n, []) for n in benchmarks.names]) 
assert len(sys.argv) == 2, "Missing argument. Please provide the benchmark_data.json file generated from postprocessing."
benchmark_data = load_json(sys.argv[1])
for d in benchmark_data.values():
    if d["category"] == "tot" and d["obj"] == 1:
        continue
    if "states" in d:
        num_states[d["name"]].append(d["states"])


def list_as_range(li):
    def to_readable_int(value):
        v = f"{value:.4g}"
        if "e+" in v: v = "{} {{\cdot}} 10^{{{}}}".format(round(float(v[:v.find("e+")])), int(v[v.find("e+")+2:]))
        return v
    assert len(li) > 0
    lower,upper = to_readable_int(min(li)),to_readable_int(max(li))
    if lower == upper: return f"${lower}$"
    return "${}..{}$".format(lower,upper)


# benchmark sources

out = r"""
\begin{tabular}{@{}ccl@{}}
\toprule
Application & Name & Description / Reference \\ \midrule
"""
for cat,names in categories.items():
    cat_col = [""] * len(names)
    mid = math.floor((len(names) - 1) / 2)
    for i in range(len(cat.split())):
        cat_col[mid + i] = cat.split()[i]
    for c,name in zip(cat_col, names):
        row = [f"{c}"]
        row.append(f"\\model{{{name}}}")
        row.append(f"{long_names[name]}~\\cite{{{cites[name]}}}")
        #assert formalism[name] in ["prism", "jani"]
        #row1.append("\\jani" if formalism[name] == "jani" else "\\prismlang")
        #row1.append(model_type[name].upper())
        #num_i = num_instances[name]
        #row1.append(f"{num_i[0]}/" + ",".join([f"{l}" for l in num_i[1:]]))
        #try:
        #    row1.append(list_as_range(num_obj[name]))
        #    row1.append(list_as_range(num_states[name]))
        #except AssertionError as ae:
        #    print("err: something is wrong with {}".format(name))
        out += "\t&\t".join(row) + "\t\\\\\n"
        #out += "\t&\t".join(row2) + "\t\\\\\n"
    out += "\\midrule\n"
out += r"""
\bottomrule
\end{tabular}
"""
# print(out)     



out = r"""
\begin{tabular}{@{}cccrrr@{}}
\toprule
\multirow{2}{*}{Name} & \multirow{2}{*}{Formalism} & \multirow{2}{*}{Type} & $\#\text{inst}\,/$ &  \multirow{2}{*}{$|\objs|$} &  \multirow{2}{*}{$|\states|$}  \\ 
&&&$\mathit{tot}, \mathit{lra}, \mathit{bnd}_{\text{m}}, \mathit{bnd}_{\text{s}}, \mathit{qu}$&&\\\midrule
"""
for cat,names in categories.items():
    for name in names:
        row = []
        row.append(f"\\model{{{name}}}")
        assert formalism[name] in ["prism", "jani"]
        row.append("\\jani" if formalism[name] == "jani" else "\\prismlang")
        row.append(model_type[name].upper())
        num_i = num_instances[name]
        row.append(f"${num_i[0]}\\,/\\," + ",".join([f"{l}" for l in num_i[1:]]) + "$")
        try:
            row.append(list_as_range(num_obj[name]))
            row.append(list_as_range(num_states[name]))
        except AssertionError as ae:
            print("err: something is wrong with {}".format(name))
        out += "\t&\t".join(row) + "\t\\\\\n"
    out += "\\midrule\n"
out += r"""
\bottomrule
\end{tabular}
"""
print(out) 


print("\n\n\n Further information:")
print("Inconsistent achievability results (true vs. false):")
for bench_id in sorted(benchmark_data.keys()):
    d = benchmark_data[bench_id]
    if "achievable" in d and len(d["achievable"]) > 1:
        print("\t{}:\t{} vs {}".format(d["id"], d["achievable"]['true'], d["achievable"]['false']))
        
