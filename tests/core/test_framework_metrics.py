"""Host instrumentation must not load the diagnostics feature package."""
import os
from pathlib import Path
import subprocess
import sys


def test_framework_metrics_import_is_independent_and_legacy_alias_is_shared():
    root = Path(__file__).parents[2]
    env = {**os.environ, 'PYTHONPATH': str(root / 'src')}
    subprocess.run([sys.executable, '-c', '''
import sys
from feishu_stack.core import metrics
assert 'feishu_stack.modules.logs_diagnostics' not in sys.modules
from feishu_stack.modules.logs_diagnostics import metrics as legacy
assert legacy is metrics
metrics.record_operation('test', 'read', True)
assert b'acc_operations_total' in legacy.render_metrics()
'''], cwd=root, env=env, check=True)
