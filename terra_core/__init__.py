"""TerraCore — 자가순환 우주선 생명유지 엔진."""

from terra_core.audit.terra_chain import ChainEntry, TerraChain
from terra_core.contracts.schemas import (
    AtmosphereState,
    AtmosphereStatus,
    BiosphereState,
    BiosphereStatus,
    ElementInventory,
    HydrosphereState,
    RegulatorState,
    RegulatorStatus,
    SynthesisPhase,
    SynthesisState,
    TelemetryFrame,
    TerraHealth,
    TerraPhysicsConfig,
    TerraState,
)
from terra_core.safety.abort_system import TerraAbortMode
from terra_core.terra_agent import TerraAgent, TerraAgentConfig

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "TerraAgent",
    "TerraAgentConfig",
    "TerraChain",
    "ChainEntry",
    "TerraPhysicsConfig",
    "TerraState",
    "TerraHealth",
    "TelemetryFrame",
    "ElementInventory",
    "SynthesisState",
    "AtmosphereState",
    "HydrosphereState",
    "BiosphereState",
    "RegulatorState",
    "SynthesisPhase",
    "AtmosphereStatus",
    "BiosphereStatus",
    "RegulatorStatus",
    "TerraAbortMode",
]
