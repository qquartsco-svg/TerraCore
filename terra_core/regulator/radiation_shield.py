"""
방사선 차폐 모델

지구 자기장 차폐 원리:
  - 지구 자기장 B ≈ 25~65 μT
  - 반 알렌 대 (Van Allen Belt): 고에너지 입자 포획
  - Lorentz 힘: F = q(v × B)
  - 하전 입자 편향: r = mv/(qB) (자기강성)

우주 방사선 종류:
  1. 은하우주선 (GCR): 고에너지 양성자/핵
  2. 태양 에너지 입자 (SEP): 태양 플레어
  3. 반 알렌 대 입자

방호 기준:
  ISS 승무원: ~1 mSv/day
  지구 표면: 0.003 mSv/day
  6개월 임무 한계: ~180 mSv (ICRP 기준)

자기장 차폐 효과:
  B ≥ 0.1 T → GCR 50% 감소 (근사)
  B ≥ 0.5 T → GCR 80% 감소

LaTeX:
  F = q(\\mathbf{v} \\times \\mathbf{B})
  r = \\frac{mv}{qB}  \\quad (\\text{자기강성})
  \\eta_{shield}(B) = 1 - e^{-B/B_0}  \\quad (B_0 = 0.2\\,T)
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from terra_core.contracts.schemas import RegulatorState


@dataclass
class RadiationShieldConfig:
    """방사선 차폐 설정 파라미터."""

    # 자기장 강도 [T]
    magnetic_field_t: float = 0.1
    # 우주 배경 방사선 선량률 [Sv/day]
    background_dose_sv_day: float = 1e-3
    # 허용 한계 [Sv/hr]
    max_dose_sv_hr: float = 1e-4
    # 물리 차폐재 질량 [kg]
    shielding_mass_kg: float = 5000.0


class RadiationShield:
    """방사선 차폐 계산기.

    자기장과 물리 차폐재를 결합해 방사선 선량률을 계산한다.
    """

    def __init__(self, config: RadiationShieldConfig):
        self.config = config

    def magnetic_attenuation(self, B_tesla: float) -> float:
        """자기장 차폐 감쇠 인자 [0, 1].

        1 = 완전 차폐, 0 = 차폐 없음.

        η(B) = 1 - exp(-B / B₀),  B₀ = 0.2 T

        Args:
            B_tesla: 자기장 강도 [T]

        Returns:
            감쇠 인자 [0, 1]
        """
        if B_tesla <= 0.0:
            return 0.0
        B0 = 0.2  # [T] 특성 차폐 자기장
        return 1.0 - math.exp(-B_tesla / B0)

    def physical_attenuation(self) -> float:
        """물리 차폐재 감쇠 인자 [0, 1].

        차폐재 질량에 비례 (5000 kg → 30% 추가 감쇠 근사).
        """
        mass = self.config.shielding_mass_kg
        reference_mass = 5000.0  # [kg]
        return min(0.3, 0.3 * (mass / reference_mass))

    def dose_rate_sv_hr(self, B_tesla: float) -> float:
        """방사선 선량률 [Sv/hr].

        배경 선량에 자기장·물리 차폐 감쇠를 적용한다.

        Args:
            B_tesla: 현재 자기장 강도 [T]

        Returns:
            선량률 [Sv/hr]
        """
        # 배경 선량 [Sv/day] → [Sv/hr]
        background_sv_hr = self.config.background_dose_sv_day / 24.0

        # 총 감쇠
        mag_atten = self.magnetic_attenuation(B_tesla)
        phys_atten = self.physical_attenuation()

        total_attenuation = mag_atten + phys_atten - mag_atten * phys_atten  # 병렬 조합
        total_attenuation = min(total_attenuation, 0.99)  # 완전 차폐 불가

        return background_sv_hr * (1.0 - total_attenuation)

    def tick(
        self,
        state: RegulatorState,
        dt_s: float,
    ) -> RegulatorState:
        """단일 타임스텝 방사선 갱신.

        Args:
            state: 현재 조절기 상태
            dt_s: 타임스텝 [s]

        Returns:
            갱신된 RegulatorState (방사선 선량 업데이트)
        """
        dose = self.dose_rate_sv_hr(state.magnetic_field_t)

        return RegulatorState(
            t_s=state.t_s + dt_s,
            status=state.status,
            temperature_k=state.temperature_k,
            pressure_pa=state.pressure_pa,
            ph=state.ph,
            magnetic_field_t=state.magnetic_field_t,
            radiation_dose_sv_hr=dose,
            thermal_margin=state.thermal_margin,
            pressure_margin=state.pressure_margin,
        )
