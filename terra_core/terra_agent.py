"""
TerraAgent — TerraCore 전체 오케스트레이터

태양계 → 우주선 매핑:
  FusionCore      = 태양 (에너지 코어)
  SynthesisEngine = 핵합성 (H→He→C/O/N 원소 생성)
  AtmosphereEngine= 대기 순환 (CO₂↔O₂↔N₂)
  HydrosphereEngine = 수순환 (H₂O 전기분해·응결)
  BiosphereEngine = 생태계 (광합성·질소 고정)
  RegulatorEngine = 항상성 (온도·압력·pH·자기장)
  TerraAgent      = 전체 오케스트레이터

8단계 tick 파이프라인:
  Step 1: SynthesisEngine.tick → SynthesisState
  Step 2: WaterCycle.tick → HydrosphereState
  Step 3: PhotosynthesisEngine.tick → BiosphereState
  Step 4: NitrogenCycle.tick → 질소 고정
  Step 5: GasCycle.tick → AtmosphereState
  Step 6: HomeostasisController.tick → RegulatorState (온도·압력)
  Step 7: RadiationShield.tick → RegulatorState (방사선)
  Step 8: OmegaMonitor + AbortSystem + TerraChain
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import List, Optional

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
from terra_core.synthesis.synthesis_engine import SynthesisConfig, SynthesisEngine
from terra_core.synthesis.pp_chain import PPChainConfig
from terra_core.synthesis.cno_cycle import CNOCycleConfig
from terra_core.synthesis.triple_alpha import TripleAlphaConfig
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


@dataclass
class TerraAgentConfig:
    """TerraAgent 전체 설정."""

    ship_id: str = "TERRA-001"
    crew_count: int = 6
    dt_s: float = 1.0
    volume_m3: float = 1000.0

    # 서브시스템 config
    synthesis_config: SynthesisConfig = field(default_factory=SynthesisConfig)
    atmosphere_config: GasCycleConfig = field(default_factory=GasCycleConfig)
    hydro_config: WaterCycleConfig = field(default_factory=WaterCycleConfig)
    photo_config: PhotosynthesisConfig = field(default_factory=PhotosynthesisConfig)
    nitrogen_config: NitrogenCycleConfig = field(default_factory=NitrogenCycleConfig)
    homeostasis_config: HomeostasisConfig = field(default_factory=HomeostasisConfig)
    radiation_config: RadiationShieldConfig = field(default_factory=RadiationShieldConfig)
    omega_config: OmegaConfig = field(default_factory=OmegaConfig)
    abort_config: AbortConfig = field(default_factory=AbortConfig)
    physics: TerraPhysicsConfig = field(default_factory=TerraPhysicsConfig)

    # 체인 기록 주기 [tick]
    chain_interval: int = 10

    # 반응로 운전 파라미터
    core_temp_k: float = 1.5e7       # 초기 코어 온도 [K]
    core_density_kgm3: float = 1.5e5  # 초기 코어 밀도 [kg/m³]

    # 광원 전력 [MW]
    light_power_mw: float = 5.0

    # 초기 수분 재고 [mol]
    initial_water_mol: float = 50000.0


class TerraAgent:
    """TerraCore 전체 오케스트레이터.

    상태는 불변 데이터클래스의 궤적으로 표현된다.
    각 tick은 현재 상태를 관측하고 다음 상태로 전이한다.
    """

    def __init__(self, config: Optional[TerraAgentConfig] = None):
        self.config = config or TerraAgentConfig()
        cfg = self.config

        # 서브시스템 초기화
        self._synthesis = SynthesisEngine(cfg.synthesis_config, cfg.physics)
        self._gas_cycle = GasCycle(cfg.atmosphere_config, cfg.physics)
        self._water_cycle = WaterCycle(cfg.hydro_config)
        self._photosynthesis = PhotosynthesisEngine(cfg.photo_config)
        self._nitrogen = NitrogenCycle(cfg.nitrogen_config)
        self._homeostasis = HomeostasisController(cfg.homeostasis_config)
        self._radiation = RadiationShield(cfg.radiation_config)
        self._omega = OmegaMonitor(cfg.omega_config)
        self._abort = AbortSystem(cfg.abort_config)
        self._chain = TerraChain(cfg.ship_id)

        # 내부 시각 카운터
        self._t_s: float = 0.0
        self._tick_count: int = 0

        # 이전 synthesis 위상 추적 (이벤트 감지용)
        self._prev_phase = SynthesisPhase.INACTIVE

        # 초기 상태 구성
        self._state = self._build_initial_state()
        self._health = self._omega.observe(self._state)

    def _build_initial_state(self) -> TerraState:
        """초기 TerraState 구성."""
        cfg = self.config
        t = 0.0

        elements = ElementInventory(
            hydrogen_mol=1e6,
            helium_mol=2.5e5,
            carbon_mol=1e4,
            nitrogen_mol=5e5,
            oxygen_mol=3e5,
            water_mol=cfg.initial_water_mol,
            co2_mol=500.0,
            ammonia_mol=100.0,
            total_mass_kg=1e7,
        )

        synthesis = SynthesisState(
            t_s=t,
            phase=SynthesisPhase.INACTIVE,
            core_temp_k=cfg.core_temp_k,
            core_density_kgm3=cfg.core_density_kgm3,
            pp_rate_mol_s=0.0,
            cno_rate_mol_s=0.0,
            triple_alpha_rate_mol_s=0.0,
            power_output_mw=0.0,
            he4_produced_mol_s=0.0,
            c12_produced_mol_s=0.0,
        )

        atmosphere = initial_atmosphere_state(cfg.atmosphere_config, cfg.physics, t)

        hydrosphere = HydrosphereState(
            t_s=t,
            water_total_mol=cfg.initial_water_mol,
            liquid_fraction=0.9,
            electrolysis_rate_mol_s=0.0,
            h2_produced_mol_s=0.0,
            o2_from_water_mol_s=0.0,
            power_consumed_mw=0.0,
            water_margin=1.0,
        )

        biosphere = BiosphereState(
            t_s=t,
            status=BiosphereStatus.SEEDING,
            plant_biomass_kg=cfg.photo_config.initial_biomass_kg,
            co2_uptake_mol_s=0.0,
            o2_release_mol_s=0.0,
            food_production_kg_day=0.0,
            nitrogen_fixed_mol_s=0.0,
            growth_rate=0.0,
        )

        regulator = RegulatorState(
            t_s=t,
            status=RegulatorStatus.NOMINAL,
            temperature_k=cfg.homeostasis_config.target_temp_k,
            pressure_pa=cfg.homeostasis_config.target_pressure_pa,
            ph=cfg.homeostasis_config.target_ph,
            magnetic_field_t=cfg.radiation_config.magnetic_field_t,
            radiation_dose_sv_hr=self._radiation.dose_rate_sv_hr(
                cfg.radiation_config.magnetic_field_t
            ),
            thermal_margin=1.0,
            pressure_margin=1.0,
        )

        return TerraState(
            t_s=t,
            elements=elements,
            synthesis=synthesis,
            atmosphere=atmosphere,
            hydrosphere=hydrosphere,
            biosphere=biosphere,
            regulator=regulator,
        )

    def tick(self) -> TelemetryFrame:
        """8단계 파이프라인 단일 타임스텝 실행.

        Returns:
            TelemetryFrame — 현재 타임스텝 텔레메트리
        """
        cfg = self.config
        dt = cfg.dt_s
        state = self._state

        # Step 1: SynthesisEngine
        new_synthesis = self._synthesis.tick(
            t_s=self._t_s + dt,
            temp_k=cfg.core_temp_k,
            density_kgm3=cfg.core_density_kgm3,
            dt_s=dt,
        )

        # Step 2: WaterCycle
        available_power = new_synthesis.power_output_mw
        new_hydro = self._water_cycle.tick(
            state=state.hydrosphere,
            available_power_mw=available_power,
            dt_s=dt,
        )

        # Step 3: PhotosynthesisEngine
        co2_ppm = state.atmosphere.co2_ppm
        new_bio = self._photosynthesis.tick(
            state=state.biosphere,
            co2_ppm=co2_ppm,
            light_power_mw=cfg.light_power_mw,
            dt_s=dt,
        )

        # Step 4: NitrogenCycle
        n2_fixed = self._nitrogen.tick(
            atmosphere=state.atmosphere,
            bio=new_bio,
            dt_s=dt,
        )
        # N₂ 고정률 갱신
        new_bio = BiosphereState(
            t_s=new_bio.t_s,
            status=new_bio.status,
            plant_biomass_kg=new_bio.plant_biomass_kg,
            co2_uptake_mol_s=new_bio.co2_uptake_mol_s,
            o2_release_mol_s=new_bio.o2_release_mol_s,
            food_production_kg_day=new_bio.food_production_kg_day,
            nitrogen_fixed_mol_s=n2_fixed,
            growth_rate=new_bio.growth_rate,
        )

        # Step 5: GasCycle
        new_atm = self._gas_cycle.tick(
            state=state.atmosphere,
            bio=new_bio,
            hydro=new_hydro,
            dt_s=dt,
            physics=cfg.physics,
        )
        # t_s 보정
        new_atm = AtmosphereState(
            t_s=self._t_s + dt,
            status=new_atm.status,
            total_pressure_pa=new_atm.total_pressure_pa,
            o2_partial_pa=new_atm.o2_partial_pa,
            n2_partial_pa=new_atm.n2_partial_pa,
            co2_partial_pa=new_atm.co2_partial_pa,
            h2o_vapor_pa=new_atm.h2o_vapor_pa,
            temperature_k=new_atm.temperature_k,
            o2_fraction=new_atm.o2_fraction,
            co2_ppm=new_atm.co2_ppm,
            breathable=new_atm.breathable,
        )

        # Step 6: HomeostasisController
        heat_input = new_synthesis.power_output_mw * 0.1  # 10% 폐열
        new_reg = self._homeostasis.tick(
            state=state.regulator,
            heat_input_mw=heat_input,
            dt_s=dt,
            physics=cfg.physics,
        )

        # Step 7: RadiationShield
        new_reg = self._radiation.tick(state=new_reg, dt_s=dt)

        # 원소 재고 갱신
        new_elements = ElementInventory(
            hydrogen_mol=max(0.0, state.elements.hydrogen_mol
                             - new_synthesis.pp_rate_mol_s * 4 * dt
                             - new_synthesis.cno_rate_mol_s * 4 * dt),
            helium_mol=state.elements.helium_mol + new_synthesis.he4_produced_mol_s * dt,
            carbon_mol=state.elements.carbon_mol + new_synthesis.c12_produced_mol_s * dt,
            nitrogen_mol=state.elements.nitrogen_mol + n2_fixed * dt,
            oxygen_mol=state.elements.oxygen_mol
                       + new_bio.o2_release_mol_s * dt
                       + new_hydro.o2_from_water_mol_s * dt,
            water_mol=new_hydro.water_total_mol,
            co2_mol=max(0.0, state.elements.co2_mol
                        + self._gas_cycle.crew_co2_output_mol_s() * dt
                        - new_bio.co2_uptake_mol_s * dt),
            ammonia_mol=state.elements.ammonia_mol,
            total_mass_kg=state.elements.total_mass_kg,
        )

        # 새 TerraState 구성
        new_state = TerraState(
            t_s=self._t_s + dt,
            elements=new_elements,
            synthesis=new_synthesis,
            atmosphere=new_atm,
            hydrosphere=new_hydro,
            biosphere=new_bio,
            regulator=new_reg,
        )

        # Step 8: OmegaMonitor + AbortSystem + TerraChain
        health = self._omega.observe(new_state)
        abort_mode = self._abort.evaluate(new_state, health)
        abort_required = self._abort.is_abort_required(new_state, health)

        health = TerraHealth(
            omega_terra=health.omega_terra,
            omega_synthesis=health.omega_synthesis,
            omega_atmosphere=health.omega_atmosphere,
            omega_hydrosphere=health.omega_hydrosphere,
            omega_biosphere=health.omega_biosphere,
            omega_regulator=health.omega_regulator,
            verdict=health.verdict,
            alerts=health.alerts,
            abort_required=abort_required,
        )

        # 감사 체인 기록
        if self._tick_count % cfg.chain_interval == 0:
            self._chain.record(
                t_s=self._t_s + dt,
                event_type=TerraChain.EVENT_TELEMETRY,
                payload=new_state.summary_dict(),
            )

        # 이벤트 감지
        self._detect_events(new_state, new_synthesis, health, abort_mode)

        # 내부 상태 갱신
        self._state = new_state
        self._health = health
        self._t_s += dt
        self._tick_count += 1
        self._prev_phase = new_synthesis.phase

        frame = TelemetryFrame(
            t_s=self._t_s,
            state=new_state,
            health=health,
            abort_required=abort_required,
        )
        return frame

    def _detect_events(
        self,
        state: TerraState,
        synthesis: SynthesisState,
        health: TerraHealth,
        abort_mode: TerraAbortMode,
    ) -> None:
        """이벤트 감지 및 체인 기록."""
        # pp chain 점화
        if (self._prev_phase == SynthesisPhase.INACTIVE
                and synthesis.phase != SynthesisPhase.INACTIVE):
            self._chain.record(
                t_s=self._t_s + self.config.dt_s,
                event_type=TerraChain.EVENT_SYNTHESIS_IGNITION,
                payload={"phase": synthesis.phase.name, "temp_k": synthesis.core_temp_k},
            )

        # 삼중 알파 점화
        if (self._prev_phase != SynthesisPhase.TRIPLE_ALPHA
                and synthesis.phase == SynthesisPhase.TRIPLE_ALPHA):
            self._chain.record(
                t_s=self._t_s + self.config.dt_s,
                event_type=TerraChain.EVENT_TRIPLE_ALPHA_START,
                payload={"temp_k": synthesis.core_temp_k, "power_mw": synthesis.power_output_mw},
            )

        # 대기 경보
        if "CO2_TOXIC" in health.alerts or "O2_LOW" in health.alerts:
            self._chain.record(
                t_s=self._t_s + self.config.dt_s,
                event_type=TerraChain.EVENT_ATMOSPHERE_ALERT,
                payload={"alerts": list(health.alerts), "co2_ppm": state.atmosphere.co2_ppm},
            )

        # 비상 중단
        if abort_mode != TerraAbortMode.NONE:
            self._chain.record(
                t_s=self._t_s + self.config.dt_s,
                event_type=TerraChain.EVENT_ABORT_EVENT,
                payload={"mode": abort_mode.name, "omega": health.omega_terra},
            )

    def ignite_synthesis(self) -> None:
        """합성 엔진 점화 — 코어 온도를 pp chain 점화 온도 이상으로 설정."""
        self.config.core_temp_k = max(
            self.config.core_temp_k,
            self.config.synthesis_config.pp_config.min_ignition_temp_k * 1.1,
        )

    def set_propulsion_mode(self, mode: str) -> None:
        """추진 모드 설정 — 코어 온도/밀도 조정.

        Args:
            mode: "LOW" | "NOMINAL" | "HIGH" | "TRIPLE_ALPHA"
        """
        modes = {
            "LOW": (5e6, 1e5),
            "NOMINAL": (1.5e7, 1.5e5),
            "HIGH": (5e7, 2e5),
            "TRIPLE_ALPHA": (1.5e8, 3e5),
        }
        if mode in modes:
            self.config.core_temp_k, self.config.core_density_kgm3 = modes[mode]

    def simulate(self, duration_s: float) -> List[TelemetryFrame]:
        """지정 시간 동안 시뮬레이션 실행.

        Args:
            duration_s: 시뮬레이션 시간 [s]

        Returns:
            TelemetryFrame 목록
        """
        frames = []
        steps = int(duration_s / self.config.dt_s)
        for _ in range(steps):
            frame = self.tick()
            frames.append(frame)
        return frames

    def get_health(self) -> TerraHealth:
        """현재 건전성 반환."""
        return self._health

    def get_state(self) -> TerraState:
        """현재 상태 반환."""
        return self._state

    def export_log(self, path: str) -> None:
        """JSON 로그 내보내기.

        Args:
            path: 출력 파일 경로
        """
        log = {
            "ship_id": self.config.ship_id,
            "chain_genesis": self._chain.genesis_hash(),
            "chain_length": self._chain.length(),
            "entries": [
                {
                    "index": e.index,
                    "t_s": e.t_s,
                    "event_type": e.event_type,
                    "payload": e.payload,
                    "hash": e.entry_hash,
                }
                for e in self._chain.entries()
            ],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(log, f, indent=2, default=str)
