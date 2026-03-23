"""TerraCore 루트 공개 API 테스트."""

from terra_core import (
    AtmosphereState,
    ChainEntry,
    ElementInventory,
    RegulatorStatus,
    SynthesisPhase,
    TelemetryFrame,
    TerraAbortMode,
    TerraAgent,
    TerraAgentConfig,
    TerraChain,
    TerraHealth,
    TerraPhysicsConfig,
    TerraState,
    __version__,
)


def test_root_public_api_exports():
    assert __version__ == "0.1.0"
    assert TerraAgent is not None
    assert TerraAgentConfig is not None
    assert TerraChain is not None
    assert ChainEntry is not None
    assert TerraPhysicsConfig is not None
    assert TerraState is not None
    assert TerraHealth is not None
    assert TelemetryFrame is not None
    assert ElementInventory is not None
    assert AtmosphereState is not None
    assert SynthesisPhase is not None
    assert RegulatorStatus is not None
    assert TerraAbortMode is not None


def test_root_agent_smoke():
    agent = TerraAgent(TerraAgentConfig(dt_s=1.0))
    frame = agent.tick()
    assert isinstance(frame, TelemetryFrame)
    assert frame.t_s > 0.0
