"""
CNO 순환 (Carbon-Nitrogen-Oxygen Cycle)
탄소를 촉매로 사용하는 수소→헬륨 핵융합.
태양 질량의 1.3배 이상 별에서 지배적.

순환 경로:
  ¹²C + p → ¹³N + γ
  ¹³N    → ¹³C + e⁺ + ν
  ¹³C + p → ¹⁴N + γ
  ¹⁴N + p → ¹⁵O + γ   ← 속도 제한 단계
  ¹⁵O    → ¹⁵N + e⁺ + ν
  ¹⁵N + p → ¹²C + ⁴He  ← C-12 재생!

알짜 반응: 4p → ⁴He + 2e⁺ + 2ν + 25.0 MeV
C-12는 소비되지 않고 재생 → 진짜 촉매

반응률:
  ε_CNO ∝ ρ · X · X_CNO · T^20
  X_CNO = 탄소+질소+산소 질량 분율
  T^20 의존성 → 온도에 극도로 민감

점화 온도: T > 1.5×10⁷ K
CNO가 pp를 초과하는 온도: T ≈ 1.7×10⁷ K

LaTeX:
  \\varepsilon_{CNO} \\propto \\rho \\cdot X \\cdot X_{CNO} \\cdot (T/T_{ref})^{20}
"""
from __future__ import annotations

from dataclasses import dataclass

from terra_core.contracts.schemas import TerraPhysicsConfig


@dataclass
class CNOCycleConfig:
    """CNO 순환 설정 파라미터."""

    # 최소 점화 온도 [K]
    min_temp_k: float = 1.5e7
    # 참조 온도 [K]
    reference_temp_k: float = 2.0e7
    # 참조 반응률 [mol/s]
    reference_rate_mol_s: float = 0.1
    # Q 값 [MeV]
    q_value_mev: float = 25.0
    # 온도 지수 (T^20 의존성)
    temp_exponent: float = 20.0


class CNOCycle:
    """CNO 순환 반응 계산기.

    탄소가 촉매로 작용하는 수소→헬륨 핵융합 반응률을 계산한다.
    T^20 의존성으로 인해 온도에 극도로 민감하다.
    """

    def __init__(self, config: CNOCycleConfig):
        self.config = config

    def rate(
        self,
        temp_k: float,
        density: float,
        h_frac: float,
        cno_frac: float,
    ) -> float:
        """CNO 반응률 [mol/s].

        ε_CNO ∝ ρ · X · X_CNO · (T / T_ref)^20

        Args:
            temp_k: 코어 온도 [K]
            density: 코어 밀도 [kg/m³]
            h_frac: 수소 질량 분율 [0, 1]
            cno_frac: CNO 원소(C+N+O) 질량 분율 [0, 1]

        Returns:
            반응률 [mol/s] — T < min_temp_k 이면 0
        """
        if temp_k < self.config.min_temp_k:
            return 0.0

        cfg = self.config
        rho_ref = 1.5e5  # 태양 코어 참조 밀도 [kg/m³]
        rho_ratio = density / rho_ref
        t_ratio = temp_k / cfg.reference_temp_k

        # 온도 지수가 크므로 오버플로 방지
        log_t_ratio = cfg.temp_exponent * (t_ratio - 1.0)
        # 지수 계산을 안전하게 수행
        import math
        t_factor = math.exp(min(cfg.temp_exponent * math.log(t_ratio), 700.0))

        return cfg.reference_rate_mol_s * rho_ratio * h_frac * (cno_frac / 0.02) * t_factor

    def c12_regeneration_fraction(self) -> float:
        """C-12 재생 분율.

        이상적: 1.0 (완벽한 촉매), 실제 근사: 0.95
        """
        return 0.95

    def power_mw(self, rate_mol_s: float, physics: TerraPhysicsConfig) -> float:
        """CNO 출력 [MW]."""
        power_w = rate_mol_s * self.config.q_value_mev * physics.mev_to_j * physics.n_a
        return power_w / 1e6

    def tick(
        self,
        temp_k: float,
        density: float,
        h_frac: float,
        cno_frac: float,
        dt_s: float,
        physics: TerraPhysicsConfig,
    ) -> tuple:
        """단일 타임스텝 계산.

        Returns:
            (rate_mol_s [mol/s], power_mw [MW])
        """
        r = self.rate(temp_k, density, h_frac, cno_frac)
        p = self.power_mw(r, physics)
        return r, p
