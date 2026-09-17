"""Configuration plugin writes must authenticate before reaching services."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from feishu_stack.api import security
from feishu_stack.modules.config_center import plugin as config
from feishu_stack.modules.routing_rules import plugin as routing


@pytest.mark.parametrize('module,method,path,payload,service_name', [
    (config, 'POST', '/api/config-center/set', {'key': 'test', 'value': 'value'}, 'set_config'),
    (config, 'DELETE', '/api/config-center/delete/test', None, 'delete_config'),
    (config, 'POST', '/api/config-center/import', {'configs': {}}, 'import_configs'),
    (config, 'POST', '/api/config-center/export', None, 'export_configs'),
    (routing, 'POST', '/api/routing-rules/set', {'name': 'test'}, 'set_rule'),
    (routing, 'DELETE', '/api/routing-rules/delete/test', None, 'delete_rule'),
    (routing, 'POST', '/api/routing-rules/batch', {'rules': []}, 'batch_import_rules'),
])
def test_mutation_authentication(monkeypatch, module, method, path, payload, service_name):
    monkeypatch.setattr(security, 'get_or_create_token', lambda: 'test-only-token')
    calls = []
    def fake_service(*args, **kwargs):
        calls.append((args, kwargs))
        return True if method == 'DELETE' else {'ok': True}
    monkeypatch.setattr(module.service, service_name, fake_service)
    app = FastAPI()
    app.include_router(module.create_router())
    with TestClient(app) as client:
        assert client.request(method, path, json=payload).status_code == 401
        assert client.request(method, path, json=payload, headers={'X-Control-Token': 'wrong'}).status_code == 403
        assert calls == []
        assert client.request(method, path, json=payload, headers={'X-Control-Token': 'test-only-token'}).status_code == 200
        assert len(calls) == 1
