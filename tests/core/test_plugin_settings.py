"""Persistent framework preferences never mutate running plugin ownership."""
import json
import os
import subprocess
import sys
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from feishu_stack import plugins
from feishu_stack.api import security
from feishu_stack.plugin_runtime import PluginRegistry
from feishu_stack.plugin_sdk import AccPlugin
from feishu_stack.plugins import settings


@pytest.fixture
def setup(monkeypatch, tmp_path):
    monkeypatch.delenv('ACC_DISABLED_PLUGINS', raising=False)
    path = tmp_path / 'plugin-settings.local.json'
    monkeypatch.setattr(settings, 'settings_path', lambda: path)
    registry = PluginRegistry([
        AccPlugin(id='framework', name='Framework', version='1', description='', kind='framework'),
        AccPlugin(id='provider', name='Provider', version='1', description='', requires=('framework',)),
        AccPlugin(id='consumer', name='Consumer', version='1', description='', requires=('provider',)),
    ])
    monkeypatch.setattr(plugins, 'get_plugin_registry', lambda: registry)
    monkeypatch.setattr(security, 'get_or_create_token', lambda: 'test-only')
    app = FastAPI()
    app.include_router(plugins.create_plugin_router())
    return TestClient(app), registry, path


def test_settings_auth_validation_and_no_side_effects(setup):
    client, registry, path = setup
    for headers, expected in [({}, 401), ({'X-Control-Token': 'wrong'}, 403)]:
        assert client.put('/api/plugins/settings', json={'disabled': ['provider', 'consumer']}, headers=headers).status_code == expected
        assert not path.exists()
    for disabled in [['framework'], ['missing'], ['provider'], [1]]:
        result = client.put('/api/plugins/settings', json={'disabled': disabled}, headers={'X-Control-Token': 'test-only'})
        assert result.status_code == 422
        assert not path.exists()


def test_save_restart_boundary_and_backup(setup):
    client, registry, path = setup
    headers = {'X-Control-Token': 'test-only'}
    result = client.put('/api/plugins/settings', json={'disabled': ['consumer', 'provider']}, headers=headers)
    assert result.status_code == 200
    assert result.json()['restart_required'] is True
    assert len(registry.resolve()) == 3
    assert settings.effective_disabled() == ('consumer', 'provider')
    restarted = PluginRegistry(registry.installed, disabled=settings.effective_disabled())
    assert [p.id for p in restarted.resolve()] == ['framework']
    assert settings.snapshot(restarted)['restart_required'] is False
    original = path.read_bytes()
    assert client.put('/api/plugins/settings', json={'disabled': []}, headers=headers).status_code == 200
    assert path.with_suffix('.json.bak').read_bytes() == original
    assert not list(path.parent.glob('.plugin-settings-*.tmp'))


def test_settings_remain_accessible_with_all_features_disabled(setup, monkeypatch):
    client, registry, path = setup
    disabled = PluginRegistry(registry.installed, disabled=['provider', 'consumer'])
    monkeypatch.setattr(plugins, 'get_plugin_registry', lambda: disabled)
    assert len(client.get('/api/plugins').json()['plugins']) == 1
    result = client.get('/api/plugins/settings')
    assert result.status_code == 200
    assert len(result.json()['plugins']) == 3


@pytest.mark.parametrize('override', ['', 'consumer'])
def test_environment_override_is_explicit_and_read_only(setup, monkeypatch, override):
    client, registry, path = setup
    settings.save_disabled(registry, ['provider', 'consumer'])
    before = path.read_bytes()
    monkeypatch.setenv('ACC_DISABLED_PLUGINS', override)
    assert client.get('/api/plugins/settings').json()['environment_override'] is True
    assert settings.effective_disabled() == (() if not override else ('consumer',))
    assert client.put('/api/plugins/settings', json={'disabled': []}, headers={'X-Control-Token': 'test-only'}).status_code == 409
    assert path.read_bytes() == before


def test_failed_atomic_replace_preserves_current_file(setup, monkeypatch):
    _, registry, path = setup
    settings.save_disabled(registry, ['consumer'])
    before = path.read_bytes()
    def fail(*args):
        raise OSError('simulated disk failure')
    monkeypatch.setattr(settings.os, 'replace', fail)
    with pytest.raises(OSError):
        settings.save_disabled(registry, [])
    assert path.read_bytes() == before
    assert not list(path.parent.glob('.plugin-settings-*.tmp'))


def test_real_host_reads_saved_preferences_and_settings_can_reenable(setup):
    _, _, path = setup
    registry = PluginRegistry(plugins.BUILTIN_PLUGINS)
    settings.save_disabled(registry, [p.id for p in registry.installed if p.kind != 'framework'])
    prelude = """
import sys
from pathlib import Path
from feishu_stack.plugins import settings
settings.settings_path = lambda: Path(sys.argv[1])
from feishu_stack.api.app import app
from feishu_stack.api.security import require_control_token
from fastapi.testclient import TestClient
client = TestClient(app)
"""
    first = """
assert client.get('/api/health').status_code == 200
assert [p['id'] for p in client.get('/api/plugins').json()['plugins']] == ['acc.framework']
assert client.get('/api/status').status_code == 404
assert len(client.get('/api/plugins/settings').json()['plugins']) >= 11
app.dependency_overrides[require_control_token] = lambda: None
assert client.put('/api/plugins/settings', json={'disabled': []}).json()['restart_required']
assert len(client.get('/api/plugins').json()['plugins']) == 1
"""
    second = """
assert len(client.get('/api/plugins').json()['plugins']) >= 11
assert not client.get('/api/plugins/settings').json()['restart_required']
"""
    env = {k: v for k, v in os.environ.items() if k != 'ACC_DISABLED_PLUGINS'}
    for script in (first, second):
        subprocess.run([sys.executable, '-c', prelude + script, str(path)], env=env, check=True)
