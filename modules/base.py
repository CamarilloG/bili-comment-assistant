from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ParamSpec(BaseModel):
    """Parameter specification for an action."""

    type: str  # "string", "int", "float", "bool", "list", "dict"
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[List[str]] = None
    constraints: Optional[Dict[str, Any]] = None


class ActionSpec(BaseModel):
    """Specification for a single module action."""

    name: str
    description: str
    parameters: Dict[str, ParamSpec] = Field(default_factory=dict)
    returns: Dict[str, str] = Field(default_factory=dict)
    side_effects: List[str] = Field(default_factory=list)
    estimated_duration: str = "medium"  # "fast"/<1s, "medium"/1-10s, "slow"/>10s
    risk_level: str = "safe"  # "safe", "moderate", "high"


class ModuleCapability(BaseModel):
    """Describes what a module can do — readable by AI for planning."""

    name: str
    description: str
    actions: List[ActionSpec]
    requires_browser: bool = False
    requires_auth: bool = False
    category: str = "system"  # "browser_automation", "data_processing", "ai_generation", "system"


class ActionResult(BaseModel):
    """Result returned from executing a module action."""

    success: bool
    data: Any = None
    error: Optional[str] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)
    logs: List[str] = Field(default_factory=list)


class ExecutionContext(BaseModel):
    """Runtime context passed to module execution."""

    session_id: str = ""
    task_id: str = ""
    browser_id: Optional[str] = None
    page_id: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True


class IModule(ABC):
    """Base interface that every functional module must implement."""

    @abstractmethod
    def get_capability(self) -> ModuleCapability:
        """Return a machine-readable description of this module's abilities."""
        ...

    @abstractmethod
    async def execute(
        self, action: str, params: Dict[str, Any], context: ExecutionContext
    ) -> ActionResult:
        """Execute the named action with the given parameters."""
        ...

    @abstractmethod
    async def validate_params(
        self, action: str, params: Dict[str, Any]
    ) -> tuple[bool, str]:
        """Validate parameters before execution. Returns (valid, error_message)."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the module is operational."""
        ...

    # ---- helpers available to all modules ----

    def _action_names(self) -> set[str]:
        return {a.name for a in self.get_capability().actions}

    def _require_action(self, action: str) -> None:
        if action not in self._action_names():
            raise ValueError(
                f"Unknown action '{action}' for module '{self.get_capability().name}'"
            )
