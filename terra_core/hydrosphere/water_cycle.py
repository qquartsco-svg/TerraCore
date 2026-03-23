"""
수순환 모델

전기분해 (Electrolysis):
  2H₂O → 2H₂ + O₂
  ΔH = +285.8 kJ/mol (H₂O 기준)
  효율 η ≈ 0.70~0.85

역반응 (연료전지):
  2H₂ + O₂ → 2H₂O + 전기
  효율 η ≈ 0.60~0.80

물의 역할:
  1. 전기분해 → O₂ (대기 산소 공급)
  2. 전기분해 → H₂ (핵융합 연료 피드백 가능)
  3. 식물 광합성 기질
  4. 승무원 음용·위생
  5. 열 전달 매체

지구 참조:
  지구 총 수분: 1.386×10²¹ kg
  담수 분율: 2.5%
  대기 중 수분: 1.27×10¹⁶ kg

LaTeX:
  P_{elec} = r_{H_2O} \\cdot \\Delta H / \\eta
  r_{O_2} = r_{H_2O} / 2   (2H_2O \\to 2H_2 + O_2)
"""
from __future__ import annotations

from dataclasses import dataclass

from terra_core.contracts.schemas import HydrosphereState


@dataclass
class WaterCycleConfig:
    """수순환 설정 파라미터."""

    # 전기분해 효율 [0, 1]
    electrolysis_efficiency: float = 0.75
    # 연료전지 효율 [0, 1]
    fuel_cell_efficiency: float = 0.65
    # H₂O mol당 전기분해 전력 [MW/(mol/s)] = 285.8 kJ/mol → MW
    power_per_mol_h2o_mw: float = 2.86e-7
    # 최소 수분 재고 [mol]
    min_water_mol: float = 1000.0
    # 승무원 1인당 소비률 [mol/s]
    crew_consumption_mol_s: float = 4.6e-5
    # 승무원 수
    crew_count: int = 6
    # 목표 전기분해율 [mol/s]
    target_electrolysis_rate_mol_s: float = 0.01


class WaterCycle:
    """수순환 계산기.

    가용 전력으로 전기분해를 수행하고, 승무원 소비를 차감하며,
    수분 재고를 갱신한다.
    """

    def __init__(self, config: WaterCycleConfig):
        self.config = config

    def electrolysis_power_mw(self, rate_mol_s: float) -> float:
        """전기분해 소비 전력 [MW].

        P = rate [mol/s] × ΔH [kJ/mol] / η / efficiency
        """
        if rate_mol_s <= 0.0:
            return 0.0
        # 285.8 kJ/mol = 2.858e5 J/mol = 2.858e-1 kJ
        energy_per_mol_j = 285800.0  # [J/mol]
        power_w = rate_mol_s * energy_per_mol_j / self.config.electrolysis_efficiency
        return power_w / 1e6  # W → MW

    def o2_from_electrolysis(self, rate_mol_s: float) -> float:
        """전기분해 O₂ 생성률 [mol/s].

        2H₂O → 2H₂ + O₂  →  O₂ = H₂O / 2
        """
        return rate_mol_s / 2.0

    def h2_from_electrolysis(self, rate_mol_s: float) -> float:
        """전기분해 H₂ 생성률 [mol/s].

        2H₂O → 2H₂ + O₂  →  H₂ = H₂O (1:1)
        """
        return rate_mol_s

    def _crew_consumption_mol_s(self) -> float:
        """승무원 전체 수분 소비률 [mol/s]."""
        return self.config.crew_consumption_mol_s * self.config.crew_count

    def tick(
        self,
        state: HydrosphereState,
        available_power_mw: float,
        dt_s: float,
    ) -> HydrosphereState:
        """단일 타임스텝 수권 갱신.

        가용 전력으로 전기분해를 수행하고, 승무원 소비를 차감한다.

        Args:
            state: 현재 수권 상태
            available_power_mw: 가용 전력 [MW]
            dt_s: 타임스텝 [s]

        Returns:
            갱신된 HydrosphereState
        """
        cfg = self.config

        # 전기분해율 결정 (전력 제한)
        target_rate = cfg.target_electrolysis_rate_mol_s
        # 필요 전력 계산
        needed_power = self.electrolysis_power_mw(target_rate)

        if available_power_mw >= needed_power and state.water_total_mol > cfg.min_water_mol:
            elec_rate = target_rate
        elif available_power_mw > 0.0 and state.water_total_mol > cfg.min_water_mol:
            # 가용 전력 비례로 전기분해율 조정
            if needed_power > 0:
                elec_rate = target_rate * min(available_power_mw / needed_power, 1.0)
            else:
                elec_rate = 0.0
        else:
            elec_rate = 0.0

        o2_gen = self.o2_from_electrolysis(elec_rate)
        h2_gen = self.h2_from_electrolysis(elec_rate)
        power_used = self.electrolysis_power_mw(elec_rate)

        # 수분 재고 갱신
        crew_consump = self._crew_consumption_mol_s()
        water_consumed = (elec_rate + crew_consump) * dt_s
        new_water = max(0.0, state.water_total_mol - water_consumed)

        # 수분 여유
        water_margin = new_water / max(state.water_total_mol, 1.0)

        # 액체 분율 (단순 모델: 수분 충분하면 0.9)
        liquid_frac = 0.9 if new_water > cfg.min_water_mol else 0.5

        return HydrosphereState(
            t_s=state.t_s + dt_s,
            water_total_mol=new_water,
            liquid_fraction=liquid_frac,
            electrolysis_rate_mol_s=elec_rate,
            h2_produced_mol_s=h2_gen,
            o2_from_water_mol_s=o2_gen,
            power_consumed_mw=power_used,
            water_margin=water_margin,
        )
