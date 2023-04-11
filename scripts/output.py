from collections import Counter,OrderedDict
import os

# Reads an execution result in json format and detects if it indicates an error due to not supporting the benchmark
def is_not_supported(result_json):
    return result_json["not-supported"]

def is_ignored(result_json):
    return False

def is_expected_error(result_json):
    return result_json["expected-error"]

def is_memout(result_json):
    return "memout" in result_json and result_json["memout"]
     
def get_runtime(result_json):
    if "wallclock-time" in result_json:
        return result_json["wallclock-time"]
    else:
        raise AssertionError("no runtime in {}".format(result_json))
        
def has_result(result_json):
    return "has-result" in result_json and result_json["has-result"]

def ensure_directory(path : str):
    if not os.path.exists(path):
        os.makedirs(path)

# Generates a csv containing runtimes. A row corresponds to a benchmark, a column corresponds to a tool/config combination.
# The first three columns contain the benchmark id, the model type, and the original format
# The last column contains the lowest runtime of the corresponding rows.
def generate_scatter_csv(exec_data, benchmarks, tools_configs):
    MIN_VALUE = 1 # runtimes will be set to max(MIN_VALUE, actual runtime)
    MAX_VALUE = 512 # runtimes will be set to min(MAX_VALUE, actual runtime)
    TO_VALUE = 724 # timeout
    MO_VALUE = 724 # Out of memory
    NA_VALUE = 724 # not available
    NS_VALUE = 724 # not supported
    #INC_VALUE = 724 # Incorrect result
    ERR_VALUE = 724 # error
    ND_VALUE = 724 # not displayed
    
    result = [ ["benchmark", "Type", "Orig", "Obj", "States"] + ["{}.{}".format(t,c) for (t,c) in tools_configs] + ["best"] ]
    for benchmark_id in benchmarks:
        benchmark = benchmarks[benchmark_id]
        
        row = [benchmark_id, benchmark["model"]["type"], benchmark["model"]["formalism"], benchmark["query"]["counts"]["all"], "TODOSTATES"]
        best_value = NA_VALUE
        for (tool, config) in tools_configs:
            value = NA_VALUE
            if benchmark_id in exec_data[tool][config]:
                res_json = exec_data[tool][config][benchmark_id]
                if is_ignored(res_json):
                    value = ND_VALUE
                elif "timeout" in res_json and res_json["timeout"] == True:
                    value = TO_VALUE
                #elif "result-correct" in res_json and res_json["result-correct"] == False:
                    #value = INC_VALUE
                elif is_memout(res_json):
                  value = MO_VALUE
                elif is_not_supported(res_json):
                    value = NS_VALUE
                elif is_expected_error(res_json):
                    value = ERR_VALUE
                elif has_result(res_json):
                    value = min(MAX_VALUE, max(MIN_VALUE,get_runtime(res_json)))
                    best_value = min(best_value, value)
                else:
                    print(f"Unexpected outcome for {res_json['id']}")
            row.append(str(value))
        row.append(str(best_value))
        result.append(row)
    return result


# Generates a csv containing runtimes. The first column denotes the row indices. Each of the remaining column corresponds to a tool/config combination. The last column corresponds to the fastest tool/config
# An entry in the ith row corresponds to the runtime of the ith fastest benchmark
def generate_quantile_csv(exec_data, benchmarks, tools_configs):
    MIN_VALUE = 0.1 # runtimes will be set to max(MIN_VALUE, actual runtime)
    runtimes_best_dict = OrderedDict()
    for (t,c) in tools_configs:
        runtimes_best_dict[t] = OrderedDict()
    result = [ ["n"] + ["{}.{}shifted".format(t,c) for (t,c) in tools_configs]  + ["{}.bestshifted".format(tool) for tool in runtimes_best_dict]] # append 'shifted' for compatibility with qcomp latex
    runtimes = OrderedDict()
    for (tool, config) in tools_configs:
        runtimes_tc = []
        for benchmark_id in benchmarks:
            if benchmark_id in exec_data[tool][config]:
                res_json = exec_data[tool][config][benchmark_id]
                if has_result(res_json):
                    runtimes_tc.append(max(MIN_VALUE,get_runtime(res_json)))
                    if benchmark_id not in runtimes_best_dict[tool]:
                        runtimes_best_dict[tool][benchmark_id] = runtimes_tc[-1]
                    else:
                        runtimes_best_dict[tool][benchmark_id] = min(runtimes_best_dict[tool][benchmark_id], runtimes_tc[-1])
        runtimes_tc.sort()
        runtimes["{}.{}".format(tool,config)] = runtimes_tc
    for tool in runtimes_best_dict:
        runtimes_best = [ runtimes_best_dict[tool][b] for b in runtimes_best_dict[tool] ]
        runtimes_best.sort()
        runtimes["{}.best".format(tool)] = runtimes_best
    for i in range(len(benchmarks)):
        row = [str(i+1)]
        for tc in runtimes:
            if i < len(runtimes[tc]):
                row.append(str(runtimes[tc][i]))
            else:
                row.append("")
        result.append(row)
    print("Correctly solved benchmarks (of {}):".format(len(benchmarks)))
    for tc in sorted(runtimes):
        print("\t{}: {}".format(tc, len(runtimes[tc])))
    return result

def generate_summary_table(exec_data, benchmarks, tools_configs):
    solved=Counter()
    solved_fastest1=Counter()
    solved_fastest2=Counter()
    not_supported=Counter()
    timeout=Counter()
    memout=Counter()
    incorrect=Counter()
    error=Counter()
    for benchmark_id in benchmarks:
        best_value = 100000
        solving_times = dict()
        for (tool, config) in tools_configs:
            if benchmark_id in exec_data[tool][config]:
                res_json = exec_data[tool][config][benchmark_id]
                if "timeout" in res_json and res_json["timeout"] == True:
                    timeout[(tool,config)] += 1
                elif is_memout(res_json):
                    memout[(tool,config)] += 1
                elif is_not_supported(res_json):
                    not_supported[(tool,config)] += 1
                elif is_expected_error(res_json):
                    error[(tool,config)] += 1
                elif has_result(res_json):
                    solved[(tool,config)] += 1
                    solving_times[(tool,config)] = value
                    if value < best_value:
                        best_value = value
                else:
                    print("Unexpected execution result for '{}.{}.{}'".format(tool, config, benchmark_id))
            else:
                not_supported[(tool,config)] += 1
        # count fastest
        for tc in solving_times:
            if solving_times[tc] <= 1.01 * best_value:
                solved_fastest1[tc] += 1
            if solving_times[tc] <= 1.5 * best_value:
                solved_fastest2[tc] += 1
        solved["best"] += min(len(solving_times),1)
    result = r"""\begin{tabular}{rrrr}""" + "\n"
    result += r"""solver & \#solved & \#incorrect & \#no result """
    result += "\\\\\\hline\n"
    for (t,c) in tools_configs:
        result += "{} & \t{} & \t{} & \t{}".format(r"\solver{" + t + "." + c + r"}",solved[(t,c)],incorrect[(t,c)], timeout[(t,c)] + memout[(t,c)] + error[(t,c)] + not_supported[(t,c)]) + "\\\\\n"
    result += r"""\end{tabular}""" + "\n"
    
    
    result += "\n\n\n" + r"""\begin{tabular}{r|""" + "r" * len(tools_configs) + """}""" + "\n"
    for (t,c) in tools_configs:
         result += "\t& " +   r"""\multicolumn{1}{c}{\rotatebox{90}{\engine{""" + "{}.{}".format(t,c) + "}}}\n"
    result += "\\\\\\hline\n"
    result += """\#solved     &""" + "\t&".join([" {}".format(solved[tc]) for tc in tools_configs]) + "\\\\\n"
    result += """\#not supp.  &""" + "\t&".join([" {}".format(not_supported[tc]) for tc in tools_configs]) + "\\\\\n"
    result += """\#time-outs  &""" + "\t&".join([" {}".format(timeout[tc]) for tc in tools_configs]) + "\\\\\n"
    result += """\#mem-outs   &""" + "\t&".join([" {}".format(memout[tc]) for tc in tools_configs]) + "\\\\\n"
    result += """\#incorrect  &""" + "\t&".join([" {}".format(incorrect[tc]) for tc in tools_configs]) + "\\\\\n"
    result += """\#error      &""" + "\t&".join([" {}".format(error[tc]) for tc in tools_configs]) + "\\\\\n"
    result += """\#fastest101 &""" + "\t&".join([" {}".format(solved_fastest1[tc]) for tc in tools_configs]) + "\\\\\n"
    result += """\#fastest150 &""" + "\t&".join([" {}".format(solved_fastest2[tc]) for tc in tools_configs]) + "\\\\\n"
    result += r"""\end{tabular}""" + "\n"
    result += "% A total of {} instances could be solved.".format(solved["best"])
    return result 
     

# Aux function for writing in files with proper indention
def write_line(file, indention, content):
    file.write("\t"*indention + content + "\n")

# Generates an html log page for the given result within output_dir/logs/
def create_log_page(result_json, output_dir):
    b = result_json["benchmark"]
    if not "log" in result_json:
        raise AssertionError("Expected a log file.")
    with open(result_json["log"], 'r') as logfile:
        logs = logfile.read().split("#" * 40)
    f_path = os.path.join("logs/", os.path.basename(result_json["log"])[:-4] + ".html")
    with open(os.path.join(output_dir, f_path), 'w') as f:
        indention = 0
        write_line(f, indention, "<!DOCTYPE html>")
        write_line(f, indention, "<html>")
        write_line(f, indention, "<head>")
        indention += 1
        write_line(f, indention, '<meta charset="UTF-8">')
        write_line(f, indention, "<title>{}.{} - {}</title>".format(result_json["tool"], result_json["configuration-id"], b["id"]))
#        write_line(f, indention, '<link rel="stylesheet" type="text/css" href="{}">'.format("http://qcomp.org/style.css")) # TODO: Might want to add another style
        write_line(f, indention, '<link rel="stylesheet" type="text/css" href=../style.css>') # TODO: Might want to add another style
        indention -= 1
        write_line(f, indention, '</head>')
        write_line(f, indention, '<body>')
        write_line(f, indention, '<h1>{}.{}</h1>'.format(result_json["tool"],result_json["configuration-id"]))

        write_line(f, indention, '<div class="box">')
        indention += 1
        write_line(f, indention, '<div class="boxlabelo"><div class="boxlabelc">Benchmark</div></div>')
        write_line(f, indention, '<table style="margin-bottom: 0.75ex;">')
        indention += 1
        write_line(f, indention, '<tr><td>id:</td><td>{} ({})</td></tr>'.format(b["id"], b["model"]["type"].upper()))
        indention -= 1
        write_line(f, indention, "</table>")
        indention -= 1
        write_line(f, indention, "</div>")

        write_line(f, indention, '<div class="box">')
        indention += 1
        write_line(f, indention, '<div class="boxlabelo"><div class="boxlabelc">Invocation ({})</div></div>'.format(result_json["configuration-id"]))
        f.write('\t' * indention + '<pre style="overflow: auto; padding-bottom: 1.5ex; padding-top: 1ex; font-size: 15px; margin-bottom: 0ex;  margin-top: 0ex;">')
        commands_str = "\n".join(result_json["commands"])
        f.write(commands_str)
        f.write('</pre>\n')
        write_line(f, indention, result_json["invocation-note"])
        indention -= 1
        write_line(f, indention, "</div>")

        write_line(f, indention, '<div class="box">')
        indention += 1
        write_line(f, indention, '<div class="boxlabelo"><div class="boxlabelc">Execution</div></div>')
        write_line(f, indention, '<table style="margin-bottom: 0.75ex;">')
        indention += 1
        if result_json["timeout"]:
            write_line(f, indention, '<tr><td>Walltime:</td><td style="color: red;">&gt {}s (Timeout)</td></tr>'.format(result_json["time-limit"]))
        else:
            write_line(f, indention, '<tr><td>Walltime:</td><td style="tt">{}s</td></tr>'.format(result_json["wallclock-time"]))
            if "model-checking-time" in result_json:
                write_line(f, indention, '<tr><td>Model Checking Walltime:</td><td style="tt">{}s</td></tr>'.format(result_json["model-checking-time"]))
            return_codes = []
            if "return-codes" in result_json:
                return_codes = result_json["return-codes"]
            if result_json["execution-error"]:
                write_line(f, indention, '<tr><td>Return code:</td><td style="tt; color: red;">{}</td></tr>'.format(", ".join([str(rc) for rc in return_codes])))
            else:
                write_line(f, indention, '<tr><td>Return code:</td><td style="tt">{}</td></tr>'.format(", ".join([str(rc) for rc in return_codes])))
        first = True
        for note in result_json["notes"]:
            write_line(f, indention, '<tr><td>{}</td><td>{}</td></tr>'.format("Note(s):" if first else "", note))
            first = False
        indention -= 1
        write_line(f, indention, "</table>")
        indention -= 1
        write_line(f, indention, "</div>")

        for log in logs:
            pos = log.find("\n", log.find("Output:\n")) + 1
            pos_end = log.find("#############################", pos)
            if pos_end < 0:
                pos_end = len(log)
            log_str = log[pos:pos_end].strip()
            if len(log_str) != 0:
                write_line(f, indention, '<div class="box">')
                indention += 1
                write_line(f, indention, '<div class="boxlabelo"><div class="boxlabelc">Log</div></div>')
                f.write("\t" * indention + '<pre style="overflow:auto; padding-bottom: 1.5ex">')
                f.write(log_str)
                write_line(f, indention, '</pre>')
                indention -= 1
                write_line(f, indention, "</div>")

            pos = log.find("##############################Output to stderr##############################\n")
            if pos >= 0:
                pos = log.find("\n", pos) + 1
                write_line(f, indention, '<div class="box">')
                indention += 1
                write_line(f, indention, '<div class="boxlabelo"><div class="boxlabelc">STDERR</div></div>')
                f.write("\t" * indention + '<pre style="overflow:auto; padding-bottom: 1.5ex">')
                pos_end = log.find("#############################", pos)
                if pos_end < 0:
                    pos_end = len(log)
                f.write(log[pos:pos_end].strip())
                write_line(f, indention, '</pre>')
                indention -= 1
                write_line(f, indention, "</div>")
        write_line(f, indention, "</body>")
        write_line(f, indention, "</html>")
    return f_path

# Generates an interactive html table from the results
def generate_table(exec_data, benchmarks, tools_configs, output_dir):
    SHOW_UNSUPPORTED = True # Also add entries for benchmarks that are known to be unsupported
    
    ensure_directory(output_dir)
    ensure_directory(os.path.join(output_dir, "logs/"))
    
    first_tool_col = 6
    num_cols = first_tool_col + len(tools_configs)

    with open (os.path.join(output_dir, "table.html"), 'w') as tablefile:
        tablefile.write(r"""<!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <title>Benchmark results</title>
      <link rel="stylesheet" type="text/css" href="style.css">
      <link rel="stylesheet" type="text/css" href="https://cdn.datatables.net/1.10.13/css/jquery.dataTables.min.css">
      <link rel="stylesheet" type="text/css" href="https://cdn.datatables.net/buttons/1.2.4/css/buttons.dataTables.min.css">
      <link rel="stylesheet" type="text/css" href="https://cdn.datatables.net/fixedheader/3.1.2/css/fixedHeader.dataTables.min.css">

      <script type="text/javascript" language="javascript" charset="utf8" src="https://code.jquery.com/jquery-1.12.4.js"></script>
      <script type="text/javascript" language="javascript" charset="utf8" src="https://cdn.datatables.net/1.10.13/js/jquery.dataTables.min.js"></script>
      <script type="text/javascript" language="javascript" charset="utf8" src="https://cdn.datatables.net/fixedheader/3.1.2/js/dataTables.fixedHeader.min.js"></script>
      <script type="text/javascript" language="javascript" charset="utf8" src="https://cdn.datatables.net/buttons/1.2.4/js/dataTables.buttons.min.js"></script>
      <script type="text/javascript" language="javascript" charset="utf8" src="https://cdn.datatables.net/buttons/1.2.4/js/buttons.colVis.min.js"></script>

      <script>
        $(document).ready(function() {
          // Set correct file
          $("#content").load("data.html");
        } );

        function updateBest(table) {
          // Remove old best ones
          table.cells().every( function() {
            $(this.node()).removeClass("best");
          });
          table.rows().every( function ( rowIdx, tableLoop, rowLoop ) {
              var bestValue = -1
              var bestIndex = -1
              $.each( this.data(), function( index, value ){
                if (index > 5 && table.column(index).visible()) {
    			    var text = $(value).text()
    	            if (["TO", "ERR", "INC", "MO", "NS", ""].indexOf(text) < 0) {
    				    var number = parseFloat(text);
    	                if (bestValue == -1 || bestValue > number) {
    	                  // New best value
    	                  bestValue = number;
    	                  bestIndex = index;
    	                }
    				  }
    			  }
              });
              // Set new best
              if (bestIndex >= 0) {
                $(table.cell(rowIdx, bestIndex).node()).addClass("best");
              }
          } );
      }
      </script>
    </head>
    """)
        indention = 0
        write_line(tablefile, indention, "<body>")
        write_line(tablefile, indention, "<div>")
        indention +=1
        write_line(tablefile, indention, '<table id="table" class="display">')
        indention += 1
        write_line(tablefile, indention, '<thead>')
        indention += 1
        write_line(tablefile, indention, '<tr>')
        indention += 1
        for head in ["Model", "Type", "Original", "Parameters", "Property", "NumObj"] + ["{}.{}".format(t,c) for (t,c) in tools_configs]:
            write_line(tablefile, indention, '<th>{}</th>'.format(head))
        indention -= 1
        write_line(tablefile, indention, '</tr>')
        indention -= 1
        write_line(tablefile, indention, '</thead>')
        write_line(tablefile, indention, '<tbody>')
        indention += 1

        for benchmark_id in benchmarks:
            b = benchmarks[benchmark_id]
            write_line(tablefile, indention, '<tr>')
            indention += 1
            write_line(tablefile, indention, '<td>{}</td>'.format(b["name"]))
            write_line(tablefile, indention, '<td>{}</td>'.format(b["model"]["type"]))
            write_line(tablefile, indention, '<td>{}</td>'.format(b["model"]["formalism"]))
            if "parameters" in b["model"]:
                write_line(tablefile, indention, '<td>{}</td>'.format(",".join([f"({p}={v})" for p,v in b["model"]["parameters"].items()])))
            else:
                write_line(tablefile, indention, '<td>-</td>')
            write_line(tablefile, indention, '<td>{}</td>'.format(b["query"]["id"]))
            write_line(tablefile, indention, '<td>{}</td>'.format(b["query"]["counts"]["all"]))
            for (t,c) in tools_configs:
                cell_content = ""
                if benchmark_id in exec_data[t][c]:
                    res_json = exec_data[t][c][benchmark_id]
                    link_attributes = ""
                    if is_ignored(res_json):
                        res_str = "-"
                        link_attributes = " class='ignore'"
                    if "timeout" in res_json and res_json["timeout"] == True:
                        res_str = "TO"
                        link_attributes = " class='timeout'"
                    elif is_memout(res_json):
                        res_str = "MO"
                        link_attributes = " class='memout'"
                    elif is_not_supported(res_json):
                        res_str = "NS" if SHOW_UNSUPPORTED else None
                        link_attributes = " class='unsupported'"
                    elif is_expected_error(res_json):
                        res_str = "ERR"
                        link_attributes = " class='error'"
                    elif has_result(res_json):
                        res_str = "%.1f" % get_runtime(res_json)
                    else:
                        print(f"Unexpected outcome for {res_json['id']}")
                    if res_str is not None:
                        logpage = create_log_page(res_json, output_dir)
                        cell_content = "<a href='{}' {}>{}</a>".format(logpage, link_attributes, res_str)
                write_line(tablefile, indention, '<td>{}</td>'.format(cell_content))
            indention -= 1
            write_line(tablefile, indention, '</tr>')
        indention -= 1
        write_line(tablefile, indention, '</tbody>')
        indention -= 1
        indention -= 1
        write_line(tablefile, indention, '</table>')
        write_line(tablefile, indention, "<script>")
        indention +=1
        write_line(tablefile, indention, 'var table = $("#table").DataTable( {')
        indention += 1
        write_line(tablefile, indention, '"paging": false,')
        write_line(tablefile, indention, '"autoWidth": false,')
        write_line(tablefile, indention, '"info": false,')
        write_line(tablefile, indention, 'fixedHeader: {')
        indention += 1
        write_line(tablefile, indention, '"header": true,')
        indention -= 1
        write_line(tablefile, indention, '},')
        write_line(tablefile, indention, '"dom": "Bfrtip",')
        write_line(tablefile, indention, 'buttons: [')
        indention += 1
        for columnIndex in range(first_tool_col, num_cols):
            write_line(tablefile, indention, '{')
            indention += 1
            write_line(tablefile, indention, 'extend: "columnsToggle",')
            write_line(tablefile, indention, 'columns: [{}],'.format(columnIndex))
            indention -= 1
            write_line(tablefile, indention, "},")
        tool_columns = [i for i in range(first_tool_col, num_cols)]
        for text, show, hide in zip(["Show all", "Hide all"], [tool_columns, []], [[], tool_columns]):
            write_line(tablefile, indention, '{')
            indention += 1
            write_line(tablefile, indention, 'extend: "colvisGroup",')
            write_line(tablefile, indention, 'text: "{}",'.format(text))
            write_line(tablefile, indention, 'show: {},'.format(show))
            write_line(tablefile, indention, 'hide: {}'.format(hide))
            indention -= 1
            write_line(tablefile, indention, "},")
        indention -= 1
        write_line(tablefile, indention, "],")
        indention -= 1
        write_line(tablefile, indention, "});")
        indention -= 1
        write_line(tablefile, indention, "")
        indention += 1
        write_line(tablefile, indention, 'table.on("column-sizing.dt", function (e, settings) {')
        indention += 1
        write_line(tablefile, indention, "updateBest(table);")
        indention -= 1
        write_line(tablefile, indention, "} );")
        indention -= 1
        write_line(tablefile, indention, "")
        indention += 1
        write_line(tablefile, indention, "updateBest(table);")
        indention -= 1
        write_line(tablefile, indention, "</script>")
        indention -= 1
        write_line(tablefile, indention, "</div>")
        write_line(tablefile, indention, "</body>")
        write_line(tablefile, indention, "</html>")

    with open (os.path.join(output_dir, "style.css"), 'w') as stylefile:
#        write_line(stylefile, 0, '@import url("{}");'.format(os.path.join(qcomp_root, "fonts/Tajawal/Tajawal.css"))) #TODO
        stylefile.write(r"""

    .best {
        background-color: lightgreen;
    }
    .error {
    	font-weight: bold;
    	background-color: lightcoral;
    }
    .incorrect {
        background-color: orange;
    	font-weight: bold;
    }
    .timeout {
        background-color: lightgray;
    }
    .memout {
        background-color: lightgray;
    }
    .unsupported {
        background-color: yellow;
    }
    .ignored {
        background-color: blue;
    }

    h1 {
    	font-size: 28px; font-weight: bold;
    	color: #000000;
    	padding: 1px; margin-top: 20px; margin-bottom: 1ex;
    }

    tt, .tt {
    	font-family: 'Courier New', monospace; line-height: 1.3;
    }

    .box {
    	margin: 2.5ex 0ex 1ex 0ex; border: 1px solid #D0D0D0; padding: 1.6ex 1.5ex 1ex 1.5ex; position: relative;
    }

    .boxlabelo {
    	position: absolute; pointer-events: none; margin-bottom: 0.5ex;
    }

    .boxlabel {
    	position: relative; top: -3.35ex; left: -0.5ex; padding: 0px 0.5ex; background-color: #FFFFFF; display: inline-block;
    }
    .boxlabelc {
    	position: relative; top: -3.17ex; left: -0.5ex; padding: 0px 0.5ex; background-color: #FFFFFF; display: inline-block;
    }
    """)
