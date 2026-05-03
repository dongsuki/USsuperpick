@echo off
REM USsuperpick AI Analyzer - local runner
REM Scheduled via Windows Task Scheduler: weekdays KST 07:30 (after mark.py finishes ~06:46)
REM
REM Required env vars (set once with setx):
REM   setx ANTHROPIC_API_KEY "sk-ant-..."
REM   setx FMP_API_KEY "..."
REM   setx AIRTABLE_API_KEY "pate1KcLxphDwMihn..."
REM   setx AIRTABLE_BASE_ID "appAh82iPV3cH6Xx5"

cd /d C:\Users\USER\Desktop\USsuperpick
set PYTHONIOENCODING=utf-8

if not exist logs mkdir logs

REM Timestamp: YYYYMMDD_HHMMSS
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set dt=%%I
set TS=%dt:~0,8%_%dt:~8,6%
set LOG=logs\ai_analyzer_%TS%.log

echo ========================================== >> "%LOG%"
echo [%date% %time%] AI Analyzer start (auto) >> "%LOG%"
echo ========================================== >> "%LOG%"

REM --limit 50: daily safety cap (~168 tickers in the view with score 50+)
REM Backfill runs ~3-4 days automatically; after that only 0-5 new tickers per day
REM For fast one-time backfill: python -m ai_analyzer.analyze --auto --limit 0
python -m ai_analyzer.analyze --auto --limit 50 >> "%LOG%" 2>&1
set EXIT_CODE=%ERRORLEVEL%

echo ========================================== >> "%LOG%"
echo [%date% %time%] Done. exit=%EXIT_CODE% >> "%LOG%"
echo ========================================== >> "%LOG%"

exit /b %EXIT_CODE%
