# TerraCore v0.1.0 — 자가순환 생명유지 코어

> **정체성**: 항성-행성 순환에서 영감을 받아, 우주선 내부 물·공기·생물량·질소·열을 닫아두는 **폐순환 생명유지 런타임**.
> 현 MVP의 공학 핵심: 전기분해 → 대기 균형 → 광합성 → 질소고정 → 항상성 제어.
> synthesis 레이어(pp chain/CNO/triple-alpha)는 폐순환 철학의 개념축이자 장기 확장 방향.
> 출력 인터페이스: `h2_rate_mol_s`, `o2_rate_mol_s`, `atmosphere_ok`, `biomass_kg`, `omega_terra`, `chain`

---

## 한눈에 보기

| 항목 | 내용 |
|------|------|
| 언어 | Python 3.9+ (stdlib only) |
| 버전 | v0.1.0 |
| 테스트 | 133 passed (§1~§16) |
| 공학 핵심 | 전기분해 / 대기 / 광합성 / 질소 / 항상성 |
| synthesis | pp chain / CNO / triple-alpha (개념축 + 장기 확장) |
| 출력 | H₂/O₂ [mol/s], 대기, 생태계, 원소 재고 |
| 감사 | SHA-256 TerraChain |
| 독립성 | YES — 단독 사용 가능 |
| 통합 | StarCraft OS submodule |

---

## 핵심 개념

### "지구는 우주선이다" (설계 철학)

```
항성-행성 순환 개념          →    TerraCore 공학 구현
─────────────────────────────────────────────────────
태양 에너지 (핵합성)         →    synthesis/ (개념축 / 장기 확장)
지구 대기 (N₂/O₂/CO₂)      →    atmosphere/gas_cycle
지구 수권 (H₂O 순환)        →    hydrosphere/water_cycle
생물권 (광합성·질소고정)     →    biosphere/photosynthesis+nitrogen
자기장 (방사선 차폐)         →    regulator/radiation_shield
항상성 (온도 조절)           →    regulator/homeostasis
```

> 이 대응표는 설계 철학의 비유다.
> TerraCore v0.1.0의 실제 공학 루프는 atmosphere/hydrosphere/biosphere/regulator 네 축이 중심이다.

### TerraCore ≠ FusionCore

| 구분 | TerraCore | FusionCore |
|------|-----------|-----------|
| 반응 유형 | 자연 항성 순환 은유 + 생명유지 공학 | 공학적 제어 핵융합 (토카막) |
| 공학 핵심 | 전기분해 / 대기 / 생태 / 항상성 | 전력 생산 / 전기추진 변환 |
| 목적 | 물·공기·생태 폐순환 유지 | 전력(MW) + 등가 추진 출력 |
| 출력 형태 | H₂/O₂/C/N + 생태계 | MW + N |
| 폐순환 | **목표: 완전 폐순환** / 현 MVP: 모델 기반 폐순환 | 부분 (연료 소모) |

---

## 핵심 물리 수식

### 공학 핵심 (MVP 중심 — §1~§5)

### 1. 물 전기분해

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

### 2. 대기 가스 수지 (이상기체 분압)

```
이상기체 법칙:  P·V = n·R·T
O₂ 분압:  p_O2 = n_O2 × R × T / V
N₂ 분압:  p_N2 = n_N2 × R × T / V
CO₂ 분압: p_CO2 = n_CO2 × R × T / V

호흡 가능 조건:
  p_O2  ∈ [19, 23] kPa
  p_CO2 < 0.5 kPa   (5000 ppm 근사)
```

### 3. 광합성 (Michaelis-Menten 동역학)

```
광합성률:
  v = V_max × [CO₂] / (K_m + [CO₂])    [mol/s]
  V_max : 최대 광합성 속도
  K_m   : 반포화 농도 (≈ 300 ppm)

생물 질량 성장 (로지스틱):
  dM/dt = r × M × (1 - M/K)
  r : 성장률,  K : 환경 수용력
```

### 4. 질소 고정

```
생물학적 고정:
  N₂ + 8H⁺ + 8e⁻ → 2NH₃ + H₂     [효소 반응]

Haber-Bosch (공학):
  N₂ + 3H₂ → 2NH₃                  (ΔH = -92 kJ/mol)
```

### 5. 항상성 제어 (PI 온도 조절)

```
Stefan-Boltzmann 방열:
  P_rad = ε × σ × A × T⁴

PI 제어:
  u(t) = Kp × e(t) + Ki × ∫e(τ)dτ
  e(t) = T_target - T_current
```

### 6. 방사선 차폐 (자기장 휴리스틱)

```
η(B) = 1 - exp(-B / B₀)
B   : 자기장 강도 [T]
B₀  : 특성 차폐 자기장 [T]
η   : 차폐 효율 [0, 1]

⚠️ 단일 자기장 파라미터 기반 휴리스틱 모델.
   실제 우주 방사선 차폐는 자기장 + 물 차폐 + 구조재 + 탱크 배치가 복합 작용.
   현재 모델은 차폐 한계 초과 여부 판단 지표로만 활용.
```

### 7. Ω_terra 건강도

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

### synthesis 레이어 (항성 순환 개념축 — 장기 확장)

> 아래 수식은 우주선 내부에서 직접 구동되는 공학 장치가 아니다.
> 항성-행성 물질 순환 철학을 수리적으로 모형화한 개념축이자, 원소 재고 갱신의 상징적 레이어다.
> 실제 생명유지 운용에서는 §1~§5 공학 루프가 중심이다.

### A. pp chain (양성자-양성자 체인)

```
반응:  4¹H → ⁴He + 2e⁺ + 2νe + 2γ
에너지: Q = 26.731 MeV

에너지 밀도:
  ε_pp = ε₀ × ρ² × X² × (T/T₀)⁴     [W/m³]
  T_min = 4 × 10⁶ K   (반응 개시 온도)
  X : 수소 질량 분율
```

### B. CNO cycle (탄소-질소-산소 순환)

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

### C. triple-alpha (삼중 알파 과정)

```
반응:  3⁴He → ¹²C + γ
Hoyle 공명: E_Hoyle = 7.6549 MeV  ← 생명 원소 탄소의 기원

에너지 밀도:
  ε_3α = ε₀ × ρ² × Y³ × (T/T₀)⁴⁰    [W/m³]
  T_min = 10⁸ K   (적색거성 핵 이상)
  Y : 헬륨 질량 분율
```

#### synthesis 위상 전환

```
INACTIVE
 └→ PP_CHAIN       T ≥ 4×10⁶ K   (수소 → 헬륨)
     └→ CNO_ACTIVE  T ≥ 1.5×10⁷ K (C 촉매 가속)
         └→ TRIPLE_ALPHA T ≥ 10⁸ K (헬륨 → 탄소)
```

---

## 폐순환 루프 (Closed-Loop — 모델 기반 MVP)

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
  H₂ → FusionCore│  H₂ (잉여) ──────────────────→│[장기] FusionCore 연료 피드백
  O₂ → AgedCare  │  O₂ (잉여) ──────────────────→│승무원 호흡
                  └─────────────────────────────┘

⚠️ 현 MVP는 주요 기체·수분·생물량 수지를 추적하는 모델 기반 폐순환.
   완전 물질 수지 폐쇄(손실/폐기물/독성 축적 포함)는 v0.2+ 목표.
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
│   └── radiation_shield.py — η(B)=1-exp(-B/B₀) 휴리스틱
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
| 전기분해 | η=0.75 단순 근사 | 실제 PEM 전해조 모델 |
| 대기 | O₂/N₂/CO₂ 이상기체 수지 | 다종 기체 + 기상 모델 |
| 생물권 | 단일 생물군 Michaelis-Menten | 다종 생태망 |
| 질소 | Haber-Bosch 단순 | 효소 동역학 정밀 모델 |
| 조절 | PI 제어 + Stefan-Boltzmann | MPC / 강화학습 |
| 방사선 | **자기장 휴리스틱** η(B) | 다층 차폐 + 입자 추적 |
| 폐순환 | 주요 성분 수지 (MVP) | 완전 물질 수지 (손실·폐기물 포함) |
| synthesis | pp/CNO/3α 근사 (개념축) | 정밀 Adelberger 핵단면적 |

---

## 활용성 (Use Cases)

```
단독 사용:
  - 장기 유인 우주 임무 생명유지 시뮬레이션
  - 산소·물·CO₂ 순환 설계 연구
  - 바이오매스·질소 루프 제어 모델링
  - 장기 체류 우주선 생존성 분석
  - 우주 식물 재배 시스템 최적화

StarCraft OS 통합:
  [기술 연결 — 현재 구현됨]
  TerraCore.o2_mol  → AgedCare 승무원 산소
  TerraCore.omega   → StarCraft 통합 건강도
  FusionCore.power  → TerraCore 전기분해 전력

  [장기 철학 연결 — 예정]
  TerraCore.h2_mol  → FusionCore 연료 피드백
  (생명유지 루프 수소와 핵융합 연료 동위원소는 아직 분리된 물질 수지)
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

> 이 소프트웨어는 **연구·교육용 시뮬레이션**입니다.
> 실제 우주선 완전 폐쇄 생명유지 시스템 완성본이 아닙니다 — 주요 성분 수지 기반 MVP 모델.
> 실제 생명유지 장치 운용, 우주선 안전 인증, 유인 우주비행 필수 제어 시스템 용도로 사용할 수 없습니다.
