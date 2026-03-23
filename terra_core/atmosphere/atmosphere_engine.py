"""
대기 엔진 — GasCycle 래퍼 및 초기 상태 생성.
"""
from __future__ import annotations

from terra_core.contracts.schemas import (
    AtmosphereState,
    AtmosphereStatus,
    TerraPhysicsConfig,
)
from terra_core.atmosphere.gas_cycle import GasCycle, GasCycleConfig


def initial_atmosphere_state(
    config: GasCycleConfig,
    physics: TerraPhysicsConfig,
    t_s: float = 0.0,
) -> AtmosphereState:
    """지구 표준 대기 조건으로 초기 AtmosphereState 생성."""
    T = 293.0  # [K] 실내 표준 온도
    V = config.volume_m3
    R = physics.r_gas

    # 목표 조성 기준 분압 계산
    p_total = config.target_pressure_pa
    o2_frac = config.target_o2_fraction
    n2_frac = 1.0 - o2_frac - 0.01  # CO₂, H₂O 여유
    co2_frac = config.target_co2_ppm / 1e6
    h2o_frac = 0.01  # 1% 수증기

    o2_pa = p_total * o2_frac
    n2_pa = p_total * n2_frac
    co2_pa = p_total * co2_frac
    h2o_pa = p_total * h2o_frac

    return AtmosphereState(
        t_s=t_s,
        status=AtmosphereStatus.NOMINAL,
        total_pressure_pa=p_total,
        o2_partial_pa=o2_pa,
        n2_partial_pa=n2_pa,
        co2_partial_pa=co2_pa,
        h2o_vapor_pa=h2o_pa,
        temperature_k=T,
        o2_fraction=o2_frac,
        co2_ppm=config.target_co2_ppm,
        breathable=True,
    )


__all__ = ["GasCycle", "GasCycleConfig", "initial_atmosphere_state"]
