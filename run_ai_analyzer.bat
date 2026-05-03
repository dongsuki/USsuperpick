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

python -m ai_analyzer.analyze --auto >> "%LOG%" 2>&1
set EXIT_CODE=%ERRORLEVEL%

echo ========================================== >> "%LOG%"
echo [%date% %time%] Done. exit=%EXIT_CODE% >> "%LOG%"
echo ========================================== >> "%LOG%"

exit /b %EXIT_CODE%
