import os, sys, json

import benchmarks
import storm

def load_json(path : str):
    with open(path, 'r', encoding='utf-8-sig') as json_file:
        return json.load(json_file, object_pairs_hook=dict)

if __name__ == "__main__":
    print("Generates achievability queries from 'split' logs.")
    print("Usages:")
    print("python3 {} path/to/first/logfiles/ path/to/second/logfiles/ ...    reads from multiple log file directories '".format(sys.argv[0]))
    print("")
    if (len(sys.argv) == 2 and sys.argv[1] in ["-h", "-help", "--help"]):
        exit(1)

    logdirs = []
    for arg in sys.argv[1:]:
        logdirs.append(arg)
    
    print("Selected log dir(s): {}".format(", ".join(logdirs)))
    print("")

    num = 0
    num_storm_fail = 0
    for logdir_input in logdirs:
        logdir = os.path.expanduser(logdir_input)
        if not os.path.isdir(logdir):
            print("Error: Directory '{}' does not exist.".format(logdir))

        print("\nGathering results from logfiles in {} ...".format(logdir))
        json_files = [ f for f in os.listdir(logdir) if f.endswith(".json") and os.path.isfile(os.path.join(logdir, f)) ]
        i = 0
        for execution_json in [ load_json(os.path.join(logdir, f)) for f in json_files ]:
            i += 1
            if execution_json["tool"] != storm.name or execution_json["configuration-id"] != "split": continue 
            inst_id = execution_json["benchmark-id"]
            inst = benchmarks.from_id(inst_id)
            with open(os.path.join(logdir, execution_json["log"]), 'r') as logfile:
                log = logfile.read()
            obj_results = []
            pos = 0
            for j in range(1, inst["query"]["counts"]["all"] + 1):
                pos = log.find(f'Model checking property "{j}": ')
                if pos < 0: break
                pos = log.find("Result (for initial states): ", pos)
                if pos < 0: break
                pos += len("Result (for initial states): ")
                pos2 = log.find("\n", pos)
                obj_results.append(float(log[pos:pos2]))
            if len(obj_results) < inst["query"]["counts"]["all"]:
                print("Unable to parse all {} objective results from {}".format(inst["query"]["counts"]["all"], execution_json["log"]))
                while len(obj_results) < inst["query"]["counts"]["all"]: obj_results.append(0.5)
                num_storm_fail += 1
            pareto_file_name = benchmarks.separated_property_filename(inst)
            with open(pareto_file_name, 'r') as paretofile:
                pareto = paretofile.read()
            achievability = pareto
            for obj_res in obj_results:
                delta = obj_res * 0.15 if obj_res != 0.0 else 0.15
                pos_min = achievability.find("min=?")
                pos_max = achievability.find("max=?")
                if pos_min >= 0:
                    if 0 <= pos_max < pos_min:
                        pos = pos_max
                    else:
                        pos = pos_min
                else:
                    assert pos_max>=0, "Neither min or max in {}".format(achievability)
                    pos = pos_max
                kind = achievability[pos-1]
                if kind == "}": kind = "R"
                if kind == "A" and achievability[pos-3:pos] == "LRA": kind = "LRA"
                assert kind in ["P", "R", "T", "LRA"], "Unexpected property kind '{}' in {} at position {}".format(kind, achievability, pos-1)
                opt = achievability[pos:pos+3]
                assert opt in ["min", "max"], "Unexpected property opt dir '{}' in {} at position {}".format(opt, achievability, pos)
                if kind in ["P", "LRA"]:
                    t_value = obj_res * 0.9 + (0.1 if opt == "min" else 0.0)
                else:
                    t_value = obj_res * (1.1 if opt == "min" else 0.9)
                    if t_value == 0.0: t_value = 1.0
                t_rel = "<=" if opt == "min" else ">="
                achievability = achievability[:pos] + f"{t_rel}{t_value}" + achievability[pos+len("opt=?"):]
            num+=1
            with open(benchmarks.achievability_property_filename(inst,check_exists=False), 'w') as ach_file:
                ach_file.write(achievability)
    print("Generated {} achievability queries.".format(num))
    print("There were {} instances where Storm could not solve all single-objective queries.".format(num_storm_fail))
            #print(achievability)
            
    
    
    
    
    
