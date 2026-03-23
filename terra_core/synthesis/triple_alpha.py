"""
삼중 알파 과정 (Triple-Alpha Process)
He-4 3개가 C-12를 생성하는 2단계 핵반응.
적색거성 진화의 핵심.

반응 경로:
  ⁴He + ⁴He → ⁸Be  (불안정, τ ≈ 10⁻¹⁶ s)
  ⁸Be + ⁴He → ¹²C* (Hoyle 공명 상태, 7.6549 MeV)
  ¹²C*       → ¹²C + 2γ (0.04% 분기율)

Hoyle 공명:
  Fred Hoyle 1954년 예측 — C-12의 7.6549 MeV 공명 상태가
  없으면 우주에 탄소가 거의 없었을 것.
  "Fine-tuned universe"의 대표적 사례.

알짜: 3⁴He → ¹²C + 7.275 MeV

반응률:
  ε_3α ∝ ρ² · Y³ · T^40  (Y = He-4 질량 분율)
  T^40 의존성 → 온도에 극도로 민감

점화 온도: T > 10⁸ K (8.6 keV)
(pp chain보다 10배 높은 온도 필요)

LaTeX:
  \\varepsilon_{3\\alpha} \\propto \\rho^2 Y^3 (T/T_{ref})^{40}
  E_{Hoyle} = 7.6549\\,\\text{MeV}
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from terra_core.contracts.schemas import TerraPhysicsConfig


@dataclass
class TripleAlphaConfig:
    """삼중 알파 과정 설정 파라미터."""

    # 최소 점화 온도 [K]
    min_temp_k: float = 1.0e8
    # 참조 온도 [K]
    reference_temp_k: float = 2.0e8
    # 참조 반응률 [mol/s]
    reference_rate_mol_s: float = 0.01
    # Q 값 [MeV]
    q_value_mev: float = 7.275
    # 온도 지수 (T^40 의존성)
    temp_exponent: float = 40.0
    # Hoyle 공명 에너지 [MeV]
    hoyle_resonance_mev: float = 7.6549


class TripleAlpha:
    """삼중 알파 과정 반응 계산기.

    He-4 3개가 C-12를 생성하는 2단계 핵반응을 계산한다.
    T^40 의존성으로 인해 임계 온도 근처에서 반응률이 급격히 변한다.
    """

    def __init__(self, config: TripleAlphaConfig):
        self.config = config

    def rate(
        self,
        temp_k: float,
        density: float,
        he4_frac: float,
    ) -> float:
        """삼중 알파 반응률 [mol/s].

        ε_3α ∝ ρ² · Y³ · (T / T_ref)^40

        Args:
            temp_k: 코어 온도 [K]
            density: 코어 밀도 [kg/m³]
            he4_frac: He-4 질량 분율 [0, 1]

        Returns:
            반응률 [mol/s] — T < min_temp_k 이면 0
        """
        if temp_k < self.config.min_temp_k:
            return 0.0

        cfg = self.config
        rho_ref = 1.5e5  # [kg/m³]
        rho_ratio = density / rho_ref

        t_ratio = temp_k / cfg.reference_temp_k
        if t_ratio <= 0.0:
            return 0.0

        # 오버플로 방지: exp(min(..., 700))
        t_exp = min(cfg.temp_exponent * math.log(t_ratio), 700.0)
        t_factor = math.exp(t_exp)

        return cfg.reference_rate_mol_s * (rho_ratio ** 2) * (he4_frac ** 3) * t_factor

    def c12_production_mol_s(self, rate_mol_s: float) -> float:
        """C-12 생성률 [mol/s].

        반응 1회당 C-12 1개 생성: 3⁴He → ¹²C
        """
        return rate_mol_s

    def power_mw(self, rate_mol_s: float, physics: TerraPhysicsConfig) -> float:
        """삼중 알파 출력 [MW]."""
        power_w = rate_mol_s * self.config.q_value_mev * physics.mev_to_j * physics.n_a
        return power_w / 1e6

    def tick(
        self,
        temp_k: float,
        density: float,
        he4_frac: float,
        dt_s: float,
        physics: TerraPhysicsConfig,
    ) -> tuple:
        """단일 타임스텝 계산.

        Returns:
            (rate_mol_s [mol/s], power_mw [MW], c12_mol_s [mol/s])
        """
        r = self.rate(temp_k, density, he4_frac)
        p = self.power_mw(r, physics)
        c12 = self.c12_production_mol_s(r)
        return r, p, c12
