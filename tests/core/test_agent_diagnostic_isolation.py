import subprocess
import sys


def test_agent_plugin_does_not_load_diagnostics():
    subprocess.run([sys.executable, '-c', '''
import sys
from feishu_stack.modules.agent_array.plugin import create_plugin
create_plugin().router_factory()
assert not any(n.startswith('feishu_stack.modules.logs_diagnostics') for n in sys.modules)
'''], check=True)
