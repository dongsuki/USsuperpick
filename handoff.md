# USsuperpick × markmarkmark 통합 작업 인계 문서 (Phase 1~5 완료)

**최종 갱신**: 2026-05-03
**작업 진행률**: Phase 1~4 main 머지 완료, Phase 5 PR #2 open 상태

---

## 🎯 프로젝트 목표

`markmarkmark` (한국주식 React 프론트엔드)에 **미국주식 대시보드를 추가**.
데이터는 `USsuperpick` (Python 스캐너)이 Airtable에 채우고, markmarkmark가 그 데이터를 읽어 렌더.

---

## 📁 프로젝트 위치

| 프로젝트 | 경로 | 역할 |
|---|---|---|
| `USsuperpick` | `C:\Users\USER\Desktop\USsuperpick` | 데이터 파이프라인 (Python) — FMP/Polygon/Yahoo → Airtable |
| `markmarkmark` | `C:\Users\USER\Desktop\markmarkmark` | UI (React/TS/Vite) — Airtable → 화면 |

GitHub:
- https://github.com/dongsuki/USsuperpick (main 브랜치)
- https://github.com/dongsuki/markmarkmark (main + phase-5-eps-trend)

---

## 🗂 Airtable 베이스 정보

### 미국주식 (USsuperpick + markmarkmark가 공유)
- **Base ID**: `appAh82iPV3cH6Xx5`
- **Table ID**: `tbljCB2CnDe2eWB3M`
- **View ID**: `viwtY7XrICnpAgyvY` (마크미너비니 뷰)
- **URL**: https://airtable.com/appAh82iPV3cH6Xx5/tbljCB2CnDe2eWB3M/viwtY7XrICnpAgyvY

### 한국주식 (markmarkmark 기존)
- markmarkmark `.env`의 `VITE_AIRTABLE_BASE_ID`, `VITE_AIRTABLE_TABLE_ID` (값은 사용자만 알고 있음)

### 답안지 / 시크릿리포트 (참고)
- 답안지 Base: `appA4t9o1QMTDZul7`
- 시크릿리포트 Base: `appJFk54sIT9oSiZy`

---

## 🔐 비밀 관리 (보안 안내)

### GitHub Secrets (USsuperpick)
GitHub Settings → Secrets and variables → Actions:
- `FMP_API_KEY` ✅ 등록됨
- `POLYGON_API_KEY` ✅
- `AIRTABLE_API_KEY` ✅
- `AIRTABLE_BASE_ID` = `appAh82iPV3cH6Xx5`
- `AIRTABLE_TABLE_NAME` = `트레이더의 선택`
- `ANTHROPIC_API_KEY` ✅ (한글명 LLM 폴백용)

### Netlify 환경변수 (markmarkmark)
- `VITE_AIRTABLE_API_KEY` (한국·미국 공용 PAT)
- `VITE_AIRTABLE_BASE_ID` (한국)
- `VITE_AIRTABLE_TABLE_ID` (한국)
- 미국 ID들은 `netlify.toml`에 박혀있음 (비시크릿이라 OK)

### 작업 중 노출된 토큰들 (사용자 주의)
이번 작업 중 채팅에 노출된 토큰들 — **rotate 권장**:
- Airtable PAT: `pate1KcLxphDwMihn.b5e7...` (필드 생성용으로 여러 번 사용)
- FMP API key: `EApxNJTRwcXOrhy2IUqSeKV0gyH8gans` (Phase 5 검증용)

→ 작업 완료 후 https://airtable.com/create/tokens, https://site.financialmodelingprep.com/developer/docs/dashboard 에서 revoke + 새 발급 → GitHub Secrets에 새 값 등록.

---

## 🏗 선택된 아키텍처: 옵션 C — 공유 우선

```
src/
├── components/
│   ├── stock-detail/             ⭐ 공통 (한국/미국 모두 사용)
│   │   ├── StockHeader.tsx       — 종목명, 시총, 적자 라벨
│   │   ├── ChartSection.tsx
│   │   ├── QuarterlyEpsChart.tsx — 통화 라벨 (Phase 5)
│   │   ├── YearlyEpsChart.tsx    — 통화 라벨
│   │   ├── QuarterlyRevenueChart.tsx — 통화 라벨
│   │   ├── EpsTrendCard.tsx (신규, 미국 전용 isUSMarket 체크)
│   │   └── ...
│   ├── stock-views/              ⭐ 공통
│   │   ├── StockListTable.tsx    — 한국/미국 모두 (한글명, 적자 라벨)
│   │   ├── StockRankingTable.tsx — 동
│   │   └── ...
│   ├── ui/StockFilter.tsx        ⭐ 공통 (선행 PEG 필터 추가)
│   ├── StockDashboard.tsx        ⭐ 공통 (marketType prop으로 분기)
│   ├── AnswerSheet.tsx           — 한국 전용 (답안지)
│   └── SecretReport.tsx          — 한국 전용
├── data/
│   └── dataService.ts            ⭐ fetchStockData(한국) + fetchUSStockData(미국)
├── utils/
│   ├── stockEvaluator.ts         ⭐ 공통 평가 로직
│   ├── stockFilter.ts            ⭐ 공통 필터 (선행 PEG 필터 추가)
│   └── stockDisplay.ts (신규)    ⭐ getDisplayName, isUSMarket, isLossMaking, getCurrencyLabel
└── types.ts                      ⭐ Stock 인터페이스 (옵셔널 필드로 확장)
```

### 절대 규칙 3가지 (옵션 C 보호)
1. **평가 로직(`utils/`)은 무조건 공통** — `stockEvaluator.ts`, `stockFilter.ts` 시장별 분리 금지
2. **차트/테이블 컴포넌트는 무조건 공통** — `stock-detail/*`, `stock-views/*`
3. **시장 전용은 `isUSMarket()` 또는 marketType prop으로 분기**

### 핵심 헬퍼 (utils/stockDisplay.ts)
- `getDisplayName(stock)` — 한글명 우선, 영문 fallback
- `isUSMarket(stock)` — NASDAQ/NYSE/AMEX 체크
- `getDisplayTicker(stock)` — 미국 ticker
- `getUSSubLabel(stock)` — "AAPL · 기술" 형식
- `isLossMaking(stock)` — 최신분기 EPS < 0
- `getReportedCurrency(stock)` — FMP reportedCurrency
- `getCurrencyLabel(stock)` — "(USD)" 또는 "(TWD · 본국 통화)" 차트용

---

## 📊 데이터 파이프라인 흐름 (USsuperpick)

```
[GitHub Actions: 평일 UTC 21:00 자동 + 수동 트리거]
  ↓
1) us_minervini_scanner_v2.py (~14분)
   ├ FMP /stock-screener → NASDAQ + NYSE 5,000~8,000 종목
   ├ FMP /historical-price-full → 가격 400일치
   ├ ThreadPoolExecutor 6 workers
   ├ 모멘텀 점수 계산 → RS 등급 (전체 모집단)
   ├ 투자 후보 필터 (시총≥$1억, 거래량≥10만, 가격≥$5)
   ├ Minervini 8조건
   ├ 이동평균 존 계산 (Phase 4-A1)
   │   - MA 3/5/8/10/15/20/33/50/100 계산
   │   - 8개 zone boolean (3일선 위/3존/8존/15존/20존/33존/50존/슈퍼존)
   └ Airtable Update/Create/Delete 동기화
       (record에 zone 8개 필드 포함)
  ↓
2) sleep 60s
  ↓
3) mark.py (~32분, Yahoo 호출 추가로 이전보다 느려짐)
   ├ Airtable "마크미너비니" 뷰에서 티커 가져오기
   ├ 각 티커마다:
   │   ├ Polygon 시장상태 + 가격 데이터
   │   ├ Polygon 종목 상세 (name, market_cap, primary_exchange)
   │   ├ FMP /income-statement (분기 8 + 연간 6)
   │   │   - reportedCurrency 추출 (Phase 5 ADR 통화)
   │   │   - revenue raw, operatingIncome, netIncome
   │   │   - EPS 계산: netIncome / weightedAverageShsOut
   │   │   - 영업이익률, 순이익률, NPM 등 비율
   │   ├ FMP /key-metrics (ROE, PER, PEG)
   │   ├ Yahoo earnings_trend (yahooquery, Phase 5)
   │   │   - 4 카테고리 × 5 시점 EPS Trend
   │   │   - +1y까지 EPS 추정 (USD per ADS, 통화 일관성 ✅)
   │   ├ Forward PE/PEG 직접 계산 (단년 성장률 기준)
   │   ├ 한글명 (Phase 4-A2)
   │   │   - Airtable 캐시 확인 → 있으면 사용 (LLM 호출 0)
   │   │   - 네이버 stock api 크롤링
   │   │   - 폴백: Claude Haiku 음역 (ANTHROPIC_API_KEY 있을 때만)
   │   ├ 최신분기 표기 ('YYYY-Qn')
   │   └ 보고통화 (reportedCurrency)
   └ Airtable update — 약 105개 필드
```

---

## 📋 Airtable 필드 카탈로그 (총 ~104개)

### 그룹 1: 기본 정보 (scanner_v2가 채움)
- 티커, 종목명, 현재가, 등락률, 거래량, 시가총액, 52주 신고가 비율, RS순위, 재료명

### 그룹 2: 한글명 + 메타 (mark.py)
- **한글명** (네이버 + LLM 폴백)
- **최신분기** ('YYYY-Qn' 형식)
- **보고통화** ('USD' / 'TWD' / 'JPY' 등)
- 거래소 정보, 업데이트 날짜, 분류

### 그룹 3: EPS 값 (mark.py income-statement)
- EPS_최신분기, 전분기, 전전분기, 4분기전, 5분기전, 6분기전, 7분기전, 8분기전 (8개)
- EPS_1년, 2년, 3년, 4년, 5년, 6년 (6개)

### 그룹 4: 성장률 (mark.py 직접 계산)
- EPS성장률 분기/연간 (3+3 = 6개) + 날짜 (6개)
- 영업이익성장률 분기/연간 (6개) + 날짜 (6개)
- 매출액성장률 분기/연간 (6개) + 날짜 (6개)
- NPM성장률 분기 4개 + 연간 3개 = 7개 (Phase 4 q4 추가) + 날짜 (6개)

### 그룹 5: Phase 1 신규 (38개)
- 매출액 raw 분기 8개
- 영업이익률(%) raw 분기 3 + 연간 3 = 6개
- 순이익률 raw 분기 8 + 연간 3 = 11개
- ROE 분기 3 + 연간 3 = 6개
- PER 분기 3 + 연간 3 = 6개
- PEG_최신분기 (1개, 직접 계산 폴백 포함)

### 그룹 6: Phase 4 이동평균 존 (8개, Checkbox)
- 3일선 위, 3존, 8존, 15존, 20존, 33존, 50존, 슈퍼존

### 그룹 7: Phase 5 EPS Trend (20개, Yahoo)
- 현재분기 / 다음분기 / 현재연도 / 내년 × 현재추정 / 7일전 / 30일전 / 60일전 / 90일전

### 그룹 8: Phase 5 Forward (4개, Yahoo)
- 선행PER_올해, 선행PER_내년 (FMP +2y는 ADR 통화 불일치로 제외)
- 선행PEG_올해, 선행PEG_내년

(선행PER_내후년, 선행PEG_내후년 필드는 만들었으나 사용자 결정으로 안 씀 — 빈 채로 유지)

---

## ✅ 완료된 작업 (Phase 1~5)

### Phase 1: USsuperpick 데이터 보강
**상태**: ✅ 완료, main 머지됨
- mark.py에 FMP `/key-metrics` 호출 추가 (ROE, PER, PEG)
- income-statement에서 raw 값 추출 (revenue, 영업이익률, 순이익률)
- Airtable에 신규 38개 필드 생성
- PEG 직접 계산 폴백 (FMP가 PEG 안 줄 때 PER/EPS성장률 사용)

### Phase 2: markmarkmark 데이터 레이어
**상태**: ✅ 완료, main 머지됨
- types.ts: 시장구분 union NASDAQ/NYSE/AMEX 확장, USStock 옵셔널 필드
- dataService.ts: `fetchUSStockData()` 신규 함수
- 미국 환경변수 (Base/Table/View ID)는 `netlify.toml`에 박힘 (비시크릿)

### Phase 3: UI 라우트 분기
**상태**: ✅ 완료, main 머지됨 (PR #1)
- App.tsx: 라우트 `/us`, `/suikasak72978566/us` 추가
- StockDashboard.tsx: marketType prop ('kr'|'us', default 'kr')
- NavigationBar: "슈퍼픽" → "슈퍼픽 한국주식" + "슈퍼픽 미국주식" 추가
- 한국 페이지 회귀 0

### Phase 4: 한글명 + 존 + 한국식 색상
**상태**: ✅ 완료, main 머지됨
- A1: scanner_v2.py에 이동평균 존 계산 추가 (한국 ma_zone_scanner.py 정의 동일)
- A2: mark.py에 네이버 한글명 크롤링 + Claude Haiku LLM 폴백
- 188개 종목 한글 음역 일괄 적용 (apply_korean_translations.py)
- markmarkmark UI: 한글명 우선 표시, 티커·섹터 보조 라벨, 시가총액 USD 형식
- 섹터 영→한 매핑 (Technology→기술 등 11개)

### Phase 5: EPS Trend + Forward PE/PEG + 시각 개선
**상태**: ⏳ phase-5-eps-trend 브랜치, **PR #2 open**
- yahooquery 도입
- EPS Trend 20개 + Forward PE/PEG 4개 데이터
- EpsTrendCard 컴포넌트 (markmarkmark 톤 디자인)
- 한국식 색상 (상향=빨강, 하향=파랑) — 단계별 변화 비교
- 선행 PEG 필터 (재무지표 섹션, 올해/내년)
- 한국식 시가총액 표기 ("2조 5천억 달러")
- 적자 종목 라벨 (EPS_최신분기 < 0 조건, 빨간 배지)
- 최신분기 필드 (Airtable Look up 대체)
- ADR 차트 통화 라벨 ("(TWD · 본국 통화)" 표시)
- 보고통화 필드 + 데이터 누락 시 라벨 미표시 안전 처리

### 데이터 정확성 검증 (Phase 5 일환)
**상태**: ✅ 완료
- FMP API 직접 호출 검증 (TSM/MFG/SMFG/TTE/NVDA/AAPL)
- ADR은 reportedCurrency가 본국 통화 (TWD/JPY)
- 야후만 사용 결정 (옵션 A) 정합 검증됨
- 점수 계산은 % 비율 위주라 통화 영향 0 — **재무 점수 정확성 보장**
- PER만 FMP 자체 계산이라 본국 시장 기준 가능성 (점수와 별개)

---

## 🚧 진행 중 / 미완료 / 결정 보류

### PR #2 머지 결정 보류 중
🔗 https://github.com/dongsuki/markmarkmark/pull/2

머지 시:
- main에 Phase 5 모든 변경 적용
- Netlify production 자동 배포 (~3분)
- 한국 사용자 사이트에 미국 페이지 EPS Trend / 선행 PEG 필터 / 한국식 시총 / 적자 라벨 / ADR 통화 라벨 모두 적용
- 한국 페이지 영향 없음 (isUSMarket 체크)

### 진행 중인 GitHub Actions 워크플로우
- Run ID: `25272264871` (UTC 06:44 시작)
- 보고통화(reportedCurrency) 필드 채우는 첫 워크플로우
- 끝나면 ADR 종목들 차트에 "(TWD · 본국 통화)" 자동 표시
- 다음 세션 시작 시 워크플로우 결과 확인 필요

### 보안 후속 작업
- Airtable PAT `pate1KcLxphDwMihn...` revoke
- FMP API key `EApxNJTRwcXOrhy2IUqSeKV0gyH8gans` rotate
- GitHub Secrets에 새 값 등록

---

## 📝 새 세션 시작 시 액션

### 1단계: 워크플로우 결과 확인 (5분)
```bash
gh run view 25272264871 --repo dongsuki/USsuperpick --json conclusion
```
- conclusion이 success면 보고통화 데이터 채워짐
- 검증: PAT으로 Airtable fetch, TSM/MFG는 'TWD'/'JPY', NVDA는 'USD' 확인

### 2단계: PR #2 시각 검증 (10분)
🔗 https://deploy-preview-2--markmarkmark.netlify.app/us
- ADR 종목 클릭 → 차트 제목에 "(TWD · 본국 통화)" 표시
- 미국 본토 종목 → "(USD)"
- 한국 페이지(`/`)에는 통화 라벨 없음
- EPS Trend 색상 단계별 변화 (한국식 빨강/파랑)
- 적자 종목에 빨간 [적자] 배지

### 3단계: PR #2 머지 결정
**OK이면**:
```bash
gh pr merge 2 --repo dongsuki/markmarkmark --merge
```
- 자동으로 production 배포

**문제 발견 시**: 추가 수정 → 새 commit → preview 재검증

### 4단계: 보안 정리
- Airtable PAT, FMP API key revoke
- 새 값 GitHub Secrets에 등록

### 5단계: handoff.md에 머지 완료 기록 + 다음 작업 정리

---

## 🔮 잠재적 다음 작업 (사용자 결정 필요)

### A. ADR 데이터 USD 변환 (작업 4~6h, 정확도 보장 어려움)
- 환율 API 추가 (FMP forex 또는 다른 소스)
- ADR ratio 매핑 테이블 (TSM 1:5, MFG 1:1/5 등)
- 본국 통화 EPS → USD per ADS 변환
- → 사용자 결정: **현재 야후만 사용으로 충분, 보류**

### B. Phase 5 추가 지표 (시간 여유 있을 때)
- 매출 추정 변화 (Revenue Estimate Trend)
- 분석가 EPS 수정 (EPS Revisions: 상향/하향 카운트)
- 5년 평균 PEG (Yahoo 표준)
- Forward PBR (BVPS 추정 어려움)

### C. 디자인 개선
- ADR 종목 종목명 옆에 국기 아이콘 (🇹🇼 TSM, 🇯🇵 MFG)
- 한글명 LLM 폴백 일관성 검토 (188개 매핑 후 신규 종목만 LLM)
- 다크모드?

### D. 한국 페이지 영향 0 보장
- E2E 테스트로 한국 페이지 회귀 자동 검증
- 머지 전 자동 빌드 + 한국 라우트 스모크 테스트

### E. 데이터 품질 개선
- 매출 0 임상 단계 바이오 처리 (현재 평가 보류 → 정상 동작)
- 적자 종목 PE/PEG (의미 없으나 표시됨, 사용자 자체 해석)
- 분석가 추정 신뢰도 표시 (numberOfAnalysts 활용)

### F. 자동화 개선
- 워크플로우 cron을 한국시간 기준 정확히 (서머타임 대응)
- 실패 알림 (Slack/이메일)
- 성능 개선 적용 (이전 handoff에서 제안한 sleep 제거 등)

---

## 🛡 절대 지킬 것 (옵션 C 보호)

작업 중 다음을 절대 하지 말 것:
1. ❌ `utils/stockEvaluator.ts`, `utils/stockFilter.ts`를 시장별 복사 금지
2. ❌ 차트 컴포넌트(`stock-detail/*`)를 한국용/미국용 복제 금지
3. ❌ "임시로 따로 만들고 나중에 통합" 금지 (실제로는 통합 안 됨)
4. ❌ 한국 평가 로직에 미국에 없는 필드를 옵셔널 체크 없이 직접 참조 금지
5. ✅ "이게 다른 시장에도 적용되나?" 자문 → 50%+ 가능성이면 공통 영역에 배치

---

## 📚 핵심 의사결정 트레일

### 왜 옵션 C? (1년 git 분석 결과)
- 평가 시스템 변경 6회/년 → utils/ 공통이어야 양쪽 자동 적용
- 한국 전용 필터/UI 8회/년 → kr/ 분리 필요
- 옵션 A(토글)는 분기문 폭발, 옵션 B(완전분리)는 동기화 누락 위험
- 옵션 C가 사용자 변경 패턴에 가장 적합

### 왜 야후만 (Phase 5 Forward 데이터)?
- FMP analyst-estimates는 +5y까지 주지만 ADR이 본국 통화로 보고
- 통화 매칭 (환율 + ADR ratio) 작업 4~6h, 정확도 보장 X
- 분석가 추정 자체가 1년 후도 변동 큰데 2년 후는 더 부정확
- 야후는 자동 USD per ADS 변환 → 통화 일관성 100%
- → +2y 빼고 +1y까지만 사용

### 왜 한글명 하이브리드 (네이버 + Claude API)?
- 네이버 단독: 42% 채움률 (대형주만)
- Claude API 비용: 신규 종목당 ~20원, 월 600원 미만
- 캐싱: Airtable에 이미 있으면 LLM 호출 0
- 188개 일괄 적용으로 1차 채움 100%, 이후 신규만 LLM

### 왜 한국식 색상?
- 한국 사용자 직관 (빨강=상승=긍정, 파랑=하락=부정)
- EPS Trend 단계별 변화 비교 (사용자 재요청)
- PEG도 동일 컨벤션 (저평가=빨강, 고평가=파랑)

### 왜 적자 라벨 종목명 옆?
- 사용자 의도: 재무점수 높은데 EPS 음수인 종목 시각 경고
- 종목명 옆이 가장 직관적
- 한국·미국 공통 적용 (한국 적자 종목도 표시)

### 데이터 정확성 — 점수 영향 없음
- 모든 성장률, 마진, 비율 지표는 통화 무관 (cancel out)
- ADR EPS/매출 절대값만 본국 통화 (차트 표시 단위 차이)
- PER만 FMP 자체 계산 (점수에 직접 영향 X, 화면 표시만)
- 사용자 검증으로 OK 판정

---

## 🗒 작업 요약 (시간순)

1. 폴더 학습 + 워크플로우 분석
2. ADR/중국·일본 주식 확장성 검토 (보류)
3. markmarkmark 통합 옵션 비교 → 옵션 C 채택
4. handoff.md 1차 작성
5. 미국 Airtable Base ID 확인 (`appAh82iPV3cH6Xx5`)
6. Phase 1 데이터 보강 (38개 필드)
7. Phase 2 데이터 레이어
8. Phase 3 UI 분기 + PR #1 → main 머지
9. 한글명 하이브리드 (188개 일괄 + LLM 자동화)
10. Phase 4 한글명 + 존 + 색상
11. ADR 통화 검증 → 야후 단독 결정
12. Phase 5 EPS Trend + Forward PE/PEG
13. EPS Trend 단계별 색상 비교
14. 한국식 시가총액 + 적자 라벨
15. ADR 차트 통화 라벨 + 보고통화 필드
16. handoff.md 총정리 (현재)

---

## 🔧 코드 핵심 라인 참조

### USsuperpick
- `mark.py:9-21` — Anthropic / yahooquery 옵셔널 import
- `mark.py:115-144` — get_korean_name_llm (Claude Haiku 폴백)
- `mark.py:146-181` — get_yahoo_eps_trend
- `mark.py:184-201` — get_fmp_analyst_estimates_annual (현재 사용 안 함)
- `mark.py:204-273` — calculate_forward_valuations
- `mark.py:339-371` — get_korean_name_naver
- `mark.py:373-394` — get_key_metrics_fmp
- `mark.py:397-562` — calculate_growth_rates_fmp (모든 raw + 성장률 + reportedCurrency + latest_quarter)
- `mark.py:660-880` — update_airtable (record dict 105개 필드)
- `us_minervini_scanner_v2.py:178-240` — calculate_technical_indicators + ma_zones
- `us_minervini_scanner_v2.py:242-298` — _calculate_ma_zones (8개 zone)
- `us_minervini_scanner_v2.py:516-528` — apply_minervini_criteria columns_order (zone 8개 포함)
- `us_minervini_scanner_v2.py:660-740` — sync_to_airtable (record_data with zone fields)
- `create_airtable_fields.py` — 75개 필드 정의 (Phase 1-5 누적)
- `apply_korean_translations.py` — 188개 한글 음역 일괄 적용 스크립트 (1회성, 향후 신규 종목 추가 시 재사용)

### markmarkmark (phase-5-eps-trend 브랜치)
- `src/types.ts:6-50` — Stock 인터페이스 (시장구분 union 확장 + 옵셔널 필드)
- `src/types.ts:130+` — Phase 5 EPS Trend 24개 필드
- `src/data/dataService.ts:10-13` — 미국 Airtable 환경변수 (netlify.toml에서)
- `src/data/dataService.ts:907+` — fetchUSStockData (전체 매핑)
- `src/utils/stockDisplay.ts` — 헬퍼 모음 (getDisplayName, isUSMarket, isLossMaking, getCurrencyLabel 등)
- `src/components/StockDashboard.tsx:18-23` — marketType prop
- `src/components/StockDashboard.tsx:60-65` — fetch 분기
- `src/components/stock-detail/EpsTrendCard.tsx` — Phase 5 신규
- `src/components/stock-detail/StockHeader.tsx` — 한국식 시총, 적자 라벨, ADR 통화 라벨
- `src/components/stock-detail/QuarterlyEpsChart.tsx` — 통화 라벨
- `src/components/stock-detail/YearlyEpsChart.tsx` — 통화 라벨
- `src/components/stock-detail/QuarterlyRevenueChart.tsx` — 통화 라벨
- `src/components/stock-views/StockListTable.tsx` — 적자 라벨, 한글명
- `src/components/stock-views/StockRankingTable.tsx` — 동
- `src/components/ui/StockFilter.tsx` — 선행 PEG 필터 추가
- `src/utils/stockFilter.ts` — forwardPegThisYear/NextYear 매핑
- `src/App.tsx` — `/us`, `/suikasak72978566/us` 라우트 + NavigationBar 메뉴

### Netlify 환경변수
- `netlify.toml [build.environment]` — 미국 Airtable Base/Table/View ID 박혀있음

---

## 📂 보조 파일

### USsuperpick
- `apply_korean_translations.py` — 1회성, 향후 신규 종목 한글명 추가용
- `create_airtable_fields.py` — Airtable Metadata API로 필드 일괄 생성

### 임시 파일 (gitignore)
- `_korean_names_pending.json` (작업 중 산출물)

### 새 종목 추가 시 운영
1. scanner_v2가 새 종목 통과시키면 mark.py가 자동 처리
2. 한글명: 네이버에 있으면 자동, 없으면 Claude Haiku 폴백
3. 보고통화: FMP에서 자동 추출
4. 모든 신규 필드 자동 채움

### 새 필드 추가 절차
1. `create_airtable_fields.py` `FIELDS_TO_CREATE`에 정의 추가
2. PAT 환경변수 설정 + `python create_airtable_fields.py` 실행 (이미 존재 필드는 skip)
3. mark.py 또는 scanner_v2.py에서 record dict에 매핑 추가
4. markmarkmark types.ts + dataService.ts에 매핑
5. 워크플로우 트리거 후 검증

---

## 🚦 새 세션 첫 액션 체크리스트

```
[ ] 1. gh run view 25272264871 — 워크플로우 success 확인
[ ] 2. PAT으로 Airtable fetch — TSM 보고통화 'TWD', NVDA 'USD' 검증
[ ] 3. https://deploy-preview-2--markmarkmark.netlify.app/us 시각 검증
       - ADR 종목 차트 통화 라벨 '(TWD · 본국 통화)' 표시
       - 적자 종목 빨간 [적자] 배지
       - 시가총액 한국식
       - EPS Trend 단계별 색상
       - 선행 PEG 필터
[ ] 4. 한국 페이지(/) 회귀 검증 — 변화 없음 확인
[ ] 5. PR #2 머지 결정
       gh pr merge 2 --repo dongsuki/markmarkmark --merge
[ ] 6. 머지 후 Netlify production 배포 확인 (~3분)
[ ] 7. 한국 사용자 사이트에서 미국 페이지 정상 동작 확인
[ ] 8. PAT/FMP key revoke + 새 발급 → GitHub Secrets 갱신
[ ] 9. handoff.md에 머지 완료 + 차후 작업 갱신
```

---

이 문서를 기반으로 새 세션이 모든 컨텍스트 파악 가능. PR #2 머지하면 Phase 5 완료.
