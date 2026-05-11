from __future__ import annotations

import importlib.util
import inspect
import os
import sys
from types import ModuleType
from typing import Dict, List, Type

from effect_engine import CreativeFilter


class PluginLoader:
    def __init__(self, plugin_dir: str) -> None:
        self.plugin_dir = plugin_dir
        self.modules: Dict[str, ModuleType] = {}
        self.filter_classes: Dict[str, Type[CreativeFilter]] = {}
        os.makedirs(self.plugin_dir, exist_ok=True)

    def scan(self) -> List[str]:
        return sorted(
            [
                os.path.join(self.plugin_dir, f)
                for f in os.listdir(self.plugin_dir)
                if f.endswith(".py") and not f.startswith("_")
            ]
        )

    def load_plugins(self) -> Dict[str, Type[CreativeFilter]]:
        self.filter_classes.clear()
        for filepath in self.scan():
            module_name = "plugin_{}".format(os.path.splitext(os.path.basename(filepath))[0])
            spec = importlib.util.spec_from_file_location(module_name, filepath)
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            self.modules[module_name] = module

            for _, obj in inspect.getmembers(module, inspect.isclass):
                if obj is CreativeFilter:
                    continue
                if issubclass(obj, CreativeFilter):
                    self.filter_classes[obj.__name__] = obj

        return dict(self.filter_classes)
