from types import SimpleNamespace
import os
import subprocess
import sys

from feishu_stack.modules.backup_migration.backups import clean


def test_backup_retention_preserves_goal_and_newest(tmp_path):
    for i in range(3):
        path = tmp_path / f'config.toml.bak-switch-{i}'
        path.write_text('fixture', encoding='utf-8')
        os.utime(path, (i + 1, i + 1))
    goal = tmp_path / 'config.toml.bak-goal-keep'
    goal.write_text('fixture', encoding='utf-8')
    assert clean(SimpleNamespace(codex_home=tmp_path), keep=1).ok
    assert sorted(p.name for p in tmp_path.iterdir()) == [goal.name, 'config.toml.bak-switch-2']


def test_backup_service_does_not_load_model_provider():
    subprocess.run([sys.executable, '-c', '''
import sys
from feishu_stack.modules.backup_migration import backups
assert not any(n.startswith('feishu_stack.modules.model_provider') for n in sys.modules)
'''], check=True)
