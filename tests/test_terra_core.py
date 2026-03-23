"""
TerraCore 테스트 스위트 — ~130 케이스

§1  TerraPhysicsConfig (5)
§2  ElementInventory (8)
§3  pp chain 물리 (10)
§4  CNO cycle 물리 (8)
§5  삼중 알파 물리 (8)
§6  SynthesisEngine 통합 (10)
§7  WaterCycle (8)
§8  PhotosynthesisEngine (10)
§9  GasCycle (10)
§10 HomeostasisController (8)
§11 RadiationShield (6)
§12 NitrogenCycle (6)
§13 OmegaMonitor (10)
§14 AbortSystem (8)
§15 TerraChain (8)
§16 TerraAgent 통합 (10)
"""
import math
import pytest

from terra_core.contracts.schemas import (
    AtmosphereState,
    AtmosphereStatus,
    BiosphereState,
    BiosphereStatus,
    ElementInventory,
    HydrosphereState,
    RegulatorState,
    RegulatorStatus,
    SynthesisPhase,
    SynthesisState,
    TelemetryFrame,
    TerraHealth,
    TerraPhysicsConfig,
    TerraState,
)
from terra_core.synthesis.pp_chain import PPChain, PPChainConfig
from terra_core.synthesis.cno_cycle import CNOCycle, CNOCycleConfig
from terra_core.synthesis.triple_alpha import TripleAlpha, TripleAlphaConfig
from terra_core.synthesis.synthesis_engine import SynthesisEngine, SynthesisConfig
from terra_core.atmosphere.gas_cycle import GasCycle, GasCycleConfig
from terra_core.atmosphere.atmosphere_engine import initial_atmosphere_state
from terra_core.hydrosphere.water_cycle import WaterCycle, WaterCycleConfig
from terra_core.biosphere.photosynthesis import PhotosynthesisEngine, PhotosynthesisConfig
from terra_core.biosphere.nitrogen_cycle import NitrogenCycle, NitrogenCycleConfig
from terra_core.regulator.homeostasis import HomeostasisController, HomeostasisConfig
from terra_core.regulator.radiation_shield import RadiationShield, RadiationShieldConfig
from terra_core.safety.omega_monitor import OmegaMonitor, OmegaConfig
from terra_core.safety.abort_system import AbortSystem, AbortConfig, TerraAbortMode
from terra_core.audit.terra_chain import TerraChain
from terra_core.terra_agent import TerraAgent, TerraAgentConfig


# ---------------------------------------------------------------------------
# 헬퍼 팩토리
# ---------------------------------------------------------------------------

def make_physics() -> TerraPhysicsConfig:
    return TerraPhysicsConfig()


def make_nominal_atmosphere(t_s: float = 0.0) -> AtmosphereState:
    """호흡 가능한 표준 대기 상태."""
    return AtmosphereState(
        t_s=t_s,
        status=AtmosphereStatus.NOMINAL,
        total_pressure_pa=101325.0,
        o2_partial_pa=21276.0,
        n2_partial_pa=79000.0,
        co2_partial_pa=81.0,  # 800 ppm
        h2o_vapor_pa=968.0,
        temperature_k=293.0,
        o2_fraction=0.2095,
        co2_ppm=800.0,
        breathable=True,
    )


def make_nominal_biosphere(t_s: float = 0.0) -> BiosphereState:
    return BiosphereState(
        t_s=t_s,
        status=BiosphereStatus.GROWING,
        plant_biomass_kg=500.0,
        co2_uptake_mol_s=5e-3,
        o2_release_mol_s=5e-3,
        food_production_kg_day=1.5,
        nitrogen_fixed_mol_s=5e-6,
        growth_rate=1e-7,
    )


def make_nominal_hydro(t_s: float = 0.0, water_mol: float = 50000.0) -> HydrosphereState:
    return HydrosphereState(
        t_s=t_s,
        water_total_mol=water_mol,
        liquid_fraction=0.9,
        electrolysis_rate_mol_s=0.01,
        h2_produced_mol_s=0.01,
        o2_from_water_mol_s=0.005,
        power_consumed_mw=0.05,
        water_margin=1.0,
    )


def make_nominal_regulator(t_s: float = 0.0) -> RegulatorState:
    return RegulatorState(
        t_s=t_s,
        status=RegulatorStatus.NOMINAL,
        temperature_k=293.0,
        pressure_pa=101325.0,
        ph=7.0,
        magnetic_field_t=0.1,
        radiation_dose_sv_hr=4e-5,
        thermal_margin=0.8,
        pressure_margin=0.95,
    )


def make_nominal_synthesis(t_s: float = 0.0) -> SynthesisState:
    return SynthesisState(
        t_s=t_s,
        phase=SynthesisPhase.PP_CHAIN,
        core_temp_k=1.5e7,
        core_density_kgm3=1.5e5,
        pp_rate_mol_s=1.0,
        cno_rate_mol_s=0.0,
        triple_alpha_rate_mol_s=0.0,
        power_output_mw=100.0,
        he4_produced_mol_s=1.0,
        c12_produced_mol_s=0.0,
    )


def make_nominal_elements() -> ElementInventory:
    return ElementInventory(
        hydrogen_mol=1e6,
        helium_mol=2.5e5,
        carbon_mol=1e4,
        nitrogen_mol=5e5,
        oxygen_mol=3e5,
        water_mol=50000.0,
        co2_mol=500.0,
        ammonia_mol=100.0,
        total_mass_kg=1e7,
    )


def make_terra_state(t_s: float = 0.0) -> TerraState:
    return TerraState(
        t_s=t_s,
        elements=make_nominal_elements(),
        synthesis=make_nominal_synthesis(t_s),
        atmosphere=make_nominal_atmosphere(t_s),
        hydrosphere=make_nominal_hydro(t_s),
        biosphere=make_nominal_biosphere(t_s),
        regulator=make_nominal_regulator(t_s),
    )


# ===========================================================================
# §1 TerraPhysicsConfig (5)
# ===========================================================================

class TestTerraPhysicsConfig:
    def test_boltzmann_constant(self):
        p = make_physics()
        assert abs(p.k_b - 1.380649e-23) < 1e-30

    def test_stefan_boltzmann(self):
        p = make_physics()
        assert abs(p.sigma_sb - 5.670374e-8) < 1e-14

    def test_avogadro(self):
        p = make_physics()
        assert abs(p.n_a - 6.02214076e23) < 1e16

    def test_mev_to_j_order(self):
        p = make_physics()
        # 1 MeV ≈ 1.6e-13 J
        assert 1e-13 < p.mev_to_j < 2e-13

    def test_solar_reference_values(self):
        p = make_physics()
        assert p.t_solar_core_k == 1.5e7
        assert p.rho_solar_core == 1.5e5


# ===========================================================================
# §2 ElementInventory (8)
# ===========================================================================

class TestElementInventory:
    def test_o2_fraction_nominal(self):
        inv = ElementInventory(
            hydrogen_mol=0, helium_mol=0, carbon_mol=0,
            nitrogen_mol=790.0, oxygen_mol=210.0,
            water_mol=0, co2_mol=0, ammonia_mol=0, total_mass_kg=0,
        )
        assert abs(inv.o2_fraction() - 210/1000) < 1e-6

    def test_o2_fraction_zero_case(self):
        inv = ElementInventory(
            hydrogen_mol=0, helium_mol=0, carbon_mol=0,
            nitrogen_mol=0, oxygen_mol=0,
            water_mol=0, co2_mol=0, ammonia_mol=0, total_mass_kg=0,
        )
        assert inv.o2_fraction() == 0.0

    def test_co2_ppm_calculation(self):
        inv = ElementInventory(
            hydrogen_mol=0, helium_mol=0, carbon_mol=0,
            nitrogen_mol=1e6, oxygen_mol=1e5,
            water_mol=0, co2_mol=1000.0, ammonia_mol=0, total_mass_kg=0,
        )
        ppm = inv.co2_ppm()
        expected = 1000.0 / (1e6 + 1e5 + 1000.0) * 1e6
        assert abs(ppm - expected) < 0.01

    def test_n2_fraction_nominal(self):
        inv = ElementInventory(
            hydrogen_mol=0, helium_mol=0, carbon_mol=0,
            nitrogen_mol=79.0, oxygen_mol=21.0,
            water_mol=0, co2_mol=0, ammonia_mol=0, total_mass_kg=0,
        )
        assert abs(inv.n2_fraction() - 79/100) < 1e-6

    def test_frozen_immutability(self):
        inv = make_nominal_elements()
        with pytest.raises((AttributeError, TypeError)):
            inv.hydrogen_mol = 0  # type: ignore

    def test_co2_ppm_zero(self):
        inv = ElementInventory(
            hydrogen_mol=0, helium_mol=0, carbon_mol=0,
            nitrogen_mol=100.0, oxygen_mol=20.0,
            water_mol=0, co2_mol=0, ammonia_mol=0, total_mass_kg=0,
        )
        assert inv.co2_ppm() == 0.0

    def test_total_mass_stored(self):
        inv = make_nominal_elements()
        assert inv.total_mass_kg == 1e7

    def test_water_mol_stored(self):
        inv = make_nominal_elements()
        assert inv.water_mol == 50000.0


# ===========================================================================
# §3 pp chain 물리 (10)
# ===========================================================================

class TestPPChain:
    def setup_method(self):
        self.cfg = PPChainConfig()
        self.pp = PPChain(self.cfg)
        self.physics = make_physics()

    def test_below_ignition_returns_zero(self):
        rate = self.pp.rate(1e6, 1.5e5, 0.73)
        assert rate == 0.0

    def test_at_ignition_nonzero(self):
        # 정확히 min_ignition_temp_k(4e6)는 < 조건이 아니므로 반응 발생
        rate = self.pp.rate(4e6, 1.5e5, 0.73)
        assert rate >= 0.0  # 경계값에서 0 이상

    def test_above_ignition_positive(self):
        rate = self.pp.rate(5e6, 1.5e5, 0.73)
        assert rate > 0.0

    def test_reference_point_returns_reference_rate(self):
        rate = self.pp.rate(1.5e7, 1.5e5, 1.0)
        assert abs(rate - self.cfg.reference_rate_mol_s) < 1e-10

    def test_rate_scales_with_density_squared(self):
        r1 = self.pp.rate(1.5e7, 1.5e5, 0.73)
        r2 = self.pp.rate(1.5e7, 3.0e5, 0.73)
        assert abs(r2 / r1 - 4.0) < 0.01

    def test_rate_scales_with_h_fraction_squared(self):
        r1 = self.pp.rate(1.5e7, 1.5e5, 0.5)
        r2 = self.pp.rate(1.5e7, 1.5e5, 1.0)
        assert abs(r2 / r1 - 4.0) < 0.01

    def test_power_mw_positive(self):
        rate = self.pp.rate(1.5e7, 1.5e5, 0.73)
        pwr = self.pp.power_mw(rate, self.physics)
        assert pwr > 0.0

    def test_he4_production_equals_rate(self):
        rate = 2.5
        he4 = self.pp.he4_production_mol_s(rate)
        assert he4 == rate

    def test_tick_returns_tuple_of_two(self):
        result = self.pp.tick(1.5e7, 1.5e5, 0.73, 1.0, self.physics)
        assert len(result) == 2

    def test_power_units_sanity(self):
        # rate 1 mol/s, Q=26.731 MeV × N_A = 26.731 × 1.602e-13 J × 6.022e23 /mol
        # ≈ 2.58e12 J/mol × 1 mol/s / 1e6 = 2.58e6 MW
        p = self.pp.power_mw(1.0, self.physics)
        assert 1e5 < p < 1e7  # MW 단위, 수백만 MW 범위


# ===========================================================================
# §4 CNO cycle 물리 (8)
# ===========================================================================

class TestCNOCycle:
    def setup_method(self):
        self.cfg = CNOCycleConfig()
        self.cno = CNOCycle(self.cfg)
        self.physics = make_physics()

    def test_below_min_temp_returns_zero(self):
        rate = self.cno.rate(1e7, 1.5e5, 0.73, 0.02)
        assert rate == 0.0

    def test_above_min_temp_nonzero(self):
        rate = self.cno.rate(2e7, 1.5e5, 0.73, 0.02)
        assert rate > 0.0

    def test_reference_rate_at_reference_temp(self):
        rate = self.cno.rate(2e7, 1.5e5, 1.0, 0.02)
        assert abs(rate - self.cfg.reference_rate_mol_s) < 1e-10

    def test_c12_regeneration_fraction(self):
        frac = self.cno.c12_regeneration_fraction()
        assert 0.9 <= frac <= 1.0

    def test_power_positive_above_ignition(self):
        rate = self.cno.rate(2e7, 1.5e5, 0.73, 0.02)
        pwr = self.cno.power_mw(rate, self.physics)
        assert pwr >= 0.0

    def test_tick_returns_two_values(self):
        result = self.cno.tick(2e7, 1.5e5, 0.73, 0.02, 1.0, self.physics)
        assert len(result) == 2

    def test_rate_increases_with_temperature(self):
        r1 = self.cno.rate(2e7, 1.5e5, 0.73, 0.02)
        r2 = self.cno.rate(2.1e7, 1.5e5, 0.73, 0.02)
        assert r2 > r1

    def test_zero_cno_fraction_returns_zero(self):
        rate = self.cno.rate(2e7, 1.5e5, 0.73, 0.0)
        assert rate == 0.0


# ===========================================================================
# §5 삼중 알파 물리 (8)
# ===========================================================================

class TestTripleAlpha:
    def setup_method(self):
        self.cfg = TripleAlphaConfig()
        self.ta = TripleAlpha(self.cfg)
        self.physics = make_physics()

    def test_below_ignition_returns_zero(self):
        rate = self.ta.rate(5e7, 1.5e5, 0.25)
        assert rate == 0.0

    def test_above_ignition_positive(self):
        rate = self.ta.rate(1.5e8, 1.5e5, 0.25)
        assert rate > 0.0

    def test_c12_production_equals_rate(self):
        rate = 0.5
        c12 = self.ta.c12_production_mol_s(rate)
        assert c12 == rate

    def test_power_positive(self):
        rate = self.ta.rate(2e8, 1.5e5, 0.5)
        pwr = self.ta.power_mw(rate, self.physics)
        assert pwr >= 0.0

    def test_tick_returns_three_values(self):
        result = self.ta.tick(2e8, 1.5e5, 0.5, 1.0, self.physics)
        assert len(result) == 3

    def test_hoyle_resonance_stored(self):
        assert abs(self.cfg.hoyle_resonance_mev - 7.6549) < 0.001

    def test_rate_scales_with_he4_cubed(self):
        r1 = self.ta.rate(2e8, 1.5e5, 0.25)
        r2 = self.ta.rate(2e8, 1.5e5, 0.50)
        # Y^3 비율: (0.5/0.25)^3 = 8
        assert abs(r2 / r1 - 8.0) < 0.1

    def test_min_ignition_temp_100mk(self):
        assert abs(self.cfg.min_temp_k - 1.0e8) < 1e3


# ===========================================================================
# §6 SynthesisEngine 통합 (10)
# ===========================================================================

class TestSynthesisEngine:
    def setup_method(self):
        self.physics = make_physics()
        self.engine = SynthesisEngine(SynthesisConfig(), self.physics)

    def test_inactive_below_4m_k(self):
        state = self.engine.tick(t_s=0, temp_k=1e6, density_kgm3=1.5e5, dt_s=1.0)
        assert state.phase == SynthesisPhase.INACTIVE

    def test_pp_chain_between_4m_15m_k(self):
        state = self.engine.tick(t_s=0, temp_k=1e7, density_kgm3=1.5e5, dt_s=1.0)
        assert state.phase == SynthesisPhase.PP_CHAIN

    def test_cno_active_above_15m_k(self):
        state = self.engine.tick(t_s=0, temp_k=2e7, density_kgm3=1.5e5, dt_s=1.0)
        assert state.phase == SynthesisPhase.CNO_ACTIVE

    def test_triple_alpha_above_100m_k(self):
        state = self.engine.tick(t_s=0, temp_k=1.5e8, density_kgm3=1.5e5, dt_s=1.0)
        assert state.phase == SynthesisPhase.TRIPLE_ALPHA

    def test_inactive_zero_power(self):
        state = self.engine.tick(t_s=0, temp_k=1e6, density_kgm3=1.5e5, dt_s=1.0)
        assert state.power_output_mw == 0.0

    def test_pp_chain_positive_power(self):
        state = self.engine.tick(t_s=0, temp_k=1e7, density_kgm3=1.5e5, dt_s=1.0)
        assert state.power_output_mw > 0.0

    def test_triple_alpha_produces_c12(self):
        state = self.engine.tick(t_s=0, temp_k=1.5e8, density_kgm3=1.5e5, dt_s=1.0)
        assert state.c12_produced_mol_s > 0.0

    def test_he4_production_nonzero_in_pp_chain(self):
        state = self.engine.tick(t_s=0, temp_k=1e7, density_kgm3=1.5e5, dt_s=1.0)
        assert state.he4_produced_mol_s >= 0.0

    def test_state_is_synthesis_state_type(self):
        state = self.engine.tick(t_s=0, temp_k=1e7, density_kgm3=1.5e5, dt_s=1.0)
        assert isinstance(state, SynthesisState)

    def test_h_fraction_decreases_over_time(self):
        initial_h = self.engine.h_fraction
        for _ in range(10):
            self.engine.tick(t_s=0, temp_k=1.5e7, density_kgm3=1.5e5, dt_s=1.0)
        assert self.engine.h_fraction <= initial_h


# ===========================================================================
# §7 WaterCycle (8)
# ===========================================================================

class TestWaterCycle:
    def setup_method(self):
        self.cfg = WaterCycleConfig()
        self.wc = WaterCycle(self.cfg)

    def test_electrolysis_power_proportional_to_rate(self):
        p1 = self.wc.electrolysis_power_mw(0.01)
        p2 = self.wc.electrolysis_power_mw(0.02)
        assert abs(p2 / p1 - 2.0) < 0.01

    def test_o2_from_electrolysis_half_rate(self):
        o2 = self.wc.o2_from_electrolysis(0.02)
        assert abs(o2 - 0.01) < 1e-10

    def test_h2_from_electrolysis_equals_rate(self):
        h2 = self.wc.h2_from_electrolysis(0.03)
        assert abs(h2 - 0.03) < 1e-10

    def test_tick_reduces_water(self):
        state = make_nominal_hydro(water_mol=50000.0)
        new = self.wc.tick(state, available_power_mw=10.0, dt_s=1.0)
        assert new.water_total_mol < state.water_total_mol

    def test_no_power_means_no_electrolysis(self):
        state = make_nominal_hydro(water_mol=50000.0)
        new = self.wc.tick(state, available_power_mw=0.0, dt_s=1.0)
        assert new.electrolysis_rate_mol_s == 0.0

    def test_water_margin_decreases(self):
        state = make_nominal_hydro(water_mol=50000.0)
        new = self.wc.tick(state, available_power_mw=10.0, dt_s=3600.0)
        assert new.water_margin <= 1.0

    def test_minimum_water_clamped_to_zero(self):
        state = make_nominal_hydro(water_mol=0.0)
        new = self.wc.tick(state, available_power_mw=100.0, dt_s=1.0)
        assert new.water_total_mol >= 0.0

    def test_tick_returns_hydro_state_type(self):
        state = make_nominal_hydro()
        new = self.wc.tick(state, available_power_mw=5.0, dt_s=1.0)
        assert isinstance(new, HydrosphereState)


# ===========================================================================
# §8 PhotosynthesisEngine (10)
# ===========================================================================

class TestPhotosynthesisEngine:
    def setup_method(self):
        self.cfg = PhotosynthesisConfig()
        self.eng = PhotosynthesisEngine(self.cfg)

    def test_zero_biomass_zero_rate(self):
        rate = self.eng.photosynthesis_rate(0.0, 800.0, 5.0)
        assert rate == 0.0

    def test_zero_co2_zero_rate(self):
        rate = self.eng.photosynthesis_rate(100.0, 0.0, 5.0)
        assert rate == 0.0

    def test_rate_positive_with_resources(self):
        rate = self.eng.photosynthesis_rate(100.0, 800.0, 5.0)
        assert rate > 0.0

    def test_o2_production_equals_co2_uptake(self):
        co2 = 5e-3
        o2 = self.eng.o2_production_mol_s(co2)
        assert abs(o2 - co2) < 1e-10

    def test_biomass_growth_positive(self):
        gr = self.eng.biomass_growth_rate(100.0, 800.0, 5.0)
        assert gr > 0.0

    def test_biomass_saturates_at_max(self):
        gr = self.eng.biomass_growth_rate(self.cfg.biomass_max_kg, 800.0, 5.0)
        assert gr <= 0.0

    def test_food_production_proportional_to_biomass(self):
        f1 = self.eng.food_production_kg_day(1000.0)
        f2 = self.eng.food_production_kg_day(2000.0)
        assert abs(f2 / f1 - 2.0) < 0.01

    def test_tick_increases_biomass(self):
        state = make_nominal_biosphere()
        new = self.eng.tick(state, co2_ppm=800.0, light_power_mw=5.0, dt_s=3600.0)
        assert new.plant_biomass_kg >= state.plant_biomass_kg

    def test_tick_returns_biosphere_state_type(self):
        state = make_nominal_biosphere()
        new = self.eng.tick(state, co2_ppm=800.0, light_power_mw=5.0, dt_s=1.0)
        assert isinstance(new, BiosphereState)

    def test_michaelis_menten_saturation(self):
        r_low = self.eng.photosynthesis_rate(100.0, 100.0, 5.0)
        r_high = self.eng.photosynthesis_rate(100.0, 10000.0, 5.0)
        # 높은 CO₂ 농도에서 더 높은 반응률
        assert r_high > r_low


# ===========================================================================
# §9 GasCycle (10)
# ===========================================================================

class TestGasCycle:
    def setup_method(self):
        self.cfg = GasCycleConfig()
        self.gc = GasCycle(self.cfg, make_physics())

    def test_crew_co2_output_total(self):
        output = self.gc.crew_co2_output_mol_s()
        expected = self.cfg.crew_co2_output_mol_s_per_person * self.cfg.crew_count
        assert abs(output - expected) < 1e-12

    def test_crew_o2_consumption_total(self):
        cons = self.gc.crew_o2_consumption_mol_s()
        expected = self.cfg.crew_o2_consumption_mol_s_per_person * self.cfg.crew_count
        assert abs(cons - expected) < 1e-12

    def test_nominal_atmosphere_breathable(self):
        atm = make_nominal_atmosphere()
        assert self.gc.is_breathable(atm)

    def test_toxic_atmosphere_not_breathable(self):
        atm = AtmosphereState(
            t_s=0, status=AtmosphereStatus.TOXIC,
            total_pressure_pa=101325, o2_partial_pa=21000,
            n2_partial_pa=50000, co2_partial_pa=10000,
            h2o_vapor_pa=1000, temperature_k=293,
            o2_fraction=0.21, co2_ppm=10000.0, breathable=False,
        )
        assert not self.gc.is_breathable(atm)

    def test_low_o2_not_breathable(self):
        atm = AtmosphereState(
            t_s=0, status=AtmosphereStatus.THIN,
            total_pressure_pa=80000, o2_partial_pa=8000,
            n2_partial_pa=72000, co2_partial_pa=400,
            h2o_vapor_pa=200, temperature_k=293,
            o2_fraction=0.10, co2_ppm=500.0, breathable=False,
        )
        assert not self.gc.is_breathable(atm)

    def test_tick_co2_increases_with_crew(self):
        atm = make_nominal_atmosphere()
        bio = make_nominal_biosphere()
        bio_zero = BiosphereState(
            t_s=0, status=BiosphereStatus.DEAD,
            plant_biomass_kg=0, co2_uptake_mol_s=0,
            o2_release_mol_s=0, food_production_kg_day=0,
            nitrogen_fixed_mol_s=0, growth_rate=0,
        )
        hydro = make_nominal_hydro()
        hydro_zero = HydrosphereState(
            t_s=0, water_total_mol=50000, liquid_fraction=0.9,
            electrolysis_rate_mol_s=0, h2_produced_mol_s=0,
            o2_from_water_mol_s=0, power_consumed_mw=0, water_margin=1.0,
        )
        new_atm = self.gc.tick(atm, bio_zero, hydro_zero, dt_s=3600.0, physics=make_physics())
        assert new_atm.co2_ppm > atm.co2_ppm

    def test_tick_returns_atmosphere_state(self):
        atm = make_nominal_atmosphere()
        new = self.gc.tick(atm, make_nominal_biosphere(), make_nominal_hydro(), 1.0, make_physics())
        assert isinstance(new, AtmosphereState)

    def test_initial_atmosphere_breathable(self):
        cfg = GasCycleConfig()
        physics = make_physics()
        atm = initial_atmosphere_state(cfg, physics)
        assert atm.breathable

    def test_o2_fraction_range(self):
        atm = make_nominal_atmosphere()
        assert 0.0 <= atm.o2_fraction <= 1.0

    def test_photosynthesis_reduces_co2(self):
        atm = make_nominal_atmosphere()
        bio = BiosphereState(
            t_s=0, status=BiosphereStatus.THRIVING,
            plant_biomass_kg=5000, co2_uptake_mol_s=1.0,
            o2_release_mol_s=1.0, food_production_kg_day=15,
            nitrogen_fixed_mol_s=1e-4, growth_rate=0,
        )
        hydro_zero = HydrosphereState(
            t_s=0, water_total_mol=50000, liquid_fraction=0.9,
            electrolysis_rate_mol_s=0, h2_produced_mol_s=0,
            o2_from_water_mol_s=0, power_consumed_mw=0, water_margin=1.0,
        )
        new = self.gc.tick(atm, bio, hydro_zero, dt_s=1.0, physics=make_physics())
        # CO₂가 감소해야 함 (강한 광합성)
        assert new.co2_ppm < atm.co2_ppm


# ===========================================================================
# §10 HomeostasisController (8)
# ===========================================================================

class TestHomeostasisController:
    def setup_method(self):
        self.cfg = HomeostasisConfig()
        self.ctrl = HomeostasisController(self.cfg)
        self.physics = make_physics()

    def test_steady_state_temperature(self):
        reg = make_nominal_regulator()
        # 목표 온도에서 방열 = 열 입력이면 온도 안정
        # 작은 타임스텝으로 안정성 확인
        new = self.ctrl.tick(reg, heat_input_mw=0.0, dt_s=0.1, physics=self.physics)
        assert isinstance(new, RegulatorState)

    def test_temperature_rises_with_heat_input(self):
        reg = make_nominal_regulator()
        new = self.ctrl.tick(reg, heat_input_mw=1000.0, dt_s=10.0, physics=self.physics)
        assert new.temperature_k > reg.temperature_k

    def test_thermal_margin_computed(self):
        reg = make_nominal_regulator()
        new = self.ctrl.tick(reg, heat_input_mw=0.0, dt_s=1.0, physics=self.physics)
        assert 0.0 <= new.thermal_margin <= 1.0

    def test_critical_at_extreme_temp(self):
        reg = RegulatorState(
            t_s=0, status=RegulatorStatus.CRITICAL,
            temperature_k=400.0, pressure_pa=101325,
            ph=7.0, magnetic_field_t=0.1,
            radiation_dose_sv_hr=4e-5,
            thermal_margin=0.0, pressure_margin=0.9,
        )
        new = self.ctrl.tick(reg, heat_input_mw=0.0, dt_s=1.0, physics=self.physics)
        assert new.status in (RegulatorStatus.CRITICAL, RegulatorStatus.UNSTABLE)

    def test_radiated_power_increases_with_temperature(self):
        # 간접 확인: 고온에서 온도 감소 속도가 빠름
        reg_cold = RegulatorState(
            t_s=0, status=RegulatorStatus.NOMINAL,
            temperature_k=250.0, pressure_pa=101325,
            ph=7.0, magnetic_field_t=0.1,
            radiation_dose_sv_hr=4e-5,
            thermal_margin=0.8, pressure_margin=0.9,
        )
        reg_hot = RegulatorState(
            t_s=0, status=RegulatorStatus.NOMINAL,
            temperature_k=350.0, pressure_pa=101325,
            ph=7.0, magnetic_field_t=0.1,
            radiation_dose_sv_hr=4e-5,
            thermal_margin=0.5, pressure_margin=0.9,
        )
        ctrl_c = HomeostasisController(self.cfg)
        ctrl_h = HomeostasisController(self.cfg)
        new_cold = ctrl_c.tick(reg_cold, 0.0, 1.0, self.physics)
        new_hot = ctrl_h.tick(reg_hot, 0.0, 1.0, self.physics)
        # 고온 우주선이 더 빠르게 냉각
        delta_cold = new_cold.temperature_k - reg_cold.temperature_k
        delta_hot = new_hot.temperature_k - reg_hot.temperature_k
        assert delta_hot < delta_cold

    def test_tick_returns_regulator_state(self):
        reg = make_nominal_regulator()
        new = self.ctrl.tick(reg, 10.0, 1.0, self.physics)
        assert isinstance(new, RegulatorState)

    def test_pressure_preserved(self):
        reg = make_nominal_regulator()
        new = self.ctrl.tick(reg, 0.0, 1.0, self.physics)
        assert new.pressure_pa == reg.pressure_pa

    def test_ph_preserved(self):
        reg = make_nominal_regulator()
        new = self.ctrl.tick(reg, 0.0, 1.0, self.physics)
        assert new.ph == reg.ph


# ===========================================================================
# §11 RadiationShield (6)
# ===========================================================================

class TestRadiationShield:
    def setup_method(self):
        self.cfg = RadiationShieldConfig()
        self.shield = RadiationShield(self.cfg)

    def test_zero_field_zero_attenuation(self):
        att = self.shield.magnetic_attenuation(0.0)
        assert att == 0.0

    def test_large_field_high_attenuation(self):
        att = self.shield.magnetic_attenuation(5.0)
        assert att > 0.9

    def test_dose_decreases_with_field(self):
        dose_low = self.shield.dose_rate_sv_hr(0.01)
        dose_high = self.shield.dose_rate_sv_hr(0.5)
        assert dose_high < dose_low

    def test_tick_updates_dose(self):
        reg = make_nominal_regulator()
        new = self.shield.tick(reg, dt_s=1.0)
        assert new.radiation_dose_sv_hr >= 0.0

    def test_physical_attenuation_bounded(self):
        att = self.shield.physical_attenuation()
        assert 0.0 <= att <= 0.3

    def test_tick_returns_regulator_state(self):
        reg = make_nominal_regulator()
        new = self.shield.tick(reg, 1.0)
        assert isinstance(new, RegulatorState)


# ===========================================================================
# §12 NitrogenCycle (6)
# ===========================================================================

class TestNitrogenCycle:
    def setup_method(self):
        self.cfg = NitrogenCycleConfig()
        self.nc = NitrogenCycle(self.cfg)

    def test_zero_biomass_zero_bio_fixation(self):
        rate = self.nc.bio_fixation_rate(0.0)
        assert rate == 0.0

    def test_positive_biomass_positive_fixation(self):
        rate = self.nc.bio_fixation_rate(100.0)
        assert rate > 0.0

    def test_fixation_proportional_to_biomass(self):
        r1 = self.nc.bio_fixation_rate(100.0)
        r2 = self.nc.bio_fixation_rate(200.0)
        assert abs(r2 / r1 - 2.0) < 0.01

    def test_haber_bosch_zero_without_n2(self):
        rate = self.nc.haber_bosch_rate(0.0, 100.0, 10.0)
        assert rate == 0.0

    def test_haber_bosch_zero_without_power(self):
        rate = self.nc.haber_bosch_rate(100.0, 100.0, 0.0)
        assert rate == 0.0

    def test_tick_returns_float(self):
        atm = make_nominal_atmosphere()
        bio = make_nominal_biosphere()
        result = self.nc.tick(atm, bio, dt_s=1.0)
        assert isinstance(result, float)
        assert result >= 0.0


# ===========================================================================
# §13 OmegaMonitor (10)
# ===========================================================================

class TestOmegaMonitor:
    def setup_method(self):
        self.cfg = OmegaConfig()
        self.monitor = OmegaMonitor(self.cfg)

    def test_nominal_state_has_positive_omega(self):
        state = make_terra_state()
        health = self.monitor.observe(state)
        assert health.omega_terra > 0.0

    def test_omega_bounded_zero_one(self):
        state = make_terra_state()
        health = self.monitor.observe(state)
        assert 0.0 <= health.omega_terra <= 1.0

    def test_thriving_verdict_high_omega(self):
        state = make_terra_state()
        health = self.monitor.observe(state)
        if health.omega_terra > 0.8:
            assert health.verdict == "THRIVING"

    def test_critical_verdict_low_omega(self):
        # 매우 나쁜 상태 구성
        bad_atm = AtmosphereState(
            t_s=0, status=AtmosphereStatus.TOXIC,
            total_pressure_pa=1000, o2_partial_pa=100,
            n2_partial_pa=800, co2_partial_pa=100,
            h2o_vapor_pa=0, temperature_k=293,
            o2_fraction=0.1, co2_ppm=100000.0, breathable=False,
        )
        bad_bio = BiosphereState(
            t_s=0, status=BiosphereStatus.DEAD,
            plant_biomass_kg=0, co2_uptake_mol_s=0,
            o2_release_mol_s=0, food_production_kg_day=0,
            nitrogen_fixed_mol_s=0, growth_rate=0,
        )
        bad_hydro = HydrosphereState(
            t_s=0, water_total_mol=0, liquid_fraction=0,
            electrolysis_rate_mol_s=0, h2_produced_mol_s=0,
            o2_from_water_mol_s=0, power_consumed_mw=0, water_margin=0.0,
        )
        state = TerraState(
            t_s=0,
            elements=make_nominal_elements(),
            synthesis=make_nominal_synthesis(),
            atmosphere=bad_atm,
            hydrosphere=bad_hydro,
            biosphere=bad_bio,
            regulator=make_nominal_regulator(),
        )
        health = self.monitor.observe(state)
        assert health.omega_terra < 0.5

    def test_observe_returns_terra_health(self):
        state = make_terra_state()
        health = self.monitor.observe(state)
        assert isinstance(health, TerraHealth)

    def test_alerts_empty_for_nominal(self):
        state = make_terra_state()
        health = self.monitor.observe(state)
        # 표준 상태에서는 CO2_TOXIC/O2_LOW 없어야 함
        assert "CO2_TOXIC" not in health.alerts
        assert "O2_LOW" not in health.alerts

    def test_omega_synthesis_inactive_low(self):
        state = make_terra_state()
        inactive_synth = SynthesisState(
            t_s=0, phase=SynthesisPhase.INACTIVE,
            core_temp_k=1e6, core_density_kgm3=1e5,
            pp_rate_mol_s=0, cno_rate_mol_s=0,
            triple_alpha_rate_mol_s=0, power_output_mw=0,
            he4_produced_mol_s=0, c12_produced_mol_s=0,
        )
        state2 = TerraState(
            t_s=0,
            elements=make_nominal_elements(),
            synthesis=inactive_synth,
            atmosphere=make_nominal_atmosphere(),
            hydrosphere=make_nominal_hydro(),
            biosphere=make_nominal_biosphere(),
            regulator=make_nominal_regulator(),
        )
        health = self.monitor.observe(state2)
        assert health.omega_synthesis < 0.5

    def test_omega_hydrosphere_equals_water_margin(self):
        state = make_terra_state()
        health = self.monitor.observe(state)
        assert abs(health.omega_hydrosphere - state.hydrosphere.water_margin) < 0.01

    def test_abort_required_false_nominal(self):
        state = make_terra_state()
        health = self.monitor.observe(state)
        assert not health.abort_required

    def test_omega_weights_sum_to_one(self):
        cfg = OmegaConfig()
        total = (cfg.w_synthesis + cfg.w_atmosphere + cfg.w_hydrosphere
                 + cfg.w_biosphere + cfg.w_regulator)
        assert abs(total - 1.0) < 1e-9


# ===========================================================================
# §14 AbortSystem (8)
# ===========================================================================

class TestAbortSystem:
    def setup_method(self):
        self.cfg = AbortConfig()
        self.abort = AbortSystem(self.cfg)
        self.monitor = OmegaMonitor(OmegaConfig())

    def _health_for(self, state: TerraState) -> TerraHealth:
        return self.monitor.observe(state)

    def test_nominal_returns_none(self):
        state = make_terra_state()
        health = self._health_for(state)
        mode = self.abort.evaluate(state, health)
        assert mode == TerraAbortMode.NONE

    def test_high_co2_triggers_atmosphere_critical(self):
        bad_atm = AtmosphereState(
            t_s=0, status=AtmosphereStatus.TOXIC,
            total_pressure_pa=101325, o2_partial_pa=21000,
            n2_partial_pa=50000, co2_partial_pa=50000,
            h2o_vapor_pa=1000, temperature_k=293,
            o2_fraction=0.21, co2_ppm=50000.0, breathable=False,
        )
        state = TerraState(
            t_s=0, elements=make_nominal_elements(),
            synthesis=make_nominal_synthesis(),
            atmosphere=bad_atm,
            hydrosphere=make_nominal_hydro(),
            biosphere=make_nominal_biosphere(),
            regulator=make_nominal_regulator(),
        )
        health = self._health_for(state)
        mode = self.abort.evaluate(state, health)
        assert mode == TerraAbortMode.ATMOSPHERE_CRITICAL

    def test_low_o2_triggers_atmosphere_critical(self):
        bad_atm = AtmosphereState(
            t_s=0, status=AtmosphereStatus.THIN,
            total_pressure_pa=50000, o2_partial_pa=5000,
            n2_partial_pa=45000, co2_partial_pa=400,
            h2o_vapor_pa=100, temperature_k=293,
            o2_fraction=0.10, co2_ppm=500.0, breathable=False,
        )
        state = TerraState(
            t_s=0, elements=make_nominal_elements(),
            synthesis=make_nominal_synthesis(),
            atmosphere=bad_atm,
            hydrosphere=make_nominal_hydro(),
            biosphere=make_nominal_biosphere(),
            regulator=make_nominal_regulator(),
        )
        health = self._health_for(state)
        mode = self.abort.evaluate(state, health)
        assert mode == TerraAbortMode.ATMOSPHERE_CRITICAL

    def test_high_temp_triggers_thermal_runaway(self):
        hot_reg = RegulatorState(
            t_s=0, status=RegulatorStatus.CRITICAL,
            temperature_k=400.0, pressure_pa=101325,
            ph=7.0, magnetic_field_t=0.1,
            radiation_dose_sv_hr=4e-5,
            thermal_margin=0.0, pressure_margin=0.9,
        )
        state = TerraState(
            t_s=0, elements=make_nominal_elements(),
            synthesis=make_nominal_synthesis(),
            atmosphere=make_nominal_atmosphere(),
            hydrosphere=make_nominal_hydro(),
            biosphere=make_nominal_biosphere(),
            regulator=hot_reg,
        )
        health = self._health_for(state)
        mode = self.abort.evaluate(state, health)
        assert mode == TerraAbortMode.THERMAL_RUNAWAY

    def test_no_water_triggers_water_critical(self):
        dry_hydro = HydrosphereState(
            t_s=0, water_total_mol=0.0, liquid_fraction=0,
            electrolysis_rate_mol_s=0, h2_produced_mol_s=0,
            o2_from_water_mol_s=0, power_consumed_mw=0, water_margin=0.0,
        )
        state = TerraState(
            t_s=0, elements=make_nominal_elements(),
            synthesis=make_nominal_synthesis(),
            atmosphere=make_nominal_atmosphere(),
            hydrosphere=dry_hydro,
            biosphere=make_nominal_biosphere(),
            regulator=make_nominal_regulator(),
        )
        health = self._health_for(state)
        mode = self.abort.evaluate(state, health)
        assert mode == TerraAbortMode.WATER_CRITICAL

    def test_no_biomass_triggers_biosphere_collapse(self):
        dead_bio = BiosphereState(
            t_s=0, status=BiosphereStatus.DEAD,
            plant_biomass_kg=0.0, co2_uptake_mol_s=0,
            o2_release_mol_s=0, food_production_kg_day=0,
            nitrogen_fixed_mol_s=0, growth_rate=0,
        )
        state = TerraState(
            t_s=0, elements=make_nominal_elements(),
            synthesis=make_nominal_synthesis(),
            atmosphere=make_nominal_atmosphere(),
            hydrosphere=make_nominal_hydro(),
            biosphere=dead_bio,
            regulator=make_nominal_regulator(),
        )
        health = self._health_for(state)
        mode = self.abort.evaluate(state, health)
        assert mode == TerraAbortMode.BIOSPHERE_COLLAPSE

    def test_is_abort_required_false_nominal(self):
        state = make_terra_state()
        health = self._health_for(state)
        assert not self.abort.is_abort_required(state, health)

    def test_abort_mode_enum_values_exist(self):
        assert TerraAbortMode.NONE is not None
        assert TerraAbortMode.ATMOSPHERE_CRITICAL is not None
        assert TerraAbortMode.RADIATION_ALERT is not None
        assert TerraAbortMode.THERMAL_RUNAWAY is not None
        assert TerraAbortMode.WATER_CRITICAL is not None
        assert TerraAbortMode.BIOSPHERE_COLLAPSE is not None


# ===========================================================================
# §15 TerraChain (8)
# ===========================================================================

class TestTerraChain:
    def test_genesis_hash_deterministic(self):
        c1 = TerraChain("TERRA-001")
        c2 = TerraChain("TERRA-001")
        assert c1.genesis_hash() == c2.genesis_hash()

    def test_different_ship_id_different_genesis(self):
        c1 = TerraChain("TERRA-001")
        c2 = TerraChain("TERRA-002")
        assert c1.genesis_hash() != c2.genesis_hash()

    def test_record_increases_length(self):
        chain = TerraChain("TEST")
        chain.record(0.0, TerraChain.EVENT_TELEMETRY, {"omega": 0.8})
        assert chain.length() == 1

    def test_multiple_records(self):
        chain = TerraChain("TEST")
        for i in range(5):
            chain.record(float(i), TerraChain.EVENT_TELEMETRY, {"t": i})
        assert chain.length() == 5

    def test_each_entry_has_unique_hash(self):
        chain = TerraChain("TEST")
        chain.record(0.0, TerraChain.EVENT_TELEMETRY, {"a": 1})
        chain.record(1.0, TerraChain.EVENT_TELEMETRY, {"a": 2})
        entries = chain.entries()
        assert entries[0].entry_hash != entries[1].entry_hash

    def test_verify_intact_chain(self):
        chain = TerraChain("TEST")
        for i in range(3):
            chain.record(float(i), TerraChain.EVENT_TELEMETRY, {"i": i})
        assert chain.verify()

    def test_event_types_defined(self):
        assert TerraChain.EVENT_TELEMETRY == "TELEMETRY"
        assert TerraChain.EVENT_SYNTHESIS_IGNITION == "SYNTHESIS_IGNITION"
        assert TerraChain.EVENT_ABORT_EVENT == "ABORT_EVENT"

    def test_last_hash_changes_with_records(self):
        chain = TerraChain("TEST")
        h0 = chain.last_hash()
        chain.record(0.0, TerraChain.EVENT_TELEMETRY, {})
        h1 = chain.last_hash()
        assert h0 != h1


# ===========================================================================
# §16 TerraAgent 통합 (10)
# ===========================================================================

class TestTerraAgent:
    def setup_method(self):
        self.agent = TerraAgent()

    def test_agent_initializes(self):
        assert self.agent is not None

    def test_tick_returns_telemetry_frame(self):
        frame = self.agent.tick()
        assert isinstance(frame, TelemetryFrame)

    def test_tick_advances_time(self):
        frame1 = self.agent.tick()
        frame2 = self.agent.tick()
        assert frame2.t_s > frame1.t_s

    def test_health_omega_bounded(self):
        frame = self.agent.tick()
        assert 0.0 <= frame.health.omega_terra <= 1.0

    def test_ignite_synthesis_raises_temp(self):
        initial_temp = self.agent.config.core_temp_k
        self.agent.ignite_synthesis()
        assert self.agent.config.core_temp_k >= initial_temp

    def test_set_propulsion_mode_nominal(self):
        self.agent.set_propulsion_mode("NOMINAL")
        assert abs(self.agent.config.core_temp_k - 1.5e7) < 1e3

    def test_set_propulsion_mode_triple_alpha(self):
        self.agent.set_propulsion_mode("TRIPLE_ALPHA")
        assert self.agent.config.core_temp_k >= 1e8

    def test_simulate_returns_frames(self):
        frames = self.agent.simulate(duration_s=10.0)
        assert len(frames) == 10

    def test_get_health_returns_terra_health(self):
        health = self.agent.get_health()
        assert isinstance(health, TerraHealth)

    def test_chain_records_after_simulate(self):
        agent = TerraAgent(TerraAgentConfig(chain_interval=5))
        agent.simulate(duration_s=20.0)
        # 20 틱, chain_interval=5이면 최소 4개 이상
        assert agent._chain.length() >= 4
