"""
CookiieBrain 브리지 — TerraCore ↔ CookiieBrain 인터페이스

CookiieBrain이 설치되어 있으면 실제 연동, 없으면 독립 운영.

try/except ImportError 패턴으로 선택적 연동.
"""
from __future__ import annotations

try:
    from cookiie_brain.core import BrainCore  # type: ignore
    BRAIN_CORE_AVAILABLE = True
except ImportError:
    try:
        from brain_core.core import BrainCore  # type: ignore
        BRAIN_CORE_AVAILABLE = True
    except ImportError:
        BRAIN_CORE_AVAILABLE = False


def terra_state_to_brain_context(terra_state_dict: dict) -> dict:
    """TerraCore 상태 → BrainCore 컨텍스트 변환.

    Args:
        terra_state_dict: TerraCore 상태 요약 딕셔너리

    Returns:
        BrainCore 컨텍스트 딕셔너리
    """
    return {
        "source": "TerraCore",
        "t_s": terra_state_dict.get("t_s", 0.0),
        "omega_terra": terra_state_dict.get("omega_terra", 0.0),
        "verdict": terra_state_dict.get("verdict", "UNKNOWN"),
        "alerts": terra_state_dict.get("alerts", []),
        "abort_required": terra_state_dict.get("abort_required", False),
        "atmosphere": {
            "breathable": terra_state_dict.get("breathable", False),
            "co2_ppm": terra_state_dict.get("co2_ppm", 0.0),
            "o2_fraction": terra_state_dict.get("o2_fraction", 0.0),
        },
        "biosphere": {
            "biomass_kg": terra_state_dict.get("biomass_kg", 0.0),
            "status": terra_state_dict.get("biosphere_status", "UNKNOWN"),
        },
    }


def brain_command_to_terra_action(brain_command: dict) -> dict:
    """BrainCore 명령 → TerraCore 액션 변환.

    Args:
        brain_command: BrainCore 명령 딕셔너리

    Returns:
        TerraCore 액션 딕셔너리
    """
    action_type = brain_command.get("action", "NOOP")
    params = brain_command.get("params", {})

    return {
        "action": action_type,
        "target_temp_k": params.get("target_temp_k", 293.0),
        "target_synthesis_power_mw": params.get("target_power_mw", 0.0),
        "electrolysis_rate_override": params.get("electrolysis_rate", None),
    }


def is_brain_core_available() -> bool:
    """BrainCore 연동 가능 여부."""
    return BRAIN_CORE_AVAILABLE
