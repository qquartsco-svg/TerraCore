"""
양성자-양성자 체인 (pp chain)
태양 같은 별의 주요 에너지원.

반응식:
  4 ¹H → ⁴He + 2e⁺ + 2ν_e + 26.731 MeV

세부 경로 (pp-I, 85%):
  p + p → ²H + e⁺ + ν_e  (느린 약한 상호작용)
  ²H + p → ³He + γ
  ³He + ³He → ⁴He + 2p

반응률 근사:
  ε_pp ∝ ρ² · X² · T⁴  (T ≈ 10⁷~10⁸ K)
  여기서 X = 수소 질량 분율, ρ = 밀도

점화 온도: T > 4×10⁶ K (0.34 keV)
태양 코어: T ≈ 1.5×10⁷ K, ρ ≈ 1.5×10⁵ kg/m³

LaTeX:
  \\varepsilon_{pp} \\propto \\rho^2 X^2 T^4
  P_{pp} = r_{pp} \\cdot Q_{MeV} \\cdot E_{MeV\\to J} \\cdot N_A
"""
from __future__ import annotations

from dataclasses import dataclass

from terra_core.contracts.schemas import TerraPhysicsConfig


@dataclass
class PPChainConfig:
    """pp chain 반응로 설정 파라미터."""

    # 최소 점화 온도 [K]
    min_ignition_temp_k: float = 4e6
    # 참조 온도 (태양 코어) [K]
    reference_temp_k: float = 1.5e7
    # 참조 밀도 [kg/m³]
    reference_density: float = 1.5e5
    # 참조 반응률 [mol/s]
    reference_rate_mol_s: float = 1.0
    # Q 값 [MeV]
    q_value_mev: float = 26.731


class PPChain:
    """양성자-양성자 체인 반응 계산기.

    태양의 pp chain 반응률을 파라메트릭 스케일링으로 근사한다.
    """

    def __init__(self, config: PPChainConfig):
        self.config = config

    def rate(
        self,
        temp_k: float,
        density_kgm3: float,
        h_fraction: float,
    ) -> float:
        """pp chain 반응률 [mol/s].

        ε ∝ ρ² · X² · (T / T_ref)^4

        Args:
            temp_k: 반응로 코어 온도 [K]
            density_kgm3: 코어 밀도 [kg/m³]
            h_fraction: 수소 질량 분율 [0, 1]

        Returns:
            반응률 [mol/s]  — T < min_ignition_temp_k 이면 0
        """
        if temp_k < self.config.min_ignition_temp_k:
            return 0.0

        cfg = self.config
        rho_ratio = density_kgm3 / cfg.reference_density
        t_ratio = temp_k / cfg.reference_temp_k
        x_ratio = h_fraction  # X / 1 (정규화된 질량 분율)

        # ε_pp ∝ ρ² · X² · T^4
        return cfg.reference_rate_mol_s * (rho_ratio ** 2) * (x_ratio ** 2) * (t_ratio ** 4)

    def power_mw(self, rate_mol_s: float, physics: TerraPhysicsConfig) -> float:
        """pp chain 출력 [MW].

        P = rate [mol/s] × Q [MeV] × mev_to_j [J/MeV] × N_A [/mol]
        → 단위: [mol/s × MeV × J/MeV × /mol] = [J/s] = [W]

        Args:
            rate_mol_s: 반응률 [mol/s]
            physics: 물리 상수 컨테이너

        Returns:
            출력 [MW]
        """
        power_w = rate_mol_s * self.config.q_value_mev * physics.mev_to_j * physics.n_a
        return power_w / 1e6  # W → MW

    def he4_production_mol_s(self, rate_mol_s: float) -> float:
        """He-4 생성률 [mol/s].

        반응 1회당 He-4 1개 생성: 4H → He + ...
        """
        return rate_mol_s  # 1:1 비율

    def tick(
        self,
        temp_k: float,
        density: float,
        h_frac: float,
        dt_s: float,
        physics: TerraPhysicsConfig,
    ) -> tuple:
        """단일 타임스텝 계산.

        Returns:
            (rate_mol_s [mol/s], power_mw [MW])
        """
        r = self.rate(temp_k, density, h_frac)
        p = self.power_mw(r, physics)
        return r, p
