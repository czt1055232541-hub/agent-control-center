import os
import subprocess
import sys


def test_builtin_discovery_does_not_import_business_modules():
    subprocess.run([sys.executable, '-c', '''
import sys
from feishu_stack.plugins import BUILTIN_PLUGINS
assert len(BUILTIN_PLUGINS) == 11
assert not any(name.startswith('feishu_stack.modules.') for name in sys.modules)
'''], check=True, env=os.environ.copy())


def test_framework_only_host_does_not_import_feature_implementations():
    subprocess.run([sys.executable, '-c', '''
import os, sys
from feishu_stack.plugins import BUILTIN_PLUGINS
os.environ['ACC_DISABLED_PLUGINS'] = ','.join(p.id for p in BUILTIN_PLUGINS if p.kind != 'framework')
from feishu_stack.api.app import app
features = [p.id.removeprefix('acc.').replace('-', '_') for p in BUILTIN_PLUGINS if p.kind != 'framework']
for name in features:
    assert not any(m == 'feishu_stack.modules.' + name or m.startswith('feishu_stack.modules.' + name + '.') for m in sys.modules), name
'''], check=True, env=os.environ.copy())
