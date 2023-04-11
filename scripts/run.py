import json, traceback, sys, os
from collections import OrderedDict
from time import sleep

from executing import Execution
from commands import create_invocations

    
if __name__ == "__main__":
    print("Multi-objective verification benchmarking tool.")
    print("This script selects and executes benchmarks.")
    print("Usages:")
    print("python3 {}                 Creates an invocations file.".format(sys.argv[0]))
    print("python3 {} <filename>      Executes benchmarks from a previously created invocations file located at <filename>.".format(sys.argv[0]))
    print("python3 {} <filename> <i>  Executes the <i>th invocation (0 based) from a previously created invocations file located at <filename>.".format(sys.argv[0]))
    print("")
    if (len(sys.argv) == 2 and sys.argv[1] in ["-h", "-help", "--help"]) or len(sys.argv) > 3:
        exit(1)
        
    if len(sys.argv) == 1:
        input("No invocations file loaded. Press Return to create one now or CTRL+C to abort.")
        create_invocations()
    else:
        assert os.path.isfile(sys.argv[1]), f"Invocations file {sys.argv[1]} does not exist."
        with open(sys.argv[1], 'r', encoding='utf-8-sig') as json_file:
            invocations = json.load(json_file, object_pairs_hook=OrderedDict)
        print(f"Loaded {len(invocations)} invocations.")
        if len(sys.argv) == 3:
            assert sys.argv[2].isdigit(), f"Expected a non-negative number for second argument but got '{sys.argv[2]}' instead."
            selected_index = int(sys.argv[2])
            assert selected_index < len(invocations), f"Second argument is out of range: got {selected_index} but there are {len(invocations)} invocations."
            invocation_indices = [selected_index]
        else:
            invocation_indices = range(len(invocations))
        for i in invocation_indices:
            invocation = invocations[i]
            print(f"Executing invocation #{i}: {invocation['id']}")
            try:
                execution = Execution(invocation)
                execution_result = execution.run()
                json_file_path = os.path.join(invocation["log-dir"], os.path.splitext(invocation["log"])[0] + ".json")
                with open(json_file_path, 'w') as json_file:
                    json.dump(execution_result, json_file, ensure_ascii=False, indent='\t')
            except KeyboardInterrupt as e:
                print("\nInterrupt while processing invocation #{}: {}\n".format(i, invocation['id']))
                print("Continuing in 5 seconds")
                sleep(5)
            except Exception:
                print("ERROR while processing invocation #{}: {}".format(i, invocation['id']))
                traceback.print_exc()
            

    
    
    

    
    