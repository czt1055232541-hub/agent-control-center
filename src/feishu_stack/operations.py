from importlib import import_module as _import_module
import sys as _sys
import types as _types
_target_module = _import_module('feishu_stack.services.operations')
class _CompatModule(_types.ModuleType):
    def __getattribute__(self, name):
        if name in {'_target_module', '_CompatModule', '__class__', '__dict__', '__name__', '__loader__', '__package__', '__spec__', '__file__', '__cached__'}:
            return _types.ModuleType.__getattribute__(self, name)
        return getattr(_target_module, name)
    def __setattr__(self, name, value):
        if name.startswith('__') or name in {'_target_module', '_CompatModule'}:
            _types.ModuleType.__setattr__(self, name, value)
            return
        setattr(_target_module, name, value)
    def __delattr__(self, name):
        delattr(_target_module, name)
_sys.modules[__name__].__class__ = _CompatModule
