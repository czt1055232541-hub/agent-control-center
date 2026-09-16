from __future__ import annotations

from pathlib import Path


PLUGIN_ROOT = Path(__file__).parents[2] / "integrations" / "dsh-plugin-acc"


def test_output_schema_uses_dsh_value_schema_required_flags() -> None:
    source = (PLUGIN_ROOT / "index.js").read_text(encoding="utf-8")

    assert "required: ['online'" not in source
    assert "online: { type: 'boolean', required: true }" in source
    assert "plugins: { type: 'array', items: { type: 'string' }, required: true }" in source
