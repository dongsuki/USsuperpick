@echo off
REM USsuperpick AI Analyzer 로컬 실행
REM Windows Task Scheduler가 평일 KST 07:30에 호출 (mark.py가 KST 06:46에 끝남)
REM
REM 환경변수는 'setx' 명령어로 사용자 단위 영구 등록되어 있어야 함:
REM   setx ANTHROPIC_API_KEY "sk-ant-..."
REM   setx FMP_API_KEY "..."
REM   setx AIRTABLE_API_KEY "pate1KcLxphDwMihn..."
REM   setx AIRTABLE_BASE_ID "appAh82iPV3cH6Xx5"

cd /d C:\Users\USER\Desktop\USsuperpick
set PYTHONIOENCODING=utf-8

if not exist logs mkdir logs

REM 타임스탬프 (YYYYMMDD_HHMMSS)
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set dt=%%I
set TS=%dt:~0,8%_%dt:~8,6%
set LOG=logs\ai_analyzer_%TS%.log

echo ========================================== >> "%LOG%"
echo [%date% %time%] AI Analyzer start (auto) >> "%LOG%"
echo ========================================== >> "%LOG%"

REM --limit 50: 자동 실행 일일 안전판 (대상 뷰 = 종합점수 50+ 약 168종목)
REM 첫 백필은 약 3~4일 자동 진행, 이후엔 신규 진입 0~5개만 잡혀서 limit 사실상 무관
REM 한 번에 빠르게 백필하려면: python -m ai_analyzer.analyze --auto --limit 0
python -m ai_analyzer.analyze --auto --limit 50 >> "%LOG%" 2>&1
set EXIT_CODE=%ERRORLEVEL%

echo ========================================== >> "%LOG%"
echo [%date% %time%] Done. exit=%EXIT_CODE% >> "%LOG%"
echo ========================================== >> "%LOG%"

exit /b %EXIT_CODE%
