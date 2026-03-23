"""
FusionCore 브리지 — TerraCore ↔ FusionCore 인터페이스

FusionCore가 설치되어 있으면 실제 연동, 없으면 독립 운영.

try/except ImportError 패턴으로 선택적 연동.
"""
from __future__ import annotations

try:
    from fusion_core.contracts.schemas import FusionCoreState, PowerBusState  # type: ignore
    FUSION_CORE_AVAILABLE = True
except ImportError:
    FUSION_CORE_AVAILABLE = False


def fusion_power_to_terra(fusion_state_dict: dict) -> dict:
    """FusionCore 출력 → TerraCore 에너지 입력 변환.

    Args:
        fusion_state_dict: FusionCore 상태 딕셔너리
            예: {"power_output_mw": 500.0, "h2_feed_mol_s": 0.1}

    Returns:
        TerraCore 입력 딕셔너리:
            {
                "power_mw": float,         # 공급 전력 [MW]
                "charged_power_mw": float, # 대전 전력 (플라즈마) [MW]
                "h2_feed_mol_s": float,    # H₂ 공급률 [mol/s]
            }
    """
    power = fusion_state_dict.get("power_output_mw", 0.0)
    charged = fusion_state_dict.get("charged_power_mw", power * 0.3)
    h2 = fusion_state_dict.get("h2_feed_mol_s", 0.0)

    return {
        "power_mw": power,
        "charged_power_mw": charged,
        "h2_feed_mol_s": h2,
    }


def terra_elements_to_fusion(terra_state_dict: dict) -> dict:
    """TerraCore 원소 재고 → FusionCore 연료 피드백.

    전기분해로 생성된 H₂를 FusionCore 연료로 되돌릴 수 있다.

    Args:
        terra_state_dict: TerraCore 상태 딕셔너리 (ElementInventory 포함)

    Returns:
        FusionCore 연료 피드백 딕셔너리:
            {
                "available_h2_mol": float,  # 공급 가능 H₂ [mol]
                "available_he3_mol": float, # 공급 가능 He-3 [mol]
            }
    """
    elements = terra_state_dict.get("elements", {})
    h2_mol = elements.get("hydrogen_mol", 0.0) * 0.01  # 1% 피드백 근사
    he_mol = elements.get("helium_mol", 0.0) * 0.001  # 0.1% He-3 근사

    return {
        "available_h2_mol": h2_mol,
        "available_he3_mol": he_mol,
    }


def is_fusion_core_available() -> bool:
    """FusionCore 연동 가능 여부."""
    return FUSION_CORE_AVAILABLE
