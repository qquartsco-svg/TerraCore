# TerraCore v0.1.0 — 항성 자가순환 생명유지 코어

> **정체성**: 항성 핵합성 환경을 우주선 내부에 재현하는 **자가순환 폐순환 생명유지 런타임**.
> 수소 → 헬륨 → 탄소/산소/질소 → 대기 → 물 → 생태계 → 다시 수소.
> 지구 자체가 우주선이라는 개념의 공학적 구현.

---

## 한눈에 보기

| 항목 | 내용 |
|------|------|
| 언어 | Python 3.9+ (stdlib only) |
| 버전 | v0.1.0 |
| 테스트 | 133 passed (§1~§16) |
| 핵심 반응 | pp chain / CNO cycle / triple-alpha |
| 출력 | H₂/O₂ [mol/s], 대기, 생태계, 원소 재고 |
| 감사 | SHA-256 TerraChain |
| 독립성 | YES — 단독 사용 가능 |
| 통합 | StarCraft OS submodule |

---

## 핵심 개념

### "지구는 우주선이다"

```
태양계 에너지 흐름        →    우주선 TerraCore 구현
─────────────────────────────────────────────────────
태양 핵 (pp chain)        →    synthesis/ 모듈
태양계 중력장             →    homeostasis/ 조절
지구 대기 (N₂/O₂/CO₂)   →    atmosphere/gas_cycle
지구 수권 (H₂O 순환)     →    hydrosphere/water_cycle
생물권 (광합성·질소고정)  →    biosphere/photosynthesis+nitrogen
지구 자기장 (방사선 차폐) →    regulator/radiation_shield
```

### TerraCore ≠ FusionCore

| 구분 | TerraCore | FusionCore |
|------|-----------|-----------|
| 반응 유형 | 자연 항성 핵합성 | 공학적 제어 핵융합 |
| 온도 | 수백만~수억 K | 10~200 keV |
| 목적 | 원소 합성 + 생명유지 | 전력 + 추력 |
| 출력 형태 | H₂/O₂/C/N + 생태계 | MW + N |
| 폐순환 | YES (완전 폐쇄 루프) | 부분 (연료 소모) |

---

## 핵심 물리 수식

### 1. pp chain (양성자-양성자 체인)

```
반응:  4¹H → ⁴He + 2e⁺ + 2νe + 2γ
에너지: Q = 26.731 MeV

에너지 밀도:
  ε_pp = ε₀ × ρ² × X² × (T/T₀)⁴     [W/m³]
  T_min = 4 × 10⁶ K   (반응 개시 온도)
  X : 수소 질량 분율
```

### 2. CNO cycle (탄소-질소-산소 순환)

```
반응: 6개 단계, C-12 촉매 재생
  ¹²C + ¹H → ¹³N + γ
  ... → ¹²C + ⁴He  (C-12 복원)
에너지: Q = 25.7 MeV

에너지 밀도:
  ε_CNO = ε₀ × ρ × X × X_CNO × (T/T₀)²⁰   [W/m³]
  T_min = 1.5 × 10⁷ K
  X_CNO : CNO 원소 질량 분율 (Z_CNO)
```

### 3. triple-alpha (삼중 알파 과정)

```
반응:  3⁴He → ¹²C + γ
Hoyle 공명: E_Hoyle = 7.6549 MeV  ← 생명 원소 탄소의 기원

에너지 밀도:
  ε_3α = ε₀ × ρ² × Y³ × (T/T₀)⁴⁰    [W/m³]
  T_min = 10⁸ K   (적색거성 핵 이상)
  Y : 헬륨 질량 분율
```

### 4. 물 전기분해

```
반응:  2H₂O → 2H₂ + O₂    (ΔH = +285.8 kJ/mol)
효율:  η = 0.75

H₂ 생산 속도:
  ṅ_H₂ = P_input [W] × η / ΔH [J/mol]
        = P_mw × 10⁶ × 0.75 / 285800
        ≈ P_mw × 2.625  [mol/s per MW]

O₂ 생산 속도:
  ṅ_O₂ = ṅ_H₂ × 0.5        [mol/s]   (화학양론)
```

### 5. 광합성 (Michaelis-Menten 동역학)

```
광합성률:
  v = V_max × [CO₂] / (K_m + [CO₂])    [mol/s]
  V_max : 최대 광합성 속도
  K_m   : 반포화 농도 (≈ 300 ppm)

생물 질량 성장 (로지스틱):
  dM/dt = r × M × (1 - M/K)
  r : 성장률,  K : 환경 수용력
```

### 6. 질소 고정

```
생물학적 고정:
  N₂ + 8H⁺ + 8e⁻ → 2NH₃ + H₂     [효소 반응]

Haber-Bosch (공학):
  N₂ + 3H₂ → 2NH₃                  (ΔH = -92 kJ/mol)
```

### 7. 항상성 제어 (PI 온도 조절)

```
Stefan-Boltzmann 방열:
  P_rad = ε × σ × A × T⁴

PI 제어:
  u(t) = Kp × e(t) + Ki × ∫e(τ)dτ
  e(t) = T_target - T_current
```

### 8. 방사선 차폐

```
η(B) = 1 - exp(-B / B₀)
B   : 자기장 강도 [T]
B₀  : 특성 차폐 자기장 [T]
η   : 차폐 효율 [0, 1]
```

### 9. Ω_terra 건강도

```
Ω_synthesis   = f(합성 출력, 온도 안정성)
Ω_atmosphere  = f(O₂/N₂/CO₂ 분압, 호흡 가능성)
Ω_hydrosphere = f(H₂O 재고, 전기분해 효율)
Ω_biosphere   = f(생물 질량, 광합성률)
Ω_regulator   = f(온도 안정성, 방사선 차폐)

Ω_terra = Ω_synthesis×0.25 + Ω_atmosphere×0.30
         + Ω_hydrosphere×0.20 + Ω_biosphere×0.15
         + Ω_regulator×0.10

판정: THRIVING(≥0.80) / STABLE(0.60~) / FRAGILE(0.40~) / CRITICAL(<0.40)
```

---

## 핵합성 위상 전환

```
INACTIVE
 └→ PP_CHAIN       T ≥ 4×10⁶ K   (수소 → 헬륨)
     └→ CNO_ACTIVE  T ≥ 1.5×10⁷ K (C 촉매 가속)
         └→ TRIPLE_ALPHA T ≥ 10⁸ K (헬륨 → 탄소)
```

---

## 폐순환 루프 (Closed-Loop)

```
                  ┌─────────────────────────────┐
                  │          TerraCore           │
                  │                              │
  FusionCore      │  H₂O ──전기분해──→ H₂ + O₂  │
  전력(MW) ───────→│                    │         │
                  │  CO₂ + H₂O ←광합성← O₂       │
                  │               ↑              │
                  │           생물 질량           │
                  │               ↑              │
                  │  N₂ ──질소고정──→ NH₃         │
                  │                              │
  H₂ → FusionCore│  H₂ (잉여) ──────────────────→│FusionCore 연료
  O₂ → AgedCare  │  O₂ (잉여) ──────────────────→│승무원 호흡
                  └─────────────────────────────┘
```

---

## SHA-256 감사 체인 (TerraChain)

```python
# 체인 검증
from terra_core import TerraAgent, TerraAgentConfig

agent = TerraAgent(TerraAgentConfig())
agent.ignite_synthesis()

for _ in range(20):
    agent.tick()

# 무결성 검증
assert agent._chain.verify(), "TerraChain 무결성 실패"
print(f"체인 길이: {agent._chain.length}")
print(f"최신 해시: {agent._chain.latest_hash[:16]}...")

# 제네시스 블록 확인
genesis = agent._chain._entries[0]
print(f"Genesis: {genesis.event_type} | {genesis.this_hash[:16]}...")
```

---

## 구조

```
terra_core/
├── contracts/
│   └── schemas.py         — TerraPhysicsConfig + 12개 frozen dataclass
├── synthesis/
│   ├── pp_chain.py        — ε ∝ ρ²X²T⁴  (T > 4×10⁶K)
│   ├── cno_cycle.py       — ε ∝ ρXX_CNO·T²⁰  (T > 1.5×10⁷K)
│   ├── triple_alpha.py    — ε ∝ ρ²Y³T⁴⁰, Hoyle 공명
│   └── synthesis_engine.py — 위상 결정 + 원소 재고 갱신
├── atmosphere/
│   └── gas_cycle.py       — 이상기체 분압, O₂/N₂/CO₂ 수지
├── hydrosphere/
│   └── water_cycle.py     — 전기분해 η=0.75, H₂O 재고
├── biosphere/
│   ├── photosynthesis.py  — Michaelis-Menten + 로지스틱 성장
│   └── nitrogen_cycle.py  — 생물 고정 + Haber-Bosch
├── regulator/
│   ├── homeostasis.py     — PI 제어 + Stefan-Boltzmann
│   └── radiation_shield.py — η(B)=1-exp(-B/B₀)
├── safety/
│   ├── omega_monitor.py   — Ω_terra 5레이어 건강도
│   └── abort_system.py    — 5가지 중단 모드
├── audit/
│   └── terra_chain.py     — SHA-256 감사 체인
├── bridge/
│   ├── fusion_core.py     — FusionCore 연동 (전력 수신, H₂ 공급)
│   └── brain_core.py      — CookiieBrain 연동
└── terra_agent.py         — 8단계 tick 파이프라인
```

---

## 빠른 시작

```python
from terra_core import TerraAgent, TerraAgentConfig

agent = TerraAgent(TerraAgentConfig())
agent.ignite_synthesis()

for _ in range(30):
    frame = agent.tick()

s = frame.state
print(f"위상:    {s.synthesis.phase.name}")
print(f"H₂ 생산: {s.hydrosphere.electrolysis_rate_mol_s:.4f} mol/s")
print(f"O₂ 재고: {s.elements.oxygen_mol:.1f} mol")
print(f"대기 OK: {s.atmosphere.is_breathable}")
print(f"생물량:  {s.biosphere.biomass_kg:.2f} kg")
print(f"Ω_terra: {frame.health.omega_terra:.3f}")
print(f"체인:    {agent._chain.verify()}")
```

---

## 확장성 (Extension Points)

| 레이어 | 현재 | 확장 방향 |
|--------|------|-----------|
| 핵합성 | pp/CNO/3α 근사식 | 정밀 Adelberger 핵단면적 |
| 대기 | O₂/N₂/CO₂ 이상기체 | 다종 기체 + 기상 모델 |
| 수권 | 전기분해 근사 | 실제 PEM 전해조 모델 |
| 생물권 | 단일 생물군 | 다종 생태망 |
| 질소 | Haber-Bosch 단순 | 효소 동역학 정밀 모델 |
| 조절 | PI 제어 | MPC / 강화학습 |
| 방사선 | 단순 자기장 모델 | 입자 추적 시뮬레이션 |

---

## 활용성 (Use Cases)

```
단독 사용:
  - 장기 유인 우주 임무 생명유지 시뮬레이션
  - 폐쇄 루프 생태계 설계 연구
  - 핵합성 기반 원소 생산 모델링
  - 우주 식물 재배 시스템 최적화

StarCraft OS 통합:
  TerraCore.h2_mol  → FusionCore 연료 피드백
  TerraCore.o2_mol  → AgedCare 승무원 산소
  TerraCore.omega   → StarCraft 통합 건강도
```

---

## 테스트

```bash
cd TerraCore_Stack
python -m pytest tests/test_terra_core.py -v
# 133 passed  §1~§16
```

§1 ElementInventory / §2 SynthesisState / §3 AtmosphereState /
§4 HydrosphereState / §5 BiosphereState / §6 RegulatorState /
§7 TerraState / §8 pp chain / §9 CNO cycle / §10 triple-alpha /
§11 전기분해 / §12 광합성 / §13 질소고정 / §14 항상성 /
§15 TerraChain / §16 TerraAgent 통합

---

## 연계 레포

| 레포 | 관계 |
|------|------|
| [StarCraft](https://github.com/qquartsco-svg/StarCraft) | TerraCore를 submodule로 포함하는 통합 OS |
| [FusionCore](https://github.com/qquartsco-svg/FusionCore) | 전력 공급 → TerraCore 전기분해 구동 |
| [Rocket_Spirit](https://github.com/qquartsco-svg/Rocket_Spirit) | 추진계 (TerraCore와 간접 연계) |

---

> 이 소프트웨어는 연구·교육용 시뮬레이션입니다.
> 실제 생명유지 장치 운용, 우주선 안전 인증, 유인 우주비행 필수 제어 시스템 용도로 사용할 수 없습니다.
