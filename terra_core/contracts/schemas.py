"""
TerraCore 계약 스키마 — 불변 상태 객체 및 열거형

태양계는 수소 핵융합을 에너지원으로 삼아 원소를 합성하고,
중력으로 분류해서 행성 환경을 만드는 자가순환 시스템이다.
지구는 그 안의 닫힌 루프 생명 유지 노드다.
TerraCore는 이 구조를 우주선 안에 구현한다.

상태는 궤적 위의 관측값이다.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Tuple


# ---------------------------------------------------------------------------
# 물리 상수 및 파라미터 컨테이너
# ---------------------------------------------------------------------------

@dataclass
class TerraPhysicsConfig:
    """TerraCore 전역 물리 상수 — Config 주입 방식으로 사용."""

    # 볼츠만 상수 [J/K]
    k_b: float = 1.380649e-23
    # 스테판-볼츠만 상수 [W/(m²·K⁴)]
    sigma_sb: float = 5.670374e-8
    # 아보가드로 수 [mol⁻¹]
    n_a: float = 6.02214076e23
    # 기체 상수 [J/(mol·K)]
    r_gas: float = 8.314462
    # 표준 중력 가속도 [m/s²]
    g0: float = 9.80665
    # eV → J 변환
    ev_to_j: float = 1.602176634e-19
    # keV → J 변환
    kev_to_j: float = 1.602176634e-16
    # MeV → J 변환
    mev_to_j: float = 1.602176634e-13
    # 태양 코어 온도 참조 [K]
    t_solar_core_k: float = 1.5e7
    # 태양 코어 밀도 참조 [kg/m³]
    rho_solar_core: float = 1.5e5


# ---------------------------------------------------------------------------
# 열거형
# ---------------------------------------------------------------------------

class SynthesisPhase(Enum):
    """핵합성 반응로 단계."""
    INACTIVE = auto()
    PP_CHAIN = auto()
    CNO_ACTIVE = auto()
    TRIPLE_ALPHA = auto()
    CARBON_BURNING = auto()
    EQUILIBRIUM = auto()


class AtmosphereStatus(Enum):
    """대기 상태 분류."""
    VACUUM = auto()
    THIN = auto()
    NOMINAL = auto()
    RICH = auto()
    TOXIC = auto()


class BiosphereStatus(Enum):
    """생태계 상태 분류."""
    DEAD = auto()
    SEEDING = auto()
    GROWING = auto()
    STABLE = auto()
    THRIVING = auto()


class RegulatorStatus(Enum):
    """조절기 상태 분류."""
    CRITICAL = auto()
    UNSTABLE = auto()
    NOMINAL = auto()
    OPTIMAL = auto()


# ---------------------------------------------------------------------------
# 불변 상태 데이터클래스
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ElementInventory:
    """원소 재고 — 우주선 내 화학 원소 총량 [mol].

    원소는 핵합성 반응을 통해 생성되고, 생명 유지 사이클을 통해 순환한다.
    """

    # H 재고 [mol]
    hydrogen_mol: float
    # He 재고 [mol]
    helium_mol: float
    # C 재고 [mol]
    carbon_mol: float
    # N 재고 [mol]
    nitrogen_mol: float
    # O 재고 [mol]
    oxygen_mol: float
    # H₂O 재고 [mol]
    water_mol: float
    # CO₂ 재고 [mol]
    co2_mol: float
    # NH₃ 재고 [mol]
    ammonia_mol: float
    # 총 질량 [kg] (근사)
    total_mass_kg: float

    def o2_fraction(self) -> float:
        """O₂ 기압 분율 [0, 1] — O₂ mol / (O₂ + N₂) mol 근사."""
        total = self.oxygen_mol + self.nitrogen_mol
        if total <= 0.0:
            return 0.0
        return self.oxygen_mol / total

    def co2_ppm(self) -> float:
        """CO₂ 농도 [ppm] — CO₂ mol / (CO₂ + O₂ + N₂) × 1e6."""
        total = self.co2_mol + self.oxygen_mol + self.nitrogen_mol
        if total <= 0.0:
            return 0.0
        return (self.co2_mol / total) * 1e6

    def n2_fraction(self) -> float:
        """N₂ 몰분율 [0, 1]."""
        total = self.co2_mol + self.oxygen_mol + self.nitrogen_mol
        if total <= 0.0:
            return 0.0
        return self.nitrogen_mol / total


@dataclass(frozen=True)
class SynthesisState:
    """핵합성 엔진 관측 상태 — 궤적 위의 한 점."""

    # 관측 시각 [s]
    t_s: float
    # 반응 단계
    phase: SynthesisPhase
    # 반응로 코어 온도 [K]
    core_temp_k: float
    # 코어 밀도 [kg/m³]
    core_density_kgm3: float
    # pp chain 반응률 [mol/s]
    pp_rate_mol_s: float
    # CNO 반응률 [mol/s]
    cno_rate_mol_s: float
    # 삼중 알파 반응률 [mol/s]
    triple_alpha_rate_mol_s: float
    # 총 출력 [MW]
    power_output_mw: float
    # He-4 생성률 [mol/s]
    he4_produced_mol_s: float
    # C-12 생성률 [mol/s]
    c12_produced_mol_s: float


@dataclass(frozen=True)
class AtmosphereState:
    """대기 관측 상태."""

    # 관측 시각 [s]
    t_s: float
    # 대기 상태
    status: AtmosphereStatus
    # 총 대기압 [Pa]
    total_pressure_pa: float
    # O₂ 분압 [Pa]
    o2_partial_pa: float
    # N₂ 분압 [Pa]
    n2_partial_pa: float
    # CO₂ 분압 [Pa]
    co2_partial_pa: float
    # 수증기 분압 [Pa]
    h2o_vapor_pa: float
    # 대기 온도 [K]
    temperature_k: float
    # O₂ 몰분율 [0, 1]
    o2_fraction: float
    # CO₂ 농도 [ppm]
    co2_ppm: float
    # 호흡 가능 여부
    breathable: bool


@dataclass(frozen=True)
class HydrosphereState:
    """수권 관측 상태."""

    # 관측 시각 [s]
    t_s: float
    # 총 수분 재고 [mol]
    water_total_mol: float
    # 액체 분율 [0, 1]
    liquid_fraction: float
    # 전기분해율 [mol/s]
    electrolysis_rate_mol_s: float
    # H₂ 생성률 [mol/s]
    h2_produced_mol_s: float
    # 전기분해 O₂ 생성률 [mol/s]
    o2_from_water_mol_s: float
    # 소비 전력 [MW]
    power_consumed_mw: float
    # 잔여 수분 분율 [0, 1]
    water_margin: float


@dataclass(frozen=True)
class BiosphereState:
    """생태계 관측 상태."""

    # 관측 시각 [s]
    t_s: float
    # 생태계 상태
    status: BiosphereStatus
    # 식물 바이오매스 [kg]
    plant_biomass_kg: float
    # CO₂ 흡수율 [mol/s]
    co2_uptake_mol_s: float
    # O₂ 방출율 [mol/s]
    o2_release_mol_s: float
    # 식량 생산률 [kg/day]
    food_production_kg_day: float
    # N₂ 고정률 [mol/s]
    nitrogen_fixed_mol_s: float
    # 바이오매스 성장률 [0, 1/s]
    growth_rate: float


@dataclass(frozen=True)
class RegulatorState:
    """조절기 관측 상태."""

    # 관측 시각 [s]
    t_s: float
    # 조절기 상태
    status: RegulatorStatus
    # 내부 온도 [K]
    temperature_k: float
    # 내부 압력 [Pa]
    pressure_pa: float
    # pH [0, 14]
    ph: float
    # 자기장 강도 [T]
    magnetic_field_t: float
    # 방사선 선량률 [Sv/hr]
    radiation_dose_sv_hr: float
    # 열 여유 [0, 1]
    thermal_margin: float
    # 압력 여유 [0, 1]
    pressure_margin: float


@dataclass(frozen=True)
class TerraState:
    """TerraCore 전체 시스템 통합 상태 — 궤적 위의 관측 스냅샷."""

    # 관측 시각 [s]
    t_s: float
    elements: ElementInventory
    synthesis: SynthesisState
    atmosphere: AtmosphereState
    hydrosphere: HydrosphereState
    biosphere: BiosphereState
    regulator: RegulatorState

    def summary_dict(self) -> dict:
        """요약 딕셔너리 반환."""
        return {
            "t_s": self.t_s,
            "synthesis_phase": self.synthesis.phase.name,
            "power_mw": self.synthesis.power_output_mw,
            "atmosphere_status": self.atmosphere.status.name,
            "breathable": self.atmosphere.breathable,
            "co2_ppm": self.atmosphere.co2_ppm,
            "o2_fraction": self.atmosphere.o2_fraction,
            "water_margin": self.hydrosphere.water_margin,
            "biomass_kg": self.biosphere.plant_biomass_kg,
            "biosphere_status": self.biosphere.status.name,
            "temperature_k": self.regulator.temperature_k,
            "regulator_status": self.regulator.status.name,
            "radiation_sv_hr": self.regulator.radiation_dose_sv_hr,
        }


@dataclass(frozen=True)
class TerraHealth:
    """TerraCore 종합 건전성 지표 — Ω (오메가) 체계."""

    # 종합 건전성 [0, 1]
    omega_terra: float
    omega_synthesis: float
    omega_atmosphere: float
    omega_hydrosphere: float
    omega_biosphere: float
    omega_regulator: float
    # 판정: THRIVING / STABLE / FRAGILE / CRITICAL
    verdict: str
    # 경보 목록
    alerts: tuple
    # 중단 필요 여부
    abort_required: bool


@dataclass(frozen=True)
class TelemetryFrame:
    """단일 텔레메트리 프레임 — 감사 체인에 기록되는 단위."""

    # 프레임 시각 [s]
    t_s: float
    state: TerraState
    health: TerraHealth
    abort_required: bool

    def summary_dict(self) -> dict:
        """요약 딕셔너리 반환."""
        return {
            "t_s": self.t_s,
            "omega_terra": self.health.omega_terra,
            "verdict": self.health.verdict,
            "abort_required": self.abort_required,
            "alerts": list(self.health.alerts),
            **self.state.summary_dict(),
        }
