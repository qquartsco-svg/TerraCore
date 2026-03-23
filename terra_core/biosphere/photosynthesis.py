"""
광합성 모델

반응식:
  6CO₂ + 6H₂O + 빛(에너지) → C₆H₁₂O₆ + 6O₂
  ΔG = -2870 kJ/mol

광합성 효율:
  이론 최대: ~11% (태양광 대비)
  실제 식물: 1~3%
  우주선 (LED + 최적화): 5~8% 가정

Michaelis-Menten CO₂ 반응 모델:
  rate = V_max · [CO₂] / (K_m + [CO₂])
  V_max = 최대 광합성률
  K_m ≈ 200 ppm (포화 절반 농도)

바이오매스 성장:
  dB/dt = μ_max · B · (CO₂ / (K_CO2 + CO₂)) · (light / (K_light + light))
  - 로지스틱 성장 (B_max 포화)

LaTeX:
  r_{photo} = V_{max} \\cdot B \\cdot \\frac{[CO_2]}{K_m + [CO_2]}
  \\frac{dB}{dt} = \\mu_{max} \\cdot B \\cdot \\left(1 - \\frac{B}{B_{max}}\\right)
                   \\cdot \\frac{[CO_2]}{K_{CO_2} + [CO_2]}
"""
from __future__ import annotations

from dataclasses import dataclass

from terra_core.contracts.schemas import BiosphereState, BiosphereStatus


@dataclass
class PhotosynthesisConfig:
    """광합성 엔진 설정 파라미터."""

    # 단위 바이오매스당 최대 광합성률 [mol CO₂/s/kg]
    v_max_mol_s_per_kg: float = 1e-5
    # Michaelis 상수 [ppm]
    k_m_co2_ppm: float = 200.0
    # 광 에너지→화학 에너지 효율
    light_efficiency: float = 0.06
    # 최대 성장률 [s⁻¹]
    mu_max_per_s: float = 1e-6
    # 최대 바이오매스 [kg]
    biomass_max_kg: float = 5000.0
    # 바이오매스 중 식량 분율
    food_fraction: float = 0.3
    # 초기 바이오매스 [kg]
    initial_biomass_kg: float = 100.0


class PhotosynthesisEngine:
    """광합성 및 바이오매스 성장 계산기.

    Michaelis-Menten 동역학으로 CO₂ 흡수율을 계산하고,
    로지스틱 성장 모델로 바이오매스 증가를 추적한다.
    """

    def __init__(self, config: PhotosynthesisConfig):
        self.config = config

    def photosynthesis_rate(
        self,
        biomass_kg: float,
        co2_ppm: float,
        light_mw: float,
    ) -> float:
        """Michaelis-Menten 광합성률 [mol CO₂/s].

        rate = V_max · B · [CO₂] / (K_m + [CO₂]) · f(light)

        Args:
            biomass_kg: 현재 바이오매스 [kg]
            co2_ppm: CO₂ 농도 [ppm]
            light_mw: 광원 전력 [MW]

        Returns:
            CO₂ 흡수율 [mol/s]
        """
        if biomass_kg <= 0.0 or co2_ppm <= 0.0:
            return 0.0

        cfg = self.config
        # Michaelis-Menten
        mm_factor = co2_ppm / (cfg.k_m_co2_ppm + co2_ppm)

        # 광 제한 인자 (Michaelis-Menten 형태, K_light = 1 MW)
        k_light_mw = 1.0
        light_factor = light_mw / (k_light_mw + light_mw) if light_mw > 0 else 0.0

        return cfg.v_max_mol_s_per_kg * biomass_kg * mm_factor * light_factor

    def o2_production_mol_s(self, co2_uptake_mol_s: float) -> float:
        """O₂ 생산률 [mol/s].

        6CO₂ + 6H₂O → C₆H₁₂O₆ + 6O₂  →  CO₂:O₂ = 1:1 몰비
        """
        return co2_uptake_mol_s

    def biomass_growth_rate(
        self,
        biomass_kg: float,
        co2_ppm: float,
        light_mw: float,
    ) -> float:
        """로지스틱 성장률 dB/dt [kg/s].

        dB/dt = μ_max · B · (1 - B/B_max) · MM(CO₂) · MM(light)
        """
        if biomass_kg <= 0.0 or co2_ppm <= 0.0:
            return 0.0

        cfg = self.config
        logistic = 1.0 - (biomass_kg / cfg.biomass_max_kg)
        if logistic <= 0.0:
            return 0.0

        mm_co2 = co2_ppm / (cfg.k_m_co2_ppm + co2_ppm)
        k_light_mw = 1.0
        mm_light = light_mw / (k_light_mw + light_mw) if light_mw > 0 else 0.0

        return cfg.mu_max_per_s * biomass_kg * logistic * mm_co2 * mm_light

    def food_production_kg_day(self, biomass_kg: float) -> float:
        """식량 생산률 [kg/day].

        전체 바이오매스의 food_fraction 분율이 식량으로 수확 가능.
        하루 기준 수확률 ≈ 0.01 (1%/day)
        """
        harvest_rate_per_day = 0.01  # 1%/day
        return biomass_kg * self.config.food_fraction * harvest_rate_per_day

    def _classify_status(self, biomass_kg: float) -> BiosphereStatus:
        """바이오매스 기반 생태계 상태 분류."""
        cfg = self.config
        if biomass_kg <= 0.0:
            return BiosphereStatus.DEAD
        if biomass_kg < 10.0:
            return BiosphereStatus.SEEDING
        if biomass_kg < cfg.biomass_max_kg * 0.3:
            return BiosphereStatus.GROWING
        if biomass_kg < cfg.biomass_max_kg * 0.7:
            return BiosphereStatus.STABLE
        return BiosphereStatus.THRIVING

    def tick(
        self,
        state: BiosphereState,
        co2_ppm: float,
        light_power_mw: float,
        dt_s: float,
    ) -> BiosphereState:
        """단일 타임스텝 생태계 갱신.

        Args:
            state: 현재 생태계 상태
            co2_ppm: 현재 CO₂ 농도 [ppm]
            light_power_mw: 광원 전력 [MW]
            dt_s: 타임스텝 [s]

        Returns:
            갱신된 BiosphereState
        """
        biomass = state.plant_biomass_kg

        co2_uptake = self.photosynthesis_rate(biomass, co2_ppm, light_power_mw)
        o2_release = self.o2_production_mol_s(co2_uptake)
        growth = self.biomass_growth_rate(biomass, co2_ppm, light_power_mw)
        new_biomass = max(0.0, biomass + growth * dt_s)
        food = self.food_production_kg_day(new_biomass)
        status = self._classify_status(new_biomass)

        return BiosphereState(
            t_s=state.t_s + dt_s,
            status=status,
            plant_biomass_kg=new_biomass,
            co2_uptake_mol_s=co2_uptake,
            o2_release_mol_s=o2_release,
            food_production_kg_day=food,
            nitrogen_fixed_mol_s=state.nitrogen_fixed_mol_s,
            growth_rate=growth / max(biomass, 1.0),
        )
