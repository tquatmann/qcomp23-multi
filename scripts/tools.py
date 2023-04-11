from collections import OrderedDict

import storm, epmc, prism, multigain
TOOLS = [storm, prism, epmc, multigain]
TOOL_NAMES = OrderedDict([[t.name, t] for t in TOOLS])

def config_from_id(tool, identifier):
    assert tool in TOOL_NAMES, f"Unknown tool '{tool}'"
    return TOOL_NAMES[tool].config_from_id(identifier)
