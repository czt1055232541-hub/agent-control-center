import subprocess
import sys
from types import SimpleNamespace
from feishu_stack.modules.feishu_connection import auth


def test_auth_probe_is_owned_by_feishu():
    subprocess.run([sys.executable, '-c', '''
import sys
from feishu_stack.modules.feishu_connection.plugin import create_plugin
create_plugin().router_factory()
assert not any(n.startswith('feishu_stack.modules.logs_diagnostics') for n in sys.modules)
'''], check=True)


def test_probe_failure_is_structured_without_real_cli(monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError('simulated CLI failure')
    monkeypatch.setattr(auth, 'run_capture', fail)
    result = auth.lark_auth_status(SimpleNamespace(lark_cli_bin='test-cli', stack_root='.'))
    assert result['ok'] is False
    assert result['stderr'] == 'simulated CLI failure'
