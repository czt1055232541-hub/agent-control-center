"""Install a real external distribution and discover it in a fresh ACC process."""

import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).parents[2]


def test_installed_external_plugin_routes_cards_and_disable(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "installed"
    shutil.copytree(ROOT / "examples" / "acc-example-plugin", source)
    installed = subprocess.run([
        sys.executable, "-m", "pip", "install", "--no-deps", "--no-build-isolation",
        "--no-index", "--target", str(target), str(source),
    ], capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert installed.returncode == 0, installed.stdout + installed.stderr
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(target), str(ROOT / "src")]),
           "ACC_DISABLED_PLUGINS": ""}
    program = """
from fastapi.testclient import TestClient
from feishu_stack.api.app import app
with TestClient(app) as client:
    inventory = client.get('/api/plugins').json()
    plugin = next(p for p in inventory['plugins'] if p['id'] == 'example.hello')
    assert plugin['cards'][0]['href'] == '/api/example/ui'
    assert client.get('/api/example/status').json() == {'ok': True, 'plugin': 'example.hello'}
    page = client.get(plugin['cards'][0]['href'])
    assert page.status_code == 200 and 'text/html' in page.headers['content-type']
    assert 'ACC Example' in page.text
"""
    subprocess.run([sys.executable, "-c", program], env=env, check=True)
    disabled = """
from fastapi.testclient import TestClient
from feishu_stack.api.app import app
with TestClient(app) as client:
    assert 'example.hello' not in {p['id'] for p in client.get('/api/plugins').json()['plugins']}
    assert client.get('/api/example/ui').status_code == 404
    assert client.get('/api/example/status').status_code == 404
    assert client.get('/api/health').status_code == 200
"""
    subprocess.run([sys.executable, "-c", disabled],
                   env={**env, "ACC_DISABLED_PLUGINS": "example.hello"}, check=True)
