"""
중단 시스템 (Abort System) — TerraCore 비상 중단 판정

우선순위:
  1. 대기 독성 (CO₂ > 4% 또는 O₂ < 12%) → ATMOSPHERE_CRITICAL
  2. 방사선 한계 초과 → RADIATION_ALERT
  3. 열 폭주 → THERMAL_RUNAWAY
  4. 수분 고갈 → WATER_CRITICAL
  5. 생태계 붕괴 (biomass → 0) → BIOSPHERE_COLLAPSE
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from terra_core.contracts.schemas import TerraHealth, TerraState


class TerraAbortMode(Enum):
    """TerraCore 중단 모드."""

    NONE = auto()
    ATMOSPHERE_CRITICAL = auto()
    WATER_CRITICAL = auto()
    THERMAL_RUNAWAY = auto()
    RADIATION_ALERT = auto()
    BIOSPHERE_COLLAPSE = auto()


@dataclass
class AbortConfig:
    """중단 시스템 설정 파라미터."""

    # Ω 중단 임계값
    omega_abort_threshold: float = 0.25
    # CO₂ 생명 위험 [ppm] = 4%
    max_co2_ppm: float = 40000.0
    # 생존 최소 O₂ 분율
    min_o2_fraction: float = 0.12
    # 최소 수분 재고 [mol]
    min_water_mol: float = 100.0
    # 최대 허용 온도 [K]
    max_temp_k: float = 330.0
    # 최대 허용 방사선 선량률 [Sv/hr]
    max_dose_sv_hr: float = 0.01


class AbortSystem:
    """TerraCore 비상 중단 판정기.

    물리 한계를 초과하면 우선순위에 따라 중단 모드를 반환한다.
    """

    def __init__(self, config: AbortConfig):
        self.config = config

    def evaluate(
        self,
        state: TerraState,
        health: TerraHealth,
    ) -> TerraAbortMode:
        """중단 모드 판정.

        우선순위 순서로 조건을 검사하고, 첫 번째 충족 조건을 반환한다.

        Args:
            state: 현재 TerraState
            health: 현재 TerraHealth

        Returns:
            TerraAbortMode (NONE이면 정상)
        """
        cfg = self.config

        # 1. 대기 독성 (최고 우선순위)
        atm = state.atmosphere
        if atm.co2_ppm > cfg.max_co2_ppm or atm.o2_fraction < cfg.min_o2_fraction:
            return TerraAbortMode.ATMOSPHERE_CRITICAL

        # 2. 방사선 한계
        if state.regulator.radiation_dose_sv_hr > cfg.max_dose_sv_hr:
            return TerraAbortMode.RADIATION_ALERT

        # 3. 열 폭주
        if state.regulator.temperature_k > cfg.max_temp_k:
            return TerraAbortMode.THERMAL_RUNAWAY

        # 4. 수분 고갈
        if state.hydrosphere.water_total_mol < cfg.min_water_mol:
            return TerraAbortMode.WATER_CRITICAL

        # 5. 생태계 붕괴
        if state.biosphere.plant_biomass_kg <= 0.0:
            return TerraAbortMode.BIOSPHERE_COLLAPSE

        return TerraAbortMode.NONE

    def is_abort_required(
        self,
        state: TerraState,
        health: TerraHealth,
    ) -> bool:
        """중단 필요 여부."""
        mode = self.evaluate(state, health)
        omega_abort = health.omega_terra < self.config.omega_abort_threshold
        return mode != TerraAbortMode.NONE or omega_abort
