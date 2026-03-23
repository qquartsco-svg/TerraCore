"""
항상성 제어 모델 (Homeostasis)

지구 항상성 참조:
  온도: 평균 15°C (288K), 변동 ±50°C (표면)
  압력: 101325 Pa (해수면)
  pH: 7.0~8.5 (해수)
  자기장: 25~65 μT

우주선 목표:
  온도: 291~295 K (18~22°C)
  압력: 101325 ± 5000 Pa
  pH: 6.5~7.5 (물·토양)
  방사선: < 1 mSv/day (지구 표면 기준)

제어 원리:
  PID 유사 피드백:
    error = setpoint - current
    correction = Kp · error + Ki · ∫error·dt

  열 제어:
    Q_out = ε · σ · A · T⁴  (복사 방열)
    T_new = T + (Q_in - Q_out) / C_thermal · dt

LaTeX:
  Q_{rad} = \\varepsilon \\sigma A T^4
  \\Delta T = \\frac{(Q_{in} - Q_{rad})}{C_{thermal}} \\cdot dt
  \\text{error} = T_{set} - T_{current}
  \\text{correction} = K_p \\cdot \\text{error} + K_i \\cdot \\int \\text{error}\\,dt
"""
from __future__ import annotations

from dataclasses import dataclass, field

from terra_core.contracts.schemas import (
    RegulatorState,
    RegulatorStatus,
    TerraPhysicsConfig,
)


@dataclass
class HomeostasisConfig:
    """항상성 제어기 설정 파라미터."""

    # 목표 온도 [K]
    target_temp_k: float = 293.0
    # 목표 압력 [Pa]
    target_pressure_pa: float = 101325.0
    # 목표 pH
    target_ph: float = 7.0
    # 온도 비례 게인
    kp_temp: float = 0.1
    # 온도 적분 게인
    ki_temp: float = 0.01
    # 최대 허용 온도 [K]
    max_temp_k: float = 320.0
    # 최소 허용 온도 [K]
    min_temp_k: float = 270.0
    # 열 용량 [J/K]
    thermal_capacity_j_per_k: float = 1e9
    # 방열판 면적 [m²]
    radiator_area_m2: float = 200.0
    # 방열판 방사율 [0, 1]
    emissivity: float = 0.9


class HomeostasisController:
    """항상성 제어기.

    Stefan-Boltzmann 복사 방열과 PID 제어로 온도를 조절한다.
    """

    def __init__(self, config: HomeostasisConfig):
        self.config = config
        self._integral_error: float = 0.0

    def _radiated_power_mw(self, temp_k: float, physics: TerraPhysicsConfig) -> float:
        """Stefan-Boltzmann 복사 방열 [MW].

        Q_rad = ε · σ · A · T⁴
        """
        q_w = (
            self.config.emissivity
            * physics.sigma_sb
            * self.config.radiator_area_m2
            * (temp_k ** 4)
        )
        return q_w / 1e6  # W → MW

    def _thermal_margin(self, temp_k: float) -> float:
        """열 여유 [0, 1].

        온도가 목표 범위 내일수록 1에 가까움.
        """
        cfg = self.config
        span = cfg.max_temp_k - cfg.min_temp_k
        if span <= 0:
            return 1.0
        dist_from_target = abs(temp_k - cfg.target_temp_k)
        half_span = span / 2.0
        return max(0.0, 1.0 - dist_from_target / half_span)

    def _classify_status(self, temp_k: float) -> RegulatorStatus:
        """온도 기반 조절기 상태 분류."""
        cfg = self.config
        if temp_k < cfg.min_temp_k or temp_k > cfg.max_temp_k:
            return RegulatorStatus.CRITICAL
        margin = self._thermal_margin(temp_k)
        if margin < 0.2:
            return RegulatorStatus.UNSTABLE
        if margin < 0.6:
            return RegulatorStatus.NOMINAL
        return RegulatorStatus.OPTIMAL

    def tick(
        self,
        state: RegulatorState,
        heat_input_mw: float,
        dt_s: float,
        physics: TerraPhysicsConfig,
    ) -> RegulatorState:
        """단일 타임스텝 항상성 갱신.

        온도 PID 제어:
        - 열 입력 - 방열 → 온도 변화
        - thermal_margin 계산
        - RegulatorStatus 판정

        Args:
            state: 현재 조절기 상태
            heat_input_mw: 열 입력 [MW]
            dt_s: 타임스텝 [s]
            physics: 물리 상수

        Returns:
            갱신된 RegulatorState
        """
        cfg = self.config
        T = state.temperature_k

        # 복사 방열 계산
        q_rad_mw = self._radiated_power_mw(T, physics)

        # 열 균형: ΔT = (Q_in - Q_rad) / C_thermal × dt
        # [MW] → [W] = × 1e6
        delta_q_w = (heat_input_mw - q_rad_mw) * 1e6  # [W]
        delta_t = delta_q_w * dt_s / cfg.thermal_capacity_j_per_k  # [K]

        # PID 보정 (간단한 PI 제어)
        error = cfg.target_temp_k - T
        self._integral_error += error * dt_s
        correction = cfg.kp_temp * error + cfg.ki_temp * self._integral_error

        new_T = T + delta_t + correction * dt_s
        new_T = max(cfg.min_temp_k * 0.8, min(new_T, cfg.max_temp_k * 1.2))

        thermal_margin = self._thermal_margin(new_T)
        pressure_margin = 1.0 - abs(state.pressure_pa - cfg.target_pressure_pa) / cfg.target_pressure_pa

        status = self._classify_status(new_T)

        return RegulatorState(
            t_s=state.t_s + dt_s,
            status=status,
            temperature_k=new_T,
            pressure_pa=state.pressure_pa,
            ph=state.ph,
            magnetic_field_t=state.magnetic_field_t,
            radiation_dose_sv_hr=state.radiation_dose_sv_hr,
            thermal_margin=max(0.0, thermal_margin),
            pressure_margin=max(0.0, min(1.0, pressure_margin)),
        )
