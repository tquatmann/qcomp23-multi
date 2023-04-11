import os

def ask_user_for_info(description, default = None, validation = None):
    if default is None:
        resp = input(f"{description}: ")
    else:
        resp = input(f"{description} [{default}]: ")
        if resp == "": resp = default
    if validation is not None and not validation(resp):
        return ask_user_for_info(description, default, validation)
    return resp

def ask_user_yn(description):
    return ask_user_for_info(description + " (type 'y' or 'n')", validation=lambda usr_input : usr_input in ["y", "n"]) == "y"

def ask_user_overwrite_file(filename):
    if os.path.isfile(filename): 
        return ask_user_yn(f"File {filename} exists. Overwrite?")
    return True

def input_selection(item : str, options, single_choice = False):
    if not single_choice:
        if "a" in options: raise AssertionError("options should not include key 'a'")
        if "d" in options: raise AssertionError("options should not include key 'd'")
        if "c" in options: raise AssertionError("options should not include key 'c'")
    if len(options) == 0: raise AssertionError("options should not be empty.")
    longest_option_descriptions = []
    longest_option_descriptions.append(max([len(key) for key in options] + [4]) + 4)
    i = 0
    while True:
        longest = -1
        for key in options:
            if i < len(options[key]):
                longest = max(longest, len(options[key][i]))
        if longest >= 0:
            longest_option_descriptions.append(longest + 4)
        else:
            break
        i += 1
        
    selected_keys = []      
    while True:
        keys = []
        print("Select {}.".format(item))
        print("    Option" + " " * (longest_option_descriptions[0] - len("Option")) + "Description")
        print("----" + "-" * sum(longest_option_descriptions))
        for key in options:
            keys.append(key)
            description = ""
            for i in range(len(options[key])):
                description += "{}{}".format(options[key][i], " " * (longest_option_descriptions[i+1] - len(options[key][i])))
            print("{}{}{}".format("[X] " if key in selected_keys else "[ ] ", key + " " * (longest_option_descriptions[0] - len(key)), description))
        if not single_choice:
            keys.append("a")
            print("    {}Select all".format("a" + " " * (longest_option_descriptions[0] - 1)))
        if not single_choice and len(selected_keys) > 0:
            keys.append("c")
            print("    {}Clear selection".format("c" + " " * (longest_option_descriptions[0] - 1)))
            keys.append("d")
            print("    {}done".format("d" + " " * (longest_option_descriptions[0] - 1)))
        selection = input("Enter option: ")
        if selection in keys:            
            if selection in options:
                selected_keys.append(selection)
                if single_choice:
                    break
            elif selection == "a":
                selected_keys = keys[:len(options)]
                break
            elif selection == "d":
                break
            elif selection == "c":
                selected_keys = []
        else:
            print ("Invalid selection. Enter any of {} or press Ctrl+C to abort.".format(keys))  
    print("Selected {}: {}".format(item,selected_keys))
    return selected_keys