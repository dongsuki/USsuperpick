# USsuperpick

미국 주식 시장용 Mark Minervini 스타일 투자 스캐너 도구 모음

## 📋 프로젝트 소개

이 레포지토리는 Mark Minervini의 투자 전략을 기반으로 한 미국 주식 스캐너 도구를 제공합니다.

## 📦 포함된 스크립트

### 1. `mark.py`
- Airtable에서 티커 목록을 가져와 재무 데이터를 업데이트하는 스크립트
- 주요 기능:
  - EPS, 매출액, 영업이익, NPM 성장률 계산
  - 분기별/연간 재무 데이터 자동 수집
  - Airtable 자동 업데이트

### 2. `us_minervini_scanner_v2.py`
- Mark Minervini의 8가지 조건을 기반으로 미국 주식을 스캔하는 도구
- 주요 기능:
  - RS(상대 강도) 등급 계산
  - Minervini 8가지 조건 자동 검증
  - Airtable 연동 지원
  - 배치 처리로 빠른 성능

## 🚀 설치 방법

### 1. 레포지토리 클론
```bash
git clone https://github.com/dongsuki/USsuperpick.git
cd USsuperpick
```

### 2. 필요한 패키지 설치
```bash
pip install -r requirements.txt
```

## 🔑 API 키 설정

스크립트 실행 전에 다음 API 키들을 환경 변수로 설정해야 합니다:

### 필요한 API 키

1. **FMP API 키** (Financial Modeling Prep)
   - https://financialmodelingprep.com/ 에서 발급
   - 환경 변수: `FMP_API_KEY`

2. **Polygon API 키** (mark.py 사용 시)
   - https://polygon.io/ 에서 발급
   - 환경 변수: `POLYGON_API_KEY`

3. **Airtable API 키** (선택사항 - Airtable 연동 시)
   - https://airtable.com/ 에서 발급
   - 환경 변수: `AIRTABLE_API_KEY`, `AIRTABLE_BASE_ID`, `AIRTABLE_TABLE_NAME`

### 환경 변수 설정 방법

**Windows (PowerShell)**
```powershell
$env:FMP_API_KEY="your_api_key_here"
$env:POLYGON_API_KEY="your_polygon_key_here"
$env:AIRTABLE_API_KEY="your_airtable_key_here"
$env:AIRTABLE_BASE_ID="your_base_id_here"
$env:AIRTABLE_TABLE_NAME="트레이더의 선택"
```

**Linux/Mac (Bash)**
```bash
export FMP_API_KEY="your_api_key_here"
export POLYGON_API_KEY="your_polygon_key_here"
export AIRTABLE_API_KEY="your_airtable_key_here"
export AIRTABLE_BASE_ID="your_base_id_here"
export AIRTABLE_TABLE_NAME="트레이더의 선택"
```

또는 `config.example.txt` 파일을 참고하여 코드 내에서 직접 설정할 수 있습니다.

## 💻 사용 방법

### mark.py 실행
```bash
python mark.py
```

### us_minervini_scanner_v2.py 실행
```bash
python us_minervini_scanner_v2.py
```

## 📊 Minervini 8가지 조건

1. ✅ RS 등급 70 이상
2. ✅ 현재가 > 150일 이평선
3. ✅ 현재가 > 200일 이평선
4. ✅ 150일 이평선 > 200일 이평선
5. ✅ 50일 이평선 > 150일 이평선
6. ✅ 200일 이평선 상승 추세
7. ✅ 현재가가 52주 저가 대비 30% 이상 상승
8. ✅ 현재가가 52주 고가의 75% 이상

## 📝 라이선스

이 프로젝트는 개인적인 투자 분석 목적으로 만들어졌습니다.

## ⚠️ 면책 조항

이 도구는 투자 참고용으로만 사용해야 하며, 실제 투자 결정은 본인의 책임입니다.

