"""
Ω (Omega) 건전성 모니터 — TerraCore 종합 건전성 지표

Ω_terra = w_syn·Ω_syn + w_atm·Ω_atm + w_hyd·Ω_hyd + w_bio·Ω_bio + w_reg·Ω_reg

판정 기준:
  Ω > 0.8 → THRIVING
  Ω > 0.6 → STABLE
  Ω > 0.4 → FRAGILE
  Ω ≤ 0.4 → CRITICAL
"""
from __future__ import annotations

from dataclasses import dataclass

from terra_core.contracts.schemas import (
    AtmosphereState,
    BiosphereState,
    HydrosphereState,
    RegulatorState,
    SynthesisPhase,
    SynthesisState,
    TerraHealth,
    TerraState,
)


@dataclass
class OmegaConfig:
    """Ω 모니터 가중치 설정."""

    w_synthesis: float = 0.25
    w_atmosphere: float = 0.30
    w_hydrosphere: float = 0.20
    w_biosphere: float = 0.15
    w_regulator: float = 0.10
    base_crew_count: int = 6
    # 광합성 최대 바이오매스 (Ω_bio 정규화용)
    biomass_max_kg: float = 5000.0


class OmegaMonitor:
    """TerraCore 종합 건전성 모니터.

    각 서브시스템의 상태를 [0, 1] 스칼라로 정규화하고
    가중 합산하여 Ω_terra를 계산한다.
    """

    def __init__(self, config: OmegaConfig):
        self.config = config

    def _omega_synthesis(self, synth: SynthesisState) -> float:
        """핵합성 건전성 [0, 1].

        INACTIVE → 0.1
        PP_CHAIN → 0.6
        CNO_ACTIVE → 0.8
        TRIPLE_ALPHA → 1.0
        출력 [MW] 기준 정규화
        """
        phase_score = {
            SynthesisPhase.INACTIVE: 0.1,
            SynthesisPhase.PP_CHAIN: 0.6,
            SynthesisPhase.CNO_ACTIVE: 0.8,
            SynthesisPhase.TRIPLE_ALPHA: 1.0,
            SynthesisPhase.CARBON_BURNING: 0.9,
            SynthesisPhase.EQUILIBRIUM: 0.95,
        }.get(synth.phase, 0.1)

        # 출력이 있으면 보너스
        power_score = min(1.0, synth.power_output_mw / 100.0) if synth.power_output_mw > 0 else 0.0

        return 0.7 * phase_score + 0.3 * power_score

    def _omega_atmosphere(self, atm: AtmosphereState) -> float:
        """대기 건전성 [0, 1].

        호흡 가능 여부, CO₂ 농도, O₂ 분율 기반.
        """
        if not atm.breathable:
            base = 0.0
        else:
            base = 0.5

        # O₂ 분율 점수 (목표: 21%)
        o2_score = 1.0 - abs(atm.o2_fraction - 0.2095) / 0.2095
        o2_score = max(0.0, o2_score)

        # CO₂ 역수 점수 (낮을수록 좋음)
        if atm.co2_ppm <= 0:
            co2_score = 1.0
        else:
            co2_score = max(0.0, 1.0 - atm.co2_ppm / 5000.0)

        return base * 0.5 + o2_score * 0.25 + co2_score * 0.25

    def _omega_hydrosphere(self, hydro: HydrosphereState) -> float:
        """수권 건전성 [0, 1]."""
        return max(0.0, min(1.0, hydro.water_margin))

    def _omega_biosphere(self, bio: BiosphereState) -> float:
        """생태계 건전성 [0, 1]."""
        biomass_score = min(1.0, bio.plant_biomass_kg / self.config.biomass_max_kg)
        food_score = min(1.0, bio.food_production_kg_day / (self.config.base_crew_count * 2.0))
        return 0.6 * biomass_score + 0.4 * food_score

    def _omega_regulator(self, reg: RegulatorState) -> float:
        """조절기 건전성 [0, 1]."""
        # 방사선 여유: max_dose = 1e-4 Sv/hr 기준
        max_dose = 1e-4
        radiation_margin = max(0.0, 1.0 - reg.radiation_dose_sv_hr / max_dose)

        return 0.5 * reg.thermal_margin + 0.3 * reg.pressure_margin + 0.2 * radiation_margin

    def _verdict(self, omega: float) -> str:
        """Ω → 판정 문자열."""
        if omega > 0.8:
            return "THRIVING"
        elif omega > 0.6:
            return "STABLE"
        elif omega > 0.4:
            return "FRAGILE"
        else:
            return "CRITICAL"

    def observe(self, state: TerraState) -> TerraHealth:
        """TerraState로부터 TerraHealth 계산.

        Args:
            state: 현재 TerraState

        Returns:
            TerraHealth — 종합 건전성 지표
        """
        cfg = self.config

        o_syn = self._omega_synthesis(state.synthesis)
        o_atm = self._omega_atmosphere(state.atmosphere)
        o_hyd = self._omega_hydrosphere(state.hydrosphere)
        o_bio = self._omega_biosphere(state.biosphere)
        o_reg = self._omega_regulator(state.regulator)

        o_terra = (
            cfg.w_synthesis * o_syn
            + cfg.w_atmosphere * o_atm
            + cfg.w_hydrosphere * o_hyd
            + cfg.w_biosphere * o_bio
            + cfg.w_regulator * o_reg
        )

        alerts = []
        if state.atmosphere.co2_ppm > 5000.0:
            alerts.append("CO2_TOXIC")
        if state.atmosphere.o2_fraction < 0.16:
            alerts.append("O2_LOW")
        if state.hydrosphere.water_margin < 0.1:
            alerts.append("WATER_CRITICAL")
        if state.regulator.radiation_dose_sv_hr > 1e-4:
            alerts.append("RADIATION_HIGH")
        if state.regulator.temperature_k > 320.0:
            alerts.append("THERMAL_HIGH")
        if state.biosphere.plant_biomass_kg < 1.0:
            alerts.append("BIOSPHERE_DEAD")

        return TerraHealth(
            omega_terra=o_terra,
            omega_synthesis=o_syn,
            omega_atmosphere=o_atm,
            omega_hydrosphere=o_hyd,
            omega_biosphere=o_bio,
            omega_regulator=o_reg,
            verdict=self._verdict(o_terra),
            alerts=tuple(alerts),
            abort_required=o_terra < 0.25,
        )
