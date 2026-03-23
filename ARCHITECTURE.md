# TerraCore Stack — Architecture

## 1. 개념: 태양계 → 우주선 매핑

태양계는 수소 핵융합을 에너지원으로 삼아 원소를 합성하고,
중력으로 분류해서 행성 환경을 만드는 자가순환 시스템이다.
지구는 그 안의 닫힌 루프 생명 유지 노드다.

TerraCore는 이 구조를 우주선 안에 재현한다:

| 태양계 구성요소  | TerraCore 구성요소        | 역할                          |
|-----------------|--------------------------|-------------------------------|
| 태양 (핵융합)   | FusionCore / SynthesisEngine | 에너지 생산, H→He→C 원소 합성 |
| 대기권          | AtmosphereEngine         | CO₂↔O₂↔N₂ 순환               |
| 수권            | HydrosphereEngine        | H₂O 전기분해·응결·순환        |
| 생물권          | BiosphereEngine          | 광합성·질소 고정·식량 생산    |
| 지구 자기장     | RegulatorEngine          | 온도·압력·pH·방사선 차폐     |
| 지구 시스템     | TerraAgent               | 전체 오케스트레이션           |

---

## 2. 핵심 물리 방정식

### pp chain 반응률
```
epsilon_pp ~ rho^2 * X^2 * (T/T_ref)^4

  P_pp = r_pp * Q_MeV * E_MeV2J * N_A
  단위: [mol/s * MeV * J/MeV * /mol] = [W]
```

### CNO cycle 반응률
```
epsilon_CNO ~ rho * X * X_CNO * (T/T_ref)^20

  X_CNO = 탄소+질소+산소 질량 분율
  T^20 의존성 → 온도에 극도로 민감
```

### 삼중 알파 반응률
```
epsilon_3alpha ~ rho^2 * Y^3 * (T/T_ref)^40

  Y = He-4 질량 분율
  T^40 의존성 → 임계 온도 근처에서 급격히 변화
  Hoyle 공명: E = 7.6549 MeV (C-12 여기 상태)
```

### 광합성 Michaelis-Menten
```
r_photo = V_max * B * [CO2] / (K_m + [CO2])

  V_max = 단위 바이오매스당 최대 광합성률 [mol CO2/s/kg]
  K_m   = Michaelis 상수 ≈ 200 ppm
  B     = 바이오매스 [kg]

dB/dt = mu_max * B * (1 - B/B_max) * MM(CO2) * MM(light)
```

### 방열 Stefan-Boltzmann
```
Q_rad = epsilon * sigma * A * T^4   [W]

  epsilon = 방사율 (0.9)
  sigma   = 스테판-볼츠만 상수 = 5.67e-8 W/(m^2*K^4)
  A       = 방열판 면적 [m^2]

Delta_T = (Q_in - Q_rad) / C_thermal * dt
```

### 자기 차폐 (Lorentz 힘)
```
F = q * (v x B)
r = m*v / (q*B)   (자기강성)

eta_shield(B) = 1 - exp(-B/B0),  B0 = 0.2 T

  B = 0.1 T → 39% 차폐
  B = 0.5 T → 92% 차폐
```

---

## 3. 8단계 tick 파이프라인

```
입력: core_temp_k, core_density, dt_s
       ↓
Step 1: SynthesisEngine.tick(temp, density, elements)
        → SynthesisState {phase, power_mw, he4/c12 생성률}
        → 원소 재고 갱신 (H 소모, He/C 생성)
       ↓
Step 2: WaterCycle.tick(hydro_state, available_power)
        → HydrosphereState {전기분해율, O2/H2 생성, 수분 재고}
       ↓
Step 3: PhotosynthesisEngine.tick(bio_state, co2_ppm, light_mw)
        → BiosphereState {바이오매스, CO2 흡수, O2 방출}
       ↓
Step 4: NitrogenCycle.tick(atmosphere, bio)
        → N2 고정률 [mol/s]
        → BiosphereState 갱신 (nitrogen_fixed)
       ↓
Step 5: GasCycle.tick(atm, bio, hydro)
        → AtmosphereState {분압, O2 분율, CO2 ppm, 호흡 가능 여부}
       ↓
Step 6: HomeostasisController.tick(reg_state, heat_input)
        → RegulatorState {온도, 압력, pH, thermal_margin}
       ↓
Step 7: RadiationShield.tick(reg_state)
        → RegulatorState {방사선 선량률 갱신}
       ↓
Step 8: OmegaMonitor.observe(terra_state)
        → TerraHealth {Omega_terra, verdict, alerts}
        AbortSystem.evaluate(state, health)
        → TerraAbortMode
        TerraChain.record(frame) [chain_interval마다]
        ↓
출력: TelemetryFrame {t_s, state, health, abort_required}
```

---

## 4. 닫힌 루프 다이어그램

### 에너지-원소 루프
```
[수소 연료] → SynthesisEngine → [헬륨/탄소 생성] → [원소 재고]
                ↓
           [전력 출력 (MW)]
                ↓
     ┌─── WaterCycle (전기분해)
     │         ↓
     │    [O2, H2 생성]
     │         ↓
     └── AtmosphereEngine
```

### 생명 유지 루프
```
[CO2] → BiosphereEngine (광합성) → [O2] → [승무원]
  ↑                                          ↓
  └─────────────── [CO2 배출] ───────────────┘
                       ↓
               [NitrogenCycle]
                       ↓
              [NH3 → 식물 비료]
```

### 수순환
```
[H2O 재고] → WaterCycle.electrolysis → [H2] (연료 피드백 가능)
                ↓                        ↓
            [O2 생성] → 대기       [FusionCore 연료]
                ↓
         승무원 소비 + 광합성 기질
                ↓
          [수분 재고 감소]
                ↑
        [응결·회수 시스템]
```

---

## 5. 기존 스택과의 연결 지도

```
FusionCore Stack
     ↕ (bridge/fusion_core.py)
TerraCore Stack
     ↕ (bridge/brain_core.py)
CookiieBrain Stack

연결 방식:
  FusionCore → TerraCore: 전력 공급 (power_mw)
  TerraCore → FusionCore: H2 연료 피드백 (available_h2_mol)
  TerraCore → BrainCore: 상태 텔레메트리 (omega, alerts)
  BrainCore → TerraCore: 제어 명령 (target_temp, power_mode)

모두 try/except ImportError로 선택적 연동.
독립 운영 시 각 스택은 자체적으로 완결된다.
```

---

## 6. 현재 모델 범위와 한계

### 구현된 범위
- pp chain, CNO cycle, 삼중 알파 반응률 파라메트릭 스케일링
- 이상기체 법칙 기반 대기 분압 추적
- 전기분해 + 승무원 + 광합성 통합 가스 순환
- Michaelis-Menten 광합성 동역학
- Stefan-Boltzmann 복사 방열 + PI 온도 제어
- 자기장 기반 방사선 차폐
- SHA-256 불변 감사 체인

### 단순화된 부분
- 핵반응률: 정밀 핵물리 S-인자 대신 파라메트릭 스케일링
- 대기 모델: 이상기체, 성층 구조 없음
- 방사선: 실시간 우주 날씨 피드 없음
- 생태계: 단일 종 바이오매스 (실제 생태망 미구현)
- 중력: 없음 (μ g 환경 효과 미고려)

---

## 7. 확장 로드맵

### v0.2 — 물리 정밀화
- NACRE/LUNA 핵반응 데이터베이스 연동
- 비이상 기체 대기 (Van der Waals)
- 다층 대기 모델 (대류권·중간권)

### v0.3 — 생태계 심화
- 다종 바이오매스 (조류·고등식물·분해자)
- 토양 생태계 모델
- 음식 영양소 추적 (단백질·탄수화물·지방)

### v0.4 — 시스템 통합
- FusionCore 실시간 양방향 연동
- BrainCore 자율 제어 루프
- 다중 우주선 편대 시뮬레이션

### v1.0 — 하드웨어 인터페이스
- 실제 환경 제어 시스템 (IoT 센서)
- 디지털 트윈 모드
- 실시간 경보 대시보드
