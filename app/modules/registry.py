from __future__ import annotations

from typing import Dict, List, Optional

from modules.base import IModule, ModuleCapability


class ModuleRegistry:
    """Central registry that holds all functional modules.

    Modules register themselves (or are registered at startup).
    The AI planner reads capabilities from this registry to understand
    what operations are available.
    """

    def __init__(self) -> None:
        self._modules: Dict[str, IModule] = {}

    def register(self, module_id: str, module: IModule) -> None:
        if module_id in self._modules:
            raise ValueError(f"Module '{module_id}' is already registered")
        self._modules[module_id] = module

    def unregister(self, module_id: str) -> None:
        self._modules.pop(module_id, None)

    def get(self, module_id: str) -> Optional[IModule]:
        return self._modules.get(module_id)

    def get_or_raise(self, module_id: str) -> IModule:
        mod = self._modules.get(module_id)
        if mod is None:
            raise KeyError(f"Module '{module_id}' not found in registry")
        return mod

    def list_ids(self) -> List[str]:
        return list(self._modules.keys())

    def get_all_capabilities(self) -> List[ModuleCapability]:
        return [m.get_capability() for m in self._modules.values()]

    def get_capability(self, module_id: str) -> ModuleCapability:
        return self.get_or_raise(module_id).get_capability()

    def __contains__(self, module_id: str) -> bool:
        return module_id in self._modules

    def __len__(self) -> int:
        return len(self._modules)
