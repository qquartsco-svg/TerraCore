"""
질소 순환 모델

지구 질소 순환:
  N₂ (대기) → NH₃ (고정) → NO₃⁻ (질산화) → 식물 흡수 → 분해 → N₂

생물학적 질소 고정:
  N₂ + 8H⁺ + 8e⁻ + 16ATP → 2NH₃ + H₂ + 16ADP
  Nitrogenase 효소 (Fe-Mo 보조인자)

우주선에서의 의미:
  - 질소는 대기 완충제 (O₂ 희석, 화재 억제)
  - NH₃는 식물 비료 (질소원)
  - 닫힌 루프: 대기 N₂ → 미생물 고정 → 식물 → 분해 → N₂

하버-보슈 공정 (인공 질소 고정):
  N₂ + 3H₂ → 2NH₃  (400-500°C, 150-300 atm, Fe 촉매)
  ΔH = -92 kJ/mol

LaTeX:
  N_2 + 3H_2 \\xrightarrow{\\text{Fe, }400^\\circ C} 2NH_3,\\quad
  \\Delta H = -92\\,\\text{kJ/mol}
"""
from __future__ import annotations

from dataclasses import dataclass

from terra_core.contracts.schemas import AtmosphereState, BiosphereState


@dataclass
class NitrogenCycleConfig:
    """질소 순환 설정 파라미터."""

    # 미생물 N₂ 고정률 [mol/s]
    bio_fixation_rate_mol_s: float = 1e-5
    # 하버-보슈 효율
    haber_bosch_efficiency: float = 0.85
    # 목표 N₂ 분율
    n2_target_fraction: float = 0.79
    # NH₃ → 식물 흡수 효율
    nh3_to_plant_efficiency: float = 0.7


class NitrogenCycle:
    """질소 순환 계산기.

    생물학적 질소 고정과 하버-보슈 공정을 통해
    N₂ → NH₃ → 식물 비료 순환을 모사한다.
    """

    def __init__(self, config: NitrogenCycleConfig):
        self.config = config

    def bio_fixation_rate(self, biomass_kg: float) -> float:
        """생물학적 N₂ 고정률 [mol/s].

        바이오매스에 비례: 식물뿌리 공생 미생물 (뿌리혹박테리아).
        """
        if biomass_kg <= 0.0:
            return 0.0
        # 바이오매스 100kg 기준 정규화
        return self.config.bio_fixation_rate_mol_s * (biomass_kg / 100.0)

    def haber_bosch_rate(
        self,
        n2_mol_available: float,
        h2_mol_available: float,
        power_mw: float,
    ) -> float:
        """하버-보슈 NH₃ 생산률 [mol/s].

        N₂ + 3H₂ → 2NH₃
        전력 기반 반응률 (0.01 mol/s/MW 근사).
        """
        if n2_mol_available <= 0.0 or h2_mol_available < 3.0 or power_mw <= 0.0:
            return 0.0
        rate_per_mw = 0.01  # [mol/s/MW]
        return power_mw * rate_per_mw * self.config.haber_bosch_efficiency

    def nh3_to_plant_absorption(self, nh3_mol_s: float) -> float:
        """NH₃ → 식물 흡수 가용 질소 [mol/s]."""
        return nh3_mol_s * self.config.nh3_to_plant_efficiency

    def tick(
        self,
        atmosphere: AtmosphereState,
        bio: BiosphereState,
        dt_s: float,
    ) -> float:
        """단일 타임스텝 질소 고정률 계산.

        Args:
            atmosphere: 현재 대기 상태
            bio: 현재 생태계 상태
            dt_s: 타임스텝 [s]

        Returns:
            N₂ 고정률 [mol/s]
        """
        bio_fix = self.bio_fixation_rate(bio.plant_biomass_kg)
        return bio_fix
