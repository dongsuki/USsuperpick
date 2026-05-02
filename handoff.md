# USsuperpick × markmarkmark 통합 작업 인계 문서

작업 일자: 2026-05-02 (최초) / 2026-05-02 (Q1~Q3 결정 반영 갱신)
범위: markmarkmark에 미국주식판 추가 (USsuperpick 데이터 활용)
선택된 아키텍처: **옵션 C — 데이터 레이어 통합 + UI 부분 분리 + "공유 우선" 전략**
NavigationBar 탭 구성: `슈퍼픽 한국주식` / `슈퍼픽 미국주식` / `월클답안지` / `시크릿리포트`
미국 Airtable: Base `appAh82iPV3cH6Xx5` / Table `tbljCB2CnDe2eWB3M` / View `viwtY7XrICnpAgyvY`

---

## 🎯 최종 목표

`markmarkmark`(한국주식 React 프론트엔드)에 **미국주식 대시보드를 추가**한다.
데이터는 `USsuperpick`(Python 스캐너 파이프라인)이 Airtable에 채워주고, markmarkmark는 그 데이터를 읽어 렌더한다.

---

## 📁 두 프로젝트 위치

| 프로젝트 | 경로 | 역할 |
|---|---|---|
| `USsuperpick` | `C:\Users\USER\Desktop\USsuperpick` | 데이터 파이프라인 (Python) — FMP/Polygon → Airtable |
| `markmarkmark` | `C:\Users\USER\Desktop\markmarkmark` | UI (React/TS/Vite) — Airtable → 화면 |

---

## 📊 USsuperpick 현재 상태

### 핵심 파일
- `us_minervini_scanner_v2.py` (40KB) — NASDAQ/NYSE 전종목 스캔 → Minervini 8조건 → Airtable 동기화
- `mark.py` (25KB) — Airtable "마크미너비니" 뷰 티커 → FMP/Polygon 재무·가격 데이터 채움
- `.github/workflows/daily_scan.yml` — 평일 UTC 21:00 자동 실행 (수동 트리거 가능)

### 동작 흐름
```
[GitHub Actions: 평일 UTC 21:00 트리거]
  ↓
1. us_minervini_scanner_v2.py (~20~40분)
   ├ FMP /stock-screener → 5,000~8,000 종목
   ├ FMP /historical-price-full → 가격 400일치
   ├ 모멘텀 점수 → RS 등급 (전체 모집단 기준 percentile)
   ├ 투자 후보 필터 (시총 ≥ $1억, 거래량 ≥ 10만, 가격 ≥ $5)
   ├ Minervini 8조건 (RS≥70, SMA, 52주 고저가 등)
   └ Airtable 동기화 (Update / Create / Delete)
  ↓
2. sleep 60초
  ↓
3. mark.py (~3~10분)
   ├ Airtable "마크미너비니" 뷰에서 티커 가져오기
   ├ 각 티커마다 Polygon 가격 + FMP 분기/연간 income-statement
   ├ 분기 8개·연간 6년 EPS/매출/영업이익/NPM 성장률 계산
   └ Airtable 업데이트 (~70 필드)
```

### Airtable 출력 (총 79필드)
- scanner_v2가 채우는 9개: 티커, 종목명, 현재가, 등락률, 거래량, 시가총액, 52주 신고가 비율, RS순위, 재료명(섹터)
- mark.py가 채우는 ~70개: EPS 값(8분기 + 6년), EPS·매출·영업이익·NPM 성장률(3분기 + 3년) + 각 날짜

### 아직 안 받고 있는 것 (Phase 1에서 보강 대상)
- ROE (분기 3개 + 연간 3년)
- PER (분기 3개 + 연간 3년)
- PEG (최신분기)
- 영업이익률 raw 값 (분기 3개 + 연간 3년)
- 매출액 raw 값 (분기 8개)
- 순이익률 raw 값 (분기 8개 + 연간 3년)

---

## 📊 markmarkmark 현재 상태

### 기술 스택
- React 18 + TypeScript + Vite + Tailwind
- 라우팅: react-router-dom
- 데이터: Airtable REST API 직접 호출
- 배포: Netlify

### 핵심 파일
- `src/App.tsx` — 라우팅 (`/`, `/answer-sheet`, `/secret-report`, `/suikasak72978566/*`)
- `src/types.ts` — Stock 인터페이스 (한국 시장 박힘)
- `src/data/dataService.ts` — Airtable fetch 함수들
- `src/components/StockDashboard.tsx` — 메인 대시보드
- `src/components/AnswerSheet.tsx`, `SecretReport.tsx` — 한국 컨텐츠 (미국과 무관)
- `src/utils/stockEvaluator.ts` — 평가 점수 알고리즘 ⭐ 핵심 공통 자산
- `src/utils/stockFilter.ts` — 필터 로직 ⭐ 핵심 공통 자산

### 한국 시장 박힌 부분 (확장 또는 분리 대상)
- `시장구분: 'KOSPI' | 'KOSDAQ'` (types.ts:15) — union 타입 하드코딩
- `시가총액(억원)` 단위
- `거래대금` (금액 단위, 미국은 거래량 = 수량)
- `종목코드` 'A+숫자' 형식
- 한국 전용 필드: `3존`, `8존`, `15존`, `20존`, `33존`, `슈퍼존`, `50존`, `3일선_위`, `중심주분류`, `재료분류`

### 한국 컨텐츠 페이지 (미국과 무관, 그대로 유지)
- `/answer-sheet` (월클답안지)
- `/secret-report` (시크릿리포트)

---

## 🔍 두 데이터의 갭 분석

### ✅ 매핑 가능 (그대로 또는 형식만 맞춤)
- 종목코드 ↔ 티커 (형식 다름, optional 처리)
- 종목명, 현재가, 등락률, RS순위, 52주 신고가 비율 — 동일

### 🟡 단위/개념 차이 (변환 필요)
| markmarkmark | USsuperpick | 처리 |
|---|---|---|
| 시가총액 (억원) | 시가총액 (USD) | fetch 시 정규화 또는 표시 단계에서 변환 |
| 거래대금 (금액) | 거래량 (수량) | 시장별 다른 필드명 또는 옵셔널 |
| 시장구분 KOSPI/KOSDAQ | 거래소 NASDAQ/NYSE/AMEX | union 타입 확장 |
| 재료분류 (테마) | 재료명 (섹터) | 의미 다르지만 같은 필드명으로 통일 가능 |

### 🔴 미국 데이터에 빠진 것 (Phase 1에서 보강)
- ROE_3년/2년/1년/전전분기/전분기/최신분기 (6개)
- PER_3년/2년/1년/전전분기/전분기/최신분기 (6개)
- PEG_최신분기 (1개)
- 영업이익률 raw (분기 3 + 연간 3 = 6개)
- 매출액 raw (분기 8개)
- 순이익률 raw (분기 8 + 연간 3 = 11개)
→ **약 30개 신규 Airtable 필드 추가 필요**

### 🔴 한국 시장 특유 (미국엔 없어도 됨)
- 존 시리즈 (3존~슈퍼존, 50존, 3일선_위)
- 중심주분류

---

## 🏗 옵션 C 아키텍처 — 공유 우선 전략

### 폴더 구조 목표
```
src/
├── components/
│   ├── common/                ⭐ 공통 (양쪽 사용)
│   │   ├── StockTable.tsx
│   │   ├── StockFilter.tsx
│   │   ├── StockSorter.tsx
│   │   ├── RankingView.tsx
│   │   └── ScoreBadge.tsx
│   ├── stock-detail/          ⭐ 거의 공통 (props로 시장 차이)
│   │   ├── StockHeader.tsx
│   │   ├── ScoreCards.tsx
│   │   ├── ChartSection.tsx
│   │   ├── GrowthCharts.tsx
│   │   ├── QuarterlyEpsChart.tsx
│   │   └── YearlyEpsChart.tsx
│   ├── kr/                    🇰🇷 한국 전용
│   │   ├── KRDashboard.tsx
│   │   ├── ZoneFilter.tsx
│   │   └── CentralStock.tsx
│   └── us/                    🇺🇸 미국 전용 (신규)
│       ├── USDashboard.tsx
│       └── (필요 시 추가)
├── data/
│   └── dataService.ts         ⭐ fetchKRStockData + fetchUSStockData
├── utils/                     ⭐ 모두 공통
│   ├── stockEvaluator.ts
│   ├── stockFilter.ts
│   └── formatting.ts
└── types.ts                   ⭐ Stock 베이스 + KRStock + USStock
```

### 절대 규칙 3가지

#### 규칙 1: 평가 로직은 무조건 `utils/`에
- `stockEvaluator.ts`, `stockFilter.ts` 절대 시장별 분리 금지
- 시장별 차이는 함수 인자/옵션으로 처리
- 데이터 누락 가능성은 `field ?? defaultValue` 패턴 사용

#### 규칙 2: 차트/표 컴포넌트는 무조건 `common/`에
- 시장별 라벨(억원/USD)은 props로 주입
- 데이터 형식 차이는 fetch 단계에서 정규화

#### 규칙 3: 시장 전용은 `kr/` 또는 `us/`에 격리
- 한국: 존 시리즈, 중심주분류, 재료분류 필터 등
- 미국: ADR 마크, 섹터 비교 등 (필요 시)

#### 위험 시나리오 — 미리 알고 있어야 함
> **"한국에서만 새 필드 추가했는데 evaluator가 그 필드를 참조"**
- 미국 데이터에 그 필드 없으면 `undefined` → 평가 시스템 깨짐
- **대책 1**: utils에서 항상 옵셔널 체크 (`stock.field ?? 0`)
- **대책 2**: 시장별 평가 함수 분리 (`evaluateKR`, `evaluateUS`)가 evaluator 내부 분기

---

## 📋 작업 단계 (Phase 1~4)

### ⭐ Phase 1 — USsuperpick 데이터 보강 (먼저 시작)

markmarkmark의 평가 시스템(`stockEvaluator.ts`)은 ROE/PER/PEG/영업이익률/매출액 raw 값을 사용. 현재 mark.py가 안 받고 있어서, 이걸 안 채우면 미국주식이 평가 시스템 절반만 작동함.

**작업 항목:**

#### 1-1. mark.py 확장
- 위치: `C:\Users\USER\Desktop\USsuperpick\mark.py`
- 추가할 API 호출:
  - FMP `/key-metrics?period=quarter&limit=20` → ROE, PER, PEG
  - FMP `/key-metrics?period=annual&limit=6` → 연간 ROE, PER, PEG
- 기존 income-statement 응답에서 저장만 빠진 것:
  - `revenue` raw (매출액_최신분기 ~ 8분기전)
  - `operatingIncome / revenue × 100` (영업이익률 raw)
  - `netIncome / revenue × 100` (순이익률 raw, 분기 8개·연간 3년)
- `update_airtable()` 함수의 record dict (라인 ~342)에 새 필드 추가

#### 1-2. Airtable 필드 자동 생성 스크립트
- 새 파일: `C:\Users\USER\Desktop\USsuperpick\create_airtable_fields.py`
- Airtable Metadata API 호출:
  ```
  POST https://api.airtable.com/v0/meta/bases/{baseId}/tables/{tableId}/fields
  ```
- 필요: PAT (Personal Access Token) + `schema.bases:write` 스코프
- 약 30개 신규 필드 정의 (ROE 6, PER 6, PEG 1, 영업이익률 6, 매출액 8, 순이익률 11)
- 1회성 실행 (필드 만들고 끝)

#### 1-3. (선택) 성능 개선
- `scanner_v2.py:762` 배치 sleep(2) 제거 → 7~8분 절감
- `scanner_v2.py` max_workers 6 → 12 → 처리시간 30~40% 단축
- `mark.py` Polygon 시장 상태 1회만 호출 (현재 종목마다 호출 중) → 30~50초 절감
- `mark.py:441` sleep(1) → 0.2 → 50종목 기준 40초 절감

**완료 기준:**
- GitHub Actions 워크플로우 1회 정상 실행
- Airtable에 신규 필드 모두 채워짐
- ROE, PER, PEG가 의미 있는 값(NaN/null 아님)으로 들어옴

**예상 시간:** 4~6시간

---

### Phase 2 — markmarkmark 데이터 레이어 확장

**작업 항목:**

#### 2-1. `src/types.ts` 확장
- 옵션 A: `Stock` 인터페이스에 미국 필드 추가 + 시장구분 union 확장
  ```typescript
  시장구분: 'KOSPI' | 'KOSDAQ' | 'NASDAQ' | 'NYSE' | 'AMEX';
  ```
- 옵션 B: `KRStock`, `USStock` 분리 + 베이스 `Stock` 인터페이스 (권장)
- `종목코드` optional 처리, `티커` 필드 추가

#### 2-2. `src/data/dataService.ts` 확장
- 새 함수: `fetchUSStockData(): Promise<USStock[]>`
- 새 환경변수:
  - `VITE_US_AIRTABLE_BASE_ID`
  - `VITE_US_AIRTABLE_TABLE_ID`
  - (Q1 결정에 따라 같은 BASE 다른 TABLE이거나 다른 BASE)

#### 2-3. `.env`, `.env.example` 추가

**예상 시간:** 2~3시간

---

### Phase 3 — UI 컴포넌트 (옵션 C 적용)

**작업 항목:**

#### 3-1. 폴더 재구성
- 기존 `src/components/StockDashboard.tsx` → `src/components/kr/KRDashboard.tsx`
- `src/components/common/` 폴더 신규 생성
- `src/components/us/USDashboard.tsx` 신규 생성

#### 3-2. 공통 컴포넌트 추출
- `StockListTable`, `StockRankingTable` → `common/`로 이동
- `StockFilter` → `common/StockFilter.tsx`로 정리 (한국 전용 필터는 props 또는 별도 KRFilter)
- `stock-detail/*` → 그대로 유지하고 양쪽 dashboard에서 import

#### 3-3. 라우팅 추가 (`App.tsx`)
```typescript
<Route path="/" element={<KRDashboard ... />} />
<Route path="/us" element={<USDashboard ... />} />
<Route path="/suikasak72978566" element={<KRDashboard ... isAdminMode />} />
<Route path="/suikasak72978566/us" element={<USDashboard ... isAdminMode />} />
```

#### 3-4. NavigationBar에 미국주식 메뉴 추가

#### 3-5. 시장 특화 처리
- 미국엔 존 시리즈, 중심주분류 숨김
- 시가총액 표기 `$1.5B` 형식
- 거래량 표기 (백만주 단위 등)

**예상 시간:** 6~8시간

---

### Phase 4 — 정리 + 테스트

1. 환경변수 정리, GitHub Actions 결과 확인
2. Vite 빌드 테스트 (`npm run build`)
3. Netlify 미리보기 배포
4. 양쪽 시장 데이터 정상 표시 확인

**예상 시간:** 2~4시간

**총 예상 시간: 16~24시간**

---

## ✅ 의사결정 완료 (2026-05-02)

### Q1. Airtable Base 분리 여부 → **완전히 다른 Base**
- 미국주식 Airtable URL: `https://airtable.com/appAh82iPV3cH6Xx5/tbljCB2CnDe2eWB3M/viwtY7XrICnpAgyvY`
- **Base ID**: `appAh82iPV3cH6Xx5`
- **Table ID**: `tbljCB2CnDe2eWB3M`
- **View ID**: `viwtY7XrICnpAgyvY`
- 한국 Base와 환경변수 분리:
  - 한국: `VITE_AIRTABLE_BASE_ID`, `VITE_AIRTABLE_TABLE_ID` (기존)
  - 미국: `VITE_US_AIRTABLE_BASE_ID`, `VITE_US_AIRTABLE_TABLE_ID`, `VITE_US_AIRTABLE_VIEW_ID` (신규)
- **확인 완료**: 이 베이스(`appAh82iPV3cH6Xx5`)가 USsuperpick GitHub Actions가 이미 데이터 채우고 있는 베이스. 즉 `AIRTABLE_BASE_ID` GitHub Secret 값 = `appAh82iPV3cH6Xx5`. USsuperpick 코드/시크릿 변경 없이 markmarkmark에서 이 베이스를 읽기만 하면 됨.

### Q2. 답안지/시크릿리포트에 미국 들어가나? → **안 들어감**
- 답안지·시크릿리포트는 **한국 컨텐츠 그대로 유지** (미국 추가 없음)
- NavigationBar 탭 구성 변경:
  - **현재**: `슈퍼픽` / `월클답안지` / `시크릿리포트`
  - **변경 후**: `슈퍼픽 한국주식` / `슈퍼픽 미국주식` / `월클답안지` / `시크릿리포트`
- 라우팅 변경 (관리자 경로 동일하게):
  - `/` → `KRDashboard` (라벨만 "슈퍼픽 한국주식"으로 변경)
  - `/us` → `USDashboard` (신규)
  - `/answer-sheet` → 그대로
  - `/secret-report` → 그대로
  - `/suikasak72978566` → `KRDashboard`
  - `/suikasak72978566/us` → `USDashboard`
  - `/suikasak72978566/answer-sheet`, `/secret-report` → 그대로

### Q3. 미국 시장 특유 기능 추가 여부 → **추후 고려**
- 지금은 **한국과 동일 수준**의 UI만 구현
- ADR 마크, 섹터 비교, 옵션/공매도 데이터 등은 나중에 결정
- 의미: USDashboard는 KRDashboard와 동일한 구조 + 한국 전용 필드(존, 중심주분류 등)만 제거

---

## 🚀 새 세션이 시작할 때 첫 번째 액션

**Q1~Q3 결정 완료. Phase 1 즉시 착수 가능.**

### Phase 1 작업 순서 (USsuperpick 폴더에서)

> **전제 확인됨 (2026-05-02)**: USsuperpick GitHub Actions가 이미 `appAh82iPV3cH6Xx5` 베이스에 데이터 채우고 있음. mark.py / scanner_v2.py 의 Airtable 연결은 그대로 유지. Phase 1은 기존 베이스에 **신규 필드 추가 + mark.py가 그 필드들도 채우게 확장**하는 작업.

1. **mark.py 확장**
   - `get_financials_fmp` (라인 85) 패턴 참고하여 `get_key_metrics_fmp(ticker, period)` 신규 함수 작성
   - FMP `/key-metrics?period=quarter&limit=20`, `/key-metrics?period=annual&limit=6`
   - `calculate_growth_rates_fmp` (라인 114)에서 받은 quarterly/annual 데이터에서 raw 값 추출:
     - `revenue` raw → 매출액_최신분기 ~ 매출액_8분기전
     - `operatingIncome / revenue × 100` → 영업이익률(%) raw
     - `netIncome / revenue × 100` → 순이익률 raw
   - `update_airtable()` (라인 331) record dict (라인 342)에 신규 필드 약 30개 추가

2. **create_airtable_fields.py 신규 작성**
   - 위치: `C:\Users\USER\Desktop\USsuperpick\create_airtable_fields.py`
   - Airtable Metadata API로 Base(`appAh82iPV3cH6Xx5`) Table(`tbljCB2CnDe2eWB3M`)에 약 30개 필드 일괄 생성
   - 필드 그룹: ROE 6, PER 6, PEG 1, 영업이익률(%) 6, 매출액 raw 8, 순이익률 11
   - **사용자에게 Airtable PAT 발급 안내 필수** (`schema.bases:write` 스코프)

3. **필드 생성 스크립트 1회 실행 후 검증**
   - Airtable Base에 신규 필드 모두 추가됐는지 확인

4. **GitHub Actions 수동 트리거 후 결과 검증**
   - 워크플로우 정상 완료
   - 신규 필드들이 의미 있는 값으로 채워졌는지 확인 (NaN/null 아님)

5. **(선택) 성능 개선 적용**
   - scanner_v2.py:762 sleep(2) 제거
   - scanner_v2.py max_workers 6→12
   - mark.py Polygon 시장상태 1회만 호출
   - mark.py:441 sleep(1)→0.2

### Phase 1 완료 후 → Phase 2 (markmarkmark) 진입

Phase 2 시작 전 **별도 git 브랜치 생성**:
```
cd C:\Users\USER\Desktop\markmarkmark
git checkout -b us-stock
```
이 브랜치에서 Phase 2~4 작업 후 main에 머지.

---

## 🛡 한국 markmarkmark 영향 차단 전략

사용자 요구: **"미국 작업 시 한국 페이지에 영향 안 가게"**

### 솔직한 답변
- **결과는 보장 가능** (한국 페이지 동작이 변하지 않음)
- **코드 0줄 수정은 불가능** (옵션 C는 본질적으로 일부 코드를 공유하는 구조)

### 영역별 영향도

#### 🟢 한국 코드 0줄 수정 (영향 0)
- `components/us/*` — 신규 폴더
- `create_airtable_fields.py` (USsuperpick 신규)
- `mark.py` 확장 (USsuperpick — 미국 Airtable에만 영향)

#### 🟡 새 코드 "추가만" (한국 동작 그대로)
- `App.tsx` — 미국 라우트 신규 추가, 기존 라우트 그대로
- `NavigationBar` — "슈퍼픽" 라벨만 "슈퍼픽 한국주식"으로 변경, 메뉴 추가
- `dataService.ts` — `fetchUSStockData` 신규 함수만, 기존 `fetchDataFromAirtable` 안 건드림
- `types.ts` — `USStock` 인터페이스 신규, `시장구분` union에 미국 거래소 추가 (KOSPI/KOSDAQ 그대로)

#### 🔴 의도된 공유 영역 (한국에도 영향 갈 수 있음)
- `utils/stockEvaluator.ts` — 미국 데이터 누락 옵셔널 처리 추가하면 한국 평가 로직에도 변경
- `utils/stockFilter.ts` — 동일
- `components/stock-detail/*` — 시장 차이를 props로 받으면 기존 호출부에 prop 추가 필요
- `components/common/*` — 공통 컴포넌트 추출 시 기존 한국 코드의 import 경로 변경

### 회귀 보호 4가지 규칙

#### 규칙 1: 별도 브랜치 작업
```bash
cd C:\Users\USER\Desktop\markmarkmark
git checkout -b us-stock
# 모든 markmarkmark 작업은 이 브랜치에서
# 완료 후 충분한 테스트 → main 머지
```

#### 규칙 2: 공통 영역 수정 시 한국 페이지 회귀 테스트
공통 영역(`utils/`, `common/`, `stock-detail/`) 수정 후 반드시 확인:
- 한국 dashboard 점수(종합점수/EPS점수/매출점수) 값이 변경 전과 동일
- 필터 동작 (RS순위, 52주신고가비율 등) 정상
- 차트 정상 렌더 (분기/연간 EPS, 매출, 영업이익률)

#### 규칙 3: 작업 중 한국 페이지 항상 띄워놓기
```bash
npm run dev
# localhost:5173/ 에서 한국 페이지 항상 모니터링
```
공통 컴포넌트 수정 즉시 한국 화면 깨졌는지 시각 확인.

#### 규칙 4: types.ts 확장 시 호환성 유지
- 기존 `Stock` 인터페이스의 모든 필드는 그대로 (시그니처 안 깸)
- 새 필드는 옵셔널(`?`)로만 추가
- `시장구분` union 확장 — 기존 KOSPI/KOSDAQ는 보존, 미국 거래소만 추가
- `종목코드`를 옵셔널로 변경하더라도 한국 데이터는 항상 채워지므로 영향 없음

### 회귀 발생 시 대처
- 한국 페이지 깨짐 발견 → 즉시 브랜치 작업 중단
- 어느 커밋이 깨뜨렸는지 `git bisect`
- 깨진 영역이 공통(`utils/`, `common/`)이면 → 옵셔널 처리 강화 또는 시장별 분기 추가
- 옵션 C 본질을 깨뜨릴 정도면 → 그 부분만 시장 분리 (kr/us 별도 함수)

---

## 🛡 절대 지킬 것 (옵션 C 보호)

작업 중 다음을 **절대 하지 말 것**:
1. ❌ `utils/stockEvaluator.ts`를 한국용/미국용으로 복사하지 말 것
2. ❌ 차트 컴포넌트(`GrowthCharts`, `EpsChart` 등)를 시장별로 복제하지 말 것
3. ❌ "일단 미국용으로 따로 만들고 나중에 통합" 식의 임시 분리 금지 (실제로는 통합 안 됨)
4. ❌ 한국 평가 로직에 미국에 없는 필드를 옵셔널 체크 없이 직접 참조하지 말 것
5. ✅ "이게 다른 시장에도 적용되나?" 자문 후 50%+ 가능성 → `common/` 또는 `utils/`에 배치

---

## 📚 참고 — 결정의 배경

### 왜 옵션 C를 선택했나
- **옵션 A** (한 페이지 토글): 데이터 모델이 너무 달라 분기문 폭발 위험
- **옵션 B** (완전 분리): 평가 시스템 변경 시 수동 동기화 빠뜨림 위험
- **옵션 C** (공유 우선): 평가/차트/필터 핵심 = 자동 동기화, 시장 특유 = 깔끔히 분리

이 선택은 markmarkmark의 1년 커밋 히스토리(61커밋) 분석으로 검증됨:
- 평가 시스템 변경 6회 (양쪽 동시 적용 필요) → utils/ 공통이 답
- 새 필드 추가 6회 (양쪽 작업 필요) → 분포는 어느 옵션이나 비슷
- 한국 전용 필터/UI 8회 → 옵션 A는 분기문 폭발할 패턴
- 차트 컴포넌트 변경 5회 (양쪽 자동 적용 가능) → 옵션 B는 동기화 누락 위험

### 왜 Phase 1 (데이터 보강)부터 하나
- markmarkmark의 `stockEvaluator.ts`는 ROE, PER, PEG, 영업이익률, 매출액 raw 값을 사용
- 미국 데이터에 이 필드들이 없으면 평가 시스템 절반만 작동
- UI부터 손대도 데이터가 빈약하면 의미 없음
- 데이터 보강은 mark.py 확장 + Airtable 필드 생성 정도라 비교적 작은 작업 (4~6시간)

### Airtable 필드 자동 생성 가능 여부
- ✅ Metadata API로 가능
- 단 PAT (Personal Access Token) + `schema.bases:write` 스코프 필요
- 기존 `airtable-python-wrapper`는 데이터 API만 지원 → `pyairtable` 또는 직접 HTTP 호출

---

## 📝 핵심 참조 정보

### Airtable 정보 (markmarkmark 한국주식)
- 한국주식 Base/Table ID: `.env`의 `VITE_AIRTABLE_BASE_ID`, `VITE_AIRTABLE_TABLE_ID` (값은 secret)
- 답안지 Base ID: `appA4t9o1QMTDZul7`
- 답안지 Table ID: `tblh7sE1Bbz2OXjBM`
- 종목마스터 Table ID: `tbllRbqwpfEY8dV2O`
- 시크릿리포트 Base ID: `appJFk54sIT9oSiZy`
- 시크릿리포트 Table ID: `tblCSlNYBX2dYi3XS`

### USsuperpick Airtable 정보
- 환경변수: `AIRTABLE_API_KEY`, `AIRTABLE_BASE_ID`, `AIRTABLE_TABLE_NAME` (= `트레이더의 선택`)
- 핵심 뷰: `마크미너비니` (mark.py 입력)
- GitHub Secrets에 등록되어야 워크플로우 동작:
  - `FMP_API_KEY`, `POLYGON_API_KEY`, `AIRTABLE_API_KEY`, `AIRTABLE_BASE_ID`, `AIRTABLE_TABLE_NAME`

### GitHub Workflow
- 위치: `.github/workflows/daily_scan.yml`
- 스케줄: 평일 UTC 21:00 (= 미 동부 16:00 EST / 17:00 EDT, 즉 장마감 후)
- 수동 트리거: GitHub Actions UI → `Daily US Stock Scanner` → `Run workflow`
- 실행 시간: 약 25~45분 (성능 개선 적용 시 12~20분)

### USsuperpick 코드 핵심 라인
- `mark.py:114-238` — `calculate_growth_rates_fmp()`: 분기/연간 성장률 계산
- `mark.py:240-314` — `get_stock_data()`: Polygon 가격 조회
- `mark.py:316-329` — `get_stock_details()`: Polygon 종목 상세
- `mark.py:331-444` — `update_airtable()`: 레코드 record dict + Airtable 업데이트
- `us_minervini_scanner_v2.py:74-127` — `get_all_stocks()`: 종목 리스트
- `us_minervini_scanner_v2.py:388-473` — `apply_minervini_criteria()`: 8조건 검증
- `us_minervini_scanner_v2.py:513-705` — `sync_to_airtable()`: 스마트 동기화

### markmarkmark 코드 핵심 라인
- `src/types.ts:6-196` — Stock 인터페이스
- `src/types.ts:15` — `시장구분: 'KOSPI' | 'KOSDAQ'` (확장 대상)
- `src/data/dataService.ts:88-367` — `fetchDataFromAirtable()`: 한국주식 fetch
- `src/utils/stockEvaluator.ts` — 평가 알고리즘 (양쪽 공통이 되어야 함)
- `src/utils/stockFilter.ts` — 필터 로직 (양쪽 공통)
- `src/components/StockDashboard.tsx` — 메인 대시보드 (Phase 3에서 분리)
- `src/App.tsx:97-118` — 라우팅 (Phase 3에서 미국 라우트 추가)

---

## 🗒 그동안의 대화 요약 (의사결정 트레일)

1. **현재 폴더 학습** → USsuperpick 구조와 동작 흐름 파악
2. **GitHub Actions 실행 방법** → 수동 트리거 가능, scanner_v2 → mark.py 순차 실행
3. **두 스크립트 동시 처리?** → No, 순차 실행. mark.py가 scanner_v2의 결과(Airtable 마크미너비니 뷰)에 의존
4. **성능 개선 제안** → 4가지 가성비 좋은 항목 (Phase 1 1-3에 포함)
5. **Airtable vs Sheets** → 현재 케이스에서 Airtable 유지가 정답 (마이그레이션 비용 > 이득)
6. **Airtable 필드 생성 가능?** → ✅ Metadata API로 가능 (PAT 필요)
7. **중·일 주식 확장** → FMP/Polygon만으로는 어려움, ADR 활용이 가성비 최선
8. **markmarkmark 통합** → 옵션 A/B/C 비교 → 옵션 C 채택
9. **옵션 C의 위험** → 사용자가 우려 표명 ("한국 수정 시 미국 빠뜨림")
10. **깃 히스토리 분석** → 1년치 61커밋 분석, 옵션 C가 사용자 패턴에 가장 적합 검증
11. **본 인계 문서 작성** (1차)
12. **Q1~Q3 결정 완료 + 한국 영향 차단 전략 추가** ← 현재

---

## ✅ 의사결정 트레일 (요약)

- 아키텍처: **옵션 C (공유 우선)**
- 미국 Airtable: **별도 Base** (`appAh82iPV3cH6Xx5` / `tbljCB2CnDe2eWB3M` / `viwtY7XrICnpAgyvY`)
- 답안지/시크릿: **미국 안 들어감**, 한국 컨텐츠 그대로
- NavigationBar: `슈퍼픽 한국주식` / `슈퍼픽 미국주식` / `월클답안지` / `시크릿리포트`
- 미국 특유 기능: **추후 고려** (지금은 한국과 동일 수준)
- 작업 브랜치: `us-stock` (markmarkmark 작업 시)

---

이 문서를 기반으로 **Phase 1부터 즉시 시작**. 새 세션은 위 "🚀 새 세션이 시작할 때" 섹션의 6단계를 그대로 실행하면 됩니다.
