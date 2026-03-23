"""
대기 가스 순환 모델

지구 대기 구성 (참조):
  N₂:  78.09%
  O₂:  20.95%
  Ar:   0.93%
  CO₂:  0.04% (420 ppm)
  H₂O:  가변

우주선 목표 대기:
  총압:  101325 Pa (1 atm)
  O₂:   21% (21276 Pa)
  N₂:   79% 근사
  CO₂:  < 5000 ppm (독성 한계: 5%)

광합성 반응:
  6CO₂ + 6H₂O + 에너지 → C₆H₁₂O₆ + 6O₂
  (ΔG = -2870 kJ/mol)

호흡 반응:
  C₆H₁₂O₆ + 6O₂ → 6CO₂ + 6H₂O + 2870 kJ/mol

CO₂ 허용 범위:
  < 1000 ppm: 정상
  1000-5000 ppm: 주의
  > 5000 ppm: 독성 (승무원 건강 위험)
  > 40000 ppm (4%): 생명 위험

LaTeX:
  P_{total} = P_{O_2} + P_{N_2} + P_{CO_2} + P_{H_2O}
  x_{CO_2} = n_{CO_2} / n_{total} \\times 10^6\\,\\text{ppm}
"""
from __future__ import annotations

from dataclasses import dataclass

from terra_core.contracts.schemas import (
    AtmosphereState,
    AtmosphereStatus,
    BiosphereState,
    HydrosphereState,
    TerraPhysicsConfig,
)


@dataclass
class GasCycleConfig:
    """대기 가스 순환 설정 파라미터."""

    # 목표 총 대기압 [Pa]
    target_pressure_pa: float = 101325.0
    # 목표 O₂ 몰분율
    target_o2_fraction: float = 0.2095
    # 목표 CO₂ 농도 [ppm]
    target_co2_ppm: float = 800.0
    # CO₂ 독성 한계 [ppm]
    max_co2_ppm: float = 5000.0
    # 생존 최소 O₂ 분율
    min_o2_fraction: float = 0.16
    # 화재 위험 최대 O₂ 분율
    max_o2_fraction: float = 0.30
    # 승무원 1인당 CO₂ 배출률 [mol/s]
    crew_co2_output_mol_s_per_person: float = 2.3e-4
    # 승무원 1인당 O₂ 소비률 [mol/s]
    crew_o2_consumption_mol_s_per_person: float = 2.0e-4
    # 승무원 수
    crew_count: int = 6
    # 거주 공간 체적 [m³]
    volume_m3: float = 1000.0


class GasCycle:
    """대기 가스 순환 계산기.

    승무원 호흡, 광합성, 전기분해로 인한 가스 분압 변화를 추적한다.
    """

    def __init__(self, config: GasCycleConfig, physics: TerraPhysicsConfig):
        self.config = config
        self.physics = physics

    def crew_co2_output_mol_s(self) -> float:
        """승무원 전체 CO₂ 배출률 [mol/s]."""
        return self.config.crew_co2_output_mol_s_per_person * self.config.crew_count

    def crew_o2_consumption_mol_s(self) -> float:
        """승무원 전체 O₂ 소비률 [mol/s]."""
        return self.config.crew_o2_consumption_mol_s_per_person * self.config.crew_count

    def _classify_status(self, total_pa: float, o2_frac: float, co2_ppm: float) -> AtmosphereStatus:
        """대기 상태 분류."""
        if total_pa < 1000.0:
            return AtmosphereStatus.VACUUM
        if total_pa < 50000.0:
            return AtmosphereStatus.THIN
        if co2_ppm > self.config.max_co2_ppm:
            return AtmosphereStatus.TOXIC
        if o2_frac > self.config.max_o2_fraction:
            return AtmosphereStatus.RICH
        return AtmosphereStatus.NOMINAL

    def is_breathable(self, state: AtmosphereState) -> bool:
        """호흡 가능 여부 판정.

        조건: O₂ 16~30%, CO₂ < 5000 ppm
        """
        return (
            self.config.min_o2_fraction <= state.o2_fraction <= self.config.max_o2_fraction
            and state.co2_ppm < self.config.max_co2_ppm
        )

    def tick(
        self,
        state: AtmosphereState,
        bio: BiosphereState,
        hydro: HydrosphereState,
        dt_s: float,
        physics: TerraPhysicsConfig,
    ) -> AtmosphereState:
        """단일 타임스텝 대기 갱신.

        수행 내용:
        1. 승무원 CO₂ 배출 + O₂ 소비
        2. 광합성 CO₂ 흡수 + O₂ 방출
        3. 전기분해 O₂ 추가
        4. 분압 재계산
        5. AtmosphereStatus 판정

        Args:
            state: 현재 대기 상태
            bio: 생태계 상태 (광합성 기여)
            hydro: 수권 상태 (전기분해 O₂)
            dt_s: 타임스텝 [s]
            physics: 물리 상수

        Returns:
            갱신된 AtmosphereState
        """
        cfg = self.config

        # 이상기체 법칙으로 현재 각 가스의 mol 수 역산
        # PV = nRT → n = PV/(RT)
        T = state.temperature_k
        V = cfg.volume_m3
        R = physics.r_gas

        def pa_to_mol(partial_pa: float) -> float:
            if T <= 0.0:
                return 0.0
            return (partial_pa * V) / (R * T)

        n_o2 = pa_to_mol(state.o2_partial_pa)
        n_n2 = pa_to_mol(state.n2_partial_pa)
        n_co2 = pa_to_mol(state.co2_partial_pa)
        n_h2o = pa_to_mol(state.h2o_vapor_pa)

        # 승무원 호흡
        n_co2 += self.crew_co2_output_mol_s() * dt_s
        n_o2 = max(0.0, n_o2 - self.crew_o2_consumption_mol_s() * dt_s)

        # 광합성: CO₂ 흡수 + O₂ 방출
        n_co2 = max(0.0, n_co2 - bio.co2_uptake_mol_s * dt_s)
        n_o2 += bio.o2_release_mol_s * dt_s

        # 전기분해 O₂ 추가
        n_o2 += hydro.o2_from_water_mol_s * dt_s

        # 분압 재계산
        def mol_to_pa(n_mol: float) -> float:
            return (n_mol * R * T) / V

        new_o2_pa = mol_to_pa(n_o2)
        new_n2_pa = mol_to_pa(n_n2)
        new_co2_pa = mol_to_pa(n_co2)
        new_h2o_pa = mol_to_pa(n_h2o)
        new_total_pa = new_o2_pa + new_n2_pa + new_co2_pa + new_h2o_pa

        # 몰분율 계산
        total_mol = n_o2 + n_n2 + n_co2 + n_h2o
        o2_frac = n_o2 / total_mol if total_mol > 0 else 0.0
        co2_ppm = (n_co2 / total_mol * 1e6) if total_mol > 0 else 0.0

        # 대기 상태 분류
        status = self._classify_status(new_total_pa, o2_frac, co2_ppm)

        new_state = AtmosphereState(
            t_s=state.t_s + dt_s,
            status=status,
            total_pressure_pa=new_total_pa,
            o2_partial_pa=new_o2_pa,
            n2_partial_pa=new_n2_pa,
            co2_partial_pa=new_co2_pa,
            h2o_vapor_pa=new_h2o_pa,
            temperature_k=T,
            o2_fraction=o2_frac,
            co2_ppm=co2_ppm,
            breathable=self.is_breathable(
                AtmosphereState(
                    t_s=state.t_s + dt_s,
                    status=status,
                    total_pressure_pa=new_total_pa,
                    o2_partial_pa=new_o2_pa,
                    n2_partial_pa=new_n2_pa,
                    co2_partial_pa=new_co2_pa,
                    h2o_vapor_pa=new_h2o_pa,
                    temperature_k=T,
                    o2_fraction=o2_frac,
                    co2_ppm=co2_ppm,
                    breathable=False,
                )
            ),
        )
        return new_state
