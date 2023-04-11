import os, sys, subprocess, threading, time, signal, copy

if sys.version_info[0] < 3:
    sys.exit("You need to run this with Python 3. Try:\npython3 {}".format(" ".join(sys.argv)))

class CommandExecution(object):
    """ Represents the execution of a single command line argument. """
    def __init__(self):
        self.timelimit = None
        self.return_code = None
        self.output = None
        self.wall_time = None
        self.proc = None

    def stop(self):
        self.timelimit = True
        sys.stdout.write("sending termination request... ")
        sys.stdout.flush()
        try:
            os.killpg(os.getpgid(self.proc.pid), signal.SIGTERM) # Send the signal to all the process groups
        except ProcessLookupError:
            pass

    def send_sigkill(self):
        sys.stdout.write("killing process... ")
        sys.stdout.flush()
        try:
            os.killpg(os.getpgid(self.proc.pid), signal.SIGKILL) # Send the signal to all the process groups
        except ProcessLookupError:
            pass
            

    def run(self, command_line_str, timelimit):
        command_line_list = command_line_str.split()
        for i in range(len(command_line_list)): command_line_list[i] = os.path.expanduser(command_line_list[i])
        # We need to make sure that the process and all its childs are killed properly. Therefore, work with processgroups
        # From https://stackoverflow.com/a/4791612
        # The os.setsid() is passed in the argument preexec_fn so
        # it's run after the fork() and before  exec() to run the shell.
        self.proc = subprocess.Popen(command_line_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setsid)
        start_time = time.time()
        timer1 = threading.Timer(timelimit, self.stop)
        timer2 = threading.Timer(timelimit + 60, self.send_sigkill) # give the program 60 seconds to terminate by itself, send SIGKILL afterwards
        self.timelimit = False
        self.output = ""
        timer1.start()
        timer2.start()
        try:
            stdout, stderr = self.proc.communicate()
        except KeyboardInterrupt:
            stdout = None
            stderr = None
            self.output += "Execution aborted after {:.2f} seconds.\n".format(time.time() - start_time)
            sys.stdout.write("aborting after {:.2f} seconds ...".format(time.time() - start_time))
            sys.stdout.flush()
            # give the user time for another interrupt
            time.sleep(2)
        except Exception as e:
            self.output = self.output + "Error when executing the command:\n{}\n".format(e)
        finally:
            timer1.cancel()
            timer2.cancel()
            self.wall_time = time.time() - start_time
            self.return_code = self.proc.returncode
        if stdout is not None:
            self.output = self.output + stdout.decode('utf8')
        if stderr is not None and len(stderr) > 0:
            self.output = self.output + "\n" + "#"*30 + "Output to stderr" + "#"*30 + "\n" + stderr.decode('utf8')
        if self.timelimit and self.wall_time <= timelimit:
            print("WARN: A timelimit was triggered although the measured time is {} seconds which is still below the time limit of {} seconds".format(self.wall_time, timelimit))


def execute_command_line(command_line_str, timelimit):
    """
    Executes the given command line with the given time limit (in seconds).
    :returns the output of the command (including the output to stderr, if present), the runtime of the command and either the return code or None (in case of a timelimit)
    """
    execution = CommandExecution()
    execution.run(command_line_str, timelimit)
    if execution.timelimit:
        return execution.output, execution.wall_time, None
    else:
        return execution.output, execution.wall_time, execution.return_code


class Execution(object):
    def __init__(self, invocation_json):
        self.invocation = invocation_json
        self.wall_time = None
        self.logs = None
        self.timeout = None
        self.error = None
        self.return_codes = None

    def to_json(self):
        res = copy.deepcopy(self.invocation)
        if self.wall_time is not None:
            res["wallclock-time"] = self.wall_time
        if self.timeout is not None:
            res["timeout"] = self.timeout
        if self.error is not None:
            res["execution-error"] = self.error
        if self.return_codes is not None:
            res["return-codes"] = self.return_codes
        return res                   

    def run(self):
        self.error = False
        self.timeout = False
        self.wall_time = 0.0
        self.logs = []
        self.return_codes = []
        for command in self.invocation["commands"]:
            log, wall_time, return_code = execute_command_line(command, self.invocation["time-limit"] - self.wall_time)
            self.wall_time = self.wall_time + wall_time
            self.logs.append("Command:\t{}\nWallclock time:\t{}\nReturn code:\t{}\nOutput:\n{}\n".format(command, wall_time, return_code, log))
            if return_code is None:
                self.timeout = True
                self.error = False
                self.logs[-1] = self.logs[-1] + "\n" + "-"*10 + "\nComputation aborted after {} seconds since the total time limit of {} seconds was exceeded.\n".format(self.wall_time, self.invocation["time-limit"])
                self.return_codes.append(-9) # process got killed due to timeout
                break
            else:
                self.error = self.error or return_code != 0
                self.return_codes.append(return_code)
        # save logfile
        with open(os.path.join(self.invocation["log-dir"], self.invocation["log"]), 'w', encoding="utf-8") as logfile:
            hline = "\n" + "#" * 40 + "\n"
            logfile.write(hline.join(self.logs))
        return self.to_json()
