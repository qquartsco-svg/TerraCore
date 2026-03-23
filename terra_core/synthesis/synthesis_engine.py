"""
핵합성 엔진 — pp chain, CNO cycle, 삼중 알파 통합 오케스트레이터

온도에 따라 활성 반응을 결정하고, 원소 재고를 갱신한다.

Phase 결정 기준:
  T < 4×10⁶ K         → INACTIVE
  4×10⁶ ≤ T < 1.5×10⁷ K → PP_CHAIN
  1.5×10⁷ ≤ T < 1×10⁸ K → PP_CHAIN + CNO_ACTIVE
  T ≥ 1×10⁸ K         → TRIPLE_ALPHA (+ 이전 반응들)
"""
from __future__ import annotations

from dataclasses import dataclass, field

from terra_core.contracts.schemas import (
    SynthesisPhase,
    SynthesisState,
    TerraPhysicsConfig,
)
from terra_core.synthesis.pp_chain import PPChain, PPChainConfig
from terra_core.synthesis.cno_cycle import CNOCycle, CNOCycleConfig
from terra_core.synthesis.triple_alpha import TripleAlpha, TripleAlphaConfig


@dataclass
class SynthesisConfig:
    """핵합성 엔진 전체 설정."""

    pp_config: PPChainConfig = field(default_factory=PPChainConfig)
    cno_config: CNOCycleConfig = field(default_factory=CNOCycleConfig)
    triple_alpha_config: TripleAlphaConfig = field(default_factory=TripleAlphaConfig)
    # 반응 챔버 체적 [m³]
    chamber_volume_m3: float = 1000.0
    # 초기 수소 질량 분율 (태양 기준)
    initial_h_fraction: float = 0.73
    # 초기 헬륨 질량 분율
    initial_he_fraction: float = 0.25
    # 초기 CNO 질량 분율
    initial_cno_fraction: float = 0.02


class SynthesisEngine:
    """핵합성 통합 엔진.

    온도·밀도·원소 재고를 입력받아 활성 핵반응을 수행하고
    SynthesisState와 갱신된 원소 분율을 반환한다.
    """

    def __init__(self, config: SynthesisConfig, physics: TerraPhysicsConfig):
        self.config = config
        self.physics = physics

        self.pp = PPChain(config.pp_config)
        self.cno = CNOCycle(config.cno_config)
        self.ta = TripleAlpha(config.triple_alpha_config)

        # 가변 상태 (내부 추적)
        self._h_frac: float = config.initial_h_fraction
        self._he_frac: float = config.initial_he_fraction
        self._cno_frac: float = config.initial_cno_fraction

    def _determine_phase(self, temp_k: float) -> SynthesisPhase:
        """온도 기반 반응 단계 결정."""
        if temp_k < 4e6:
            return SynthesisPhase.INACTIVE
        elif temp_k < 1.5e7:
            return SynthesisPhase.PP_CHAIN
        elif temp_k < 1e8:
            # T > 1.7e7이면 CNO 지배
            return SynthesisPhase.CNO_ACTIVE
        else:
            return SynthesisPhase.TRIPLE_ALPHA

    def tick(
        self,
        t_s: float,
        temp_k: float,
        density_kgm3: float,
        dt_s: float,
    ) -> SynthesisState:
        """단일 타임스텝 계산.

        Args:
            t_s: 현재 시각 [s]
            temp_k: 반응로 온도 [K]
            density_kgm3: 반응로 밀도 [kg/m³]
            dt_s: 타임스텝 크기 [s]

        Returns:
            SynthesisState 관측값
        """
        phase = self._determine_phase(temp_k)

        pp_rate, pp_pwr = 0.0, 0.0
        cno_rate, cno_pwr = 0.0, 0.0
        ta_rate, ta_pwr, ta_c12 = 0.0, 0.0, 0.0
        he4_total = 0.0
        c12_total = 0.0

        if phase != SynthesisPhase.INACTIVE:
            pp_rate, pp_pwr = self.pp.tick(temp_k, density_kgm3, self._h_frac, dt_s, self.physics)

        if phase in (SynthesisPhase.CNO_ACTIVE, SynthesisPhase.TRIPLE_ALPHA):
            cno_rate, cno_pwr = self.cno.tick(
                temp_k, density_kgm3, self._h_frac, self._cno_frac, dt_s, self.physics
            )

        if phase == SynthesisPhase.TRIPLE_ALPHA:
            ta_rate, ta_pwr, ta_c12 = self.ta.tick(
                temp_k, density_kgm3, self._he_frac, dt_s, self.physics
            )

        # He-4 생성
        he4_total = self.pp.he4_production_mol_s(pp_rate) + cno_rate + ta_rate
        c12_total = ta_c12

        # 원소 분율 갱신 (근사: 전체 연료 질량 기준 정규화)
        h_consumed = (pp_rate * 4 + cno_rate * 4) * dt_s  # 4H→He per reaction
        he_produced = he4_total * dt_s
        c12_produced = c12_total * dt_s

        total_frac = self._h_frac + self._he_frac + self._cno_frac
        if total_frac > 0:
            # 수소 소모
            delta_h = min(h_consumed / (density_kgm3 * self.config.chamber_volume_m3 + 1.0), self._h_frac * 0.01)
            self._h_frac = max(0.0, self._h_frac - delta_h)
            self._he_frac = min(1.0, self._he_frac + delta_h * 0.98)

        total_power_mw = pp_pwr + cno_pwr + ta_pwr

        return SynthesisState(
            t_s=t_s,
            phase=phase,
            core_temp_k=temp_k,
            core_density_kgm3=density_kgm3,
            pp_rate_mol_s=pp_rate,
            cno_rate_mol_s=cno_rate,
            triple_alpha_rate_mol_s=ta_rate,
            power_output_mw=total_power_mw,
            he4_produced_mol_s=he4_total,
            c12_produced_mol_s=c12_total,
        )

    @property
    def h_fraction(self) -> float:
        """현재 수소 질량 분율."""
        return self._h_frac

    @property
    def he_fraction(self) -> float:
        """현재 헬륨 질량 분율."""
        return self._he_frac

    @property
    def cno_fraction(self) -> float:
        """현재 CNO 질량 분율."""
        return self._cno_frac
