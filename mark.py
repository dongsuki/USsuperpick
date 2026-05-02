import os
import requests
from datetime import datetime, time as dtime
from airtable import Airtable
import time
from typing import Dict, List, Optional, Tuple

# Anthropic Claude (한글명 LLM 폴백) — optional dependency
try:
    from anthropic import Anthropic
    _anthropic_client: Optional[Anthropic] = (
        Anthropic() if os.getenv('ANTHROPIC_API_KEY') else None
    )
except ImportError:
    _anthropic_client = None

# === API 키 설정 ===
# 환경 변수에서 API 키를 가져옵니다.
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY", "YOUR_POLYGON_API_KEY")
FMP_API_KEY = os.getenv("FMP_API_KEY", "YOUR_FMP_API_KEY")
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY", "YOUR_AIRTABLE_API_KEY")

# === Airtable 설정 ===
SOURCE_BASE_ID = os.getenv("AIRTABLE_BASE_ID", "YOUR_BASE_ID")
TARGET_BASE_ID = os.getenv("AIRTABLE_BASE_ID", "YOUR_BASE_ID")
SOURCE_TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME", "트레이더의 선택")
SOURCE_VIEW_NAME = "마크미너비니"
TARGET_TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME", "트레이더의 선택")

def get_tickers_from_airtable() -> List[str]:
    """Airtable에서 티커 목록 가져오기"""
    try:
        airtable = Airtable(SOURCE_BASE_ID, SOURCE_TABLE_NAME, AIRTABLE_API_KEY)
        records = airtable.get_all(view=SOURCE_VIEW_NAME)
        
        tickers = []
        for record in records:
            ticker = record['fields'].get('티커')
            if ticker:
                tickers.append(ticker)
                
        print(f"Airtable에서 {len(tickers)}개의 티커를 불러왔습니다.")
        return tickers
        
    except Exception as e:
        print(f"티커 목록 조회 중 에러 발생: {str(e)}")
        return []

def calculate_eps(net_income: float, shares: float) -> Optional[float]:
    """순이익과 주식수로 EPS 직접 계산"""
    try:
        if not net_income or not shares or shares <= 0:
            return None
        return net_income / shares
    except (ValueError, TypeError, ZeroDivisionError) as e:
        print(f"EPS 계산 중 에러: {str(e)}")
        return None

def find_matching_quarter_data(current_data: Dict, financials: List[Dict]) -> Optional[Dict]:
    """Calendar Year와 Period 기준으로 전년 동기 데이터 찾기"""
    try:
        current_year = int(current_data.get('calendarYear', 0))
        current_period = current_data.get('period', '')
        target_year = current_year - 1
        
        for quarter in financials:
            if (int(quarter.get('calendarYear', 0)) == target_year and 
                quarter.get('period', '') == current_period):
                return quarter
                
    except Exception as e:
        print(f"분기 매칭 중 에러 발생: {str(e)}")
    
    return None

def safe_growth_rate(current: float, previous: float) -> Optional[float]:
    """안전하게 성장률을 계산"""
    try:
        if current is None or previous is None:
            return None
            
        current = float(current)
        previous = float(previous)
        
        if previous == 0:
            return None
            
        return ((current - previous) / abs(previous)) * 100
            
    except (ValueError, TypeError) as e:
        print(f"성장률 계산 중 에러: {str(e)}")
        return None

def get_financials_fmp(ticker: str, period: str = 'quarter') -> List:
    """FMP API를 사용하여 재무데이터 조회"""
    url = f"https://financialmodelingprep.com/api/v3/income-statement/{ticker}"
    params = {
        'apikey': FMP_API_KEY,
        'period': period,
        'limit': 20 if period == 'quarter' else 5
    }
    
    try:
        print(f"\n재무데이터 요청: {ticker} ({period})")
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            financials = response.json()
            print(f"재무데이터 수신 성공: {ticker} (데이터 수: {len(financials)})")
            
            if not financials:
                print(f"재무데이터 없음: {ticker}")
                return []
                
            return sorted(financials, key=lambda x: x.get('date', ''), reverse=True)
        else:
            print(f"재무데이터 조회 실패 ({ticker}): {response.status_code}")
            return []
    except Exception as e:
        print(f"재무데이터 조회 중 에러 발생 ({ticker}): {str(e)}")
        return []

def get_korean_name_llm(ticker: str, english_name: str) -> Optional[str]:
    """Claude Haiku로 한글 음역 생성 (네이버 폴백용).

    회사명을 음역(번역 X)해서 한글로 반환. 약어/심볼은 그대로.
    """
    if not _anthropic_client or not english_name:
        return None
    try:
        prompt = (
            "다음 미국 주식 회사명을 한국어로 음역해줘.\n\n"
            "규칙:\n"
            "- 번역 금지, 발음대로 음역만\n"
            "- 결과만 출력 (설명/따옴표/공백 없음)\n"
            "- 약어(2~4자)는 그대로 (예: AAR → AAR, TSMC → TSMC)\n"
            "- 회사명 접미사(Inc., Corp., Ltd., Co., plc, S.A. 등)는 제외\n"
            "- 공식 한국어 표기가 있으면 그것 사용 (예: 애플, 구글, 마이크로소프트)\n\n"
            f"회사명: {english_name}\n"
            f"티커: {ticker}\n\n"
            "한글:"
        )
        response = _anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=50,
            messages=[{"role": "user", "content": prompt}],
        )
        result = response.content[0].text.strip()
        # 한글 1자라도 포함되거나 ticker 그대로면 OK
        if result and (any('가' <= ch <= '힣' for ch in result) or result.upper() == ticker.upper()):
            return result[:50]
        return None
    except Exception as e:
        print(f"LLM 음역 실패 ({ticker}): {e}")
        return None


def get_korean_name_naver(ticker: str) -> Optional[str]:
    """네이버 미국주식 페이지에서 한글명 가져오기.

    네이버는 미국 종목에 .O 접미사 사용 (예: AAPL → AAPL.O).
    회사 한글명이 있으면 반환, 없으면 None.
    """
    try:
        url = f"https://api.stock.naver.com/stock/{ticker}.O/basic"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36',
            'Referer': f'https://m.stock.naver.com/worldstock/stock/{ticker}.O/total',
            'Accept': 'application/json',
        }
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code != 200:
            return None
        data = response.json()
        # 네이버 응답: stockName(한글) 또는 stockNameKor 등 키 존재
        # 우선순위: stockName > stockNameEng (영문이면 fallback)
        name_kor = data.get('stockName')
        if name_kor and any('가' <= ch <= '힣' for ch in name_kor):
            # 한글 1자라도 포함되면 한글명으로 인정
            return name_kor.strip()
        return None
    except Exception:
        return None


def get_key_metrics_fmp(ticker: str, period: str = 'quarter') -> List:
    """FMP key-metrics API 조회 (ROE, PER, PEG)"""
    url = f"https://financialmodelingprep.com/api/v3/key-metrics/{ticker}"
    params = {
        'apikey': FMP_API_KEY,
        'period': period,
        'limit': 20 if period == 'quarter' else 6
    }

    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            if not data:
                return []
            return sorted(data, key=lambda x: x.get('date', ''), reverse=True)
        else:
            print(f"key-metrics 조회 실패 ({ticker}): {response.status_code}")
            return []
    except Exception as e:
        print(f"key-metrics 조회 중 에러 발생 ({ticker}): {str(e)}")
        return []

def calculate_growth_rates_fmp(ticker: str) -> Dict:
    growth_rates = {
        'dates': {
            'quarters': {'q1': None, 'q2': None, 'q3': None, 'q4': None, 'q5': None, 'q6': None, 'q7': None, 'q8': None},
            'years': {'y1': None, 'y2': None, 'y3': None, 'y4': None, 'y5': None, 'y6': None}
        },
        'eps_growth': {'q1': None, 'q2': None, 'q3': None, 'y1': None, 'y2': None, 'y3': None},
        'eps_values': {'q1': None, 'q2': None, 'q3': None, 'q4': None, 'q5': None, 'q6': None, 'q7': None, 'q8': None, 'y1': None, 'y2': None, 'y3': None, 'y4': None, 'y5': None, 'y6': None},  # EPS 값 확장
        'operating_income_growth': {'q1': None, 'q2': None, 'q3': None, 'y1': None, 'y2': None, 'y3': None},
        'revenue_growth': {'q1': None, 'q2': None, 'q3': None, 'y1': None, 'y2': None, 'y3': None},
        'npm_growth': {'q1': None, 'q2': None, 'q3': None, 'q4': None, 'y1': None, 'y2': None, 'y3': None},
        # === 신규: raw values for markmarkmark 평가 시스템 ===
        'revenue_values': {'q1': None, 'q2': None, 'q3': None, 'q4': None, 'q5': None, 'q6': None, 'q7': None, 'q8': None},
        'operating_margin_values': {'q1': None, 'q2': None, 'q3': None, 'y1': None, 'y2': None, 'y3': None},
        'net_margin_values': {'q1': None, 'q2': None, 'q3': None, 'q4': None, 'q5': None, 'q6': None, 'q7': None, 'q8': None, 'y1': None, 'y2': None, 'y3': None},
        'roe_values': {'q1': None, 'q2': None, 'q3': None, 'y1': None, 'y2': None, 'y3': None},
        'per_values': {'q1': None, 'q2': None, 'q3': None, 'y1': None, 'y2': None, 'y3': None},
        'peg_values': {'q1': None}
    }
    
    # 분기 데이터 조회
    quarterly_data = get_financials_fmp(ticker, 'quarter')
    if not quarterly_data:
        return growth_rates
        
    # 연간 데이터 조회
    annual_data = get_financials_fmp(ticker, 'annual')
    if not annual_data:
        return growth_rates
    try:
        # 분기별 성장률 계산 (기존 3분기 + EPS 값만 8분기까지 확장)
        for i in range(min(3, len(quarterly_data))):
            current_quarter = quarterly_data[i]
            year_ago_quarter = find_matching_quarter_data(current_quarter, quarterly_data)
            
            if year_ago_quarter:
                quarter_key = f'q{i+1}'
                growth_rates['dates']['quarters'][quarter_key] = current_quarter['date']
                
                # EPS 계산
                current_eps = calculate_eps(
                    current_quarter.get('netIncome', 0),
                    current_quarter.get('weightedAverageShsOut', 0)
                )
                growth_rates['eps_values'][quarter_key] = current_eps  # EPS 값 저장
                previous_eps = calculate_eps(
                    year_ago_quarter.get('netIncome', 0),
                    year_ago_quarter.get('weightedAverageShsOut', 0)
                )
                
                # NPM 계산 (추가)
                current_npm = (current_quarter.get('netIncome', 0) / current_quarter.get('revenue', 1)) * 100 if current_quarter.get('revenue', 0) != 0 else None
                previous_npm = (year_ago_quarter.get('netIncome', 0) / year_ago_quarter.get('revenue', 1)) * 100 if year_ago_quarter.get('revenue', 0) != 0 else None
                
                # 성장률 계산
                growth_rates['eps_growth'][quarter_key] = safe_growth_rate(current_eps, previous_eps)
                growth_rates['operating_income_growth'][quarter_key] = safe_growth_rate(
                    current_quarter.get('operatingIncome'),
                    year_ago_quarter.get('operatingIncome')
                )
                growth_rates['revenue_growth'][quarter_key] = safe_growth_rate(
                    current_quarter.get('revenue'),
                    year_ago_quarter.get('revenue')
                )
                growth_rates['npm_growth'][quarter_key] = safe_growth_rate(current_npm, previous_npm)  # NPM 성장률 추가

        # NPM 성장률 q4 (markmarkmark 마진 개선 점수의 1년 비교용)
        if len(quarterly_data) >= 4:
            q4_quarter = quarterly_data[3]
            year_ago_q4 = find_matching_quarter_data(q4_quarter, quarterly_data)
            if year_ago_q4:
                rev_q4 = q4_quarter.get('revenue', 0)
                rev_ya = year_ago_q4.get('revenue', 0)
                current_npm_q4 = (q4_quarter.get('netIncome', 0) / rev_q4) * 100 if rev_q4 else None
                previous_npm_q4 = (year_ago_q4.get('netIncome', 0) / rev_ya) * 100 if rev_ya else None
                growth_rates['npm_growth']['q4'] = safe_growth_rate(current_npm_q4, previous_npm_q4)

        # 추가 분기별 EPS 값만 계산 (q4~q8)
        for i in range(3, min(8, len(quarterly_data))):
            if i < len(quarterly_data):
                current_quarter = quarterly_data[i]
                quarter_key = f'q{i+1}'
                growth_rates['dates']['quarters'][quarter_key] = current_quarter['date']
                
                # EPS 값만 계산
                current_eps = calculate_eps(
                    current_quarter.get('netIncome', 0),
                    current_quarter.get('weightedAverageShsOut', 0)
                )
                growth_rates['eps_values'][quarter_key] = current_eps
        
        # 연간 성장률 계산 (기존 3년 + EPS 값만 6년까지 확장)
        for i in range(min(3, len(annual_data) - 1)):
            current_year = annual_data[i]
            previous_year = annual_data[i + 1]
            
            year_key = f'y{i+1}'
            growth_rates['dates']['years'][year_key] = current_year['calendarYear']
            
            # EPS 계산
            current_eps = calculate_eps(
                current_year.get('netIncome', 0),
                current_year.get('weightedAverageShsOut', 0)
            )
            growth_rates['eps_values'][year_key] = current_eps  # EPS 값 저장
            previous_eps = calculate_eps(
                previous_year.get('netIncome', 0),
                previous_year.get('weightedAverageShsOut', 0)
            )
            
            # NPM 계산 (추가)
            current_npm = (current_year.get('netIncome', 0) / current_year.get('revenue', 1)) * 100 if current_year.get('revenue', 0) != 0 else None
            previous_npm = (previous_year.get('netIncome', 0) / previous_year.get('revenue', 1)) * 100 if previous_year.get('revenue', 0) != 0 else None
            
            # 성장률 계산
            growth_rates['eps_growth'][year_key] = safe_growth_rate(current_eps, previous_eps)
            growth_rates['operating_income_growth'][year_key] = safe_growth_rate(
                current_year.get('operatingIncome'),
                previous_year.get('operatingIncome')
            )
            growth_rates['revenue_growth'][year_key] = safe_growth_rate(
                current_year.get('revenue'),
                previous_year.get('revenue')
            )
            growth_rates['npm_growth'][year_key] = safe_growth_rate(current_npm, previous_npm)  # NPM 성장률 추가
        
        # 추가 연간 EPS 값만 계산 (y4~y6)
        for i in range(3, min(7, len(annual_data))):  # 6을 7로 변경하여 y6까지 포함
            if i < len(annual_data):
                current_year = annual_data[i]
                year_key = f'y{i+1}'
                growth_rates['dates']['years'][year_key] = current_year['calendarYear']

                # EPS 값만 계산
                current_eps = calculate_eps(
                    current_year.get('netIncome', 0),
                    current_year.get('weightedAverageShsOut', 0)
                )
                growth_rates['eps_values'][year_key] = current_eps

        # === 신규: raw values 추출 (markmarkmark 평가 시스템 호환) ===
        # 분기 매출액 raw 값 (q1~q8) + 분기 순이익률 (q1~q8)
        for i in range(min(8, len(quarterly_data))):
            q = quarterly_data[i]
            qkey = f'q{i+1}'
            revenue = q.get('revenue')
            net_income = q.get('netIncome')
            growth_rates['revenue_values'][qkey] = revenue
            if revenue and revenue != 0 and net_income is not None:
                growth_rates['net_margin_values'][qkey] = (net_income / revenue) * 100

        # 분기 영업이익률 (q1~q3)
        for i in range(min(3, len(quarterly_data))):
            q = quarterly_data[i]
            qkey = f'q{i+1}'
            revenue = q.get('revenue')
            op_income = q.get('operatingIncome')
            if revenue and revenue != 0 and op_income is not None:
                growth_rates['operating_margin_values'][qkey] = (op_income / revenue) * 100

        # 연간 영업이익률 + 순이익률 (y1~y3)
        for i in range(min(3, len(annual_data))):
            y = annual_data[i]
            ykey = f'y{i+1}'
            revenue = y.get('revenue')
            op_income = y.get('operatingIncome')
            net_income = y.get('netIncome')
            if revenue and revenue != 0:
                if op_income is not None:
                    growth_rates['operating_margin_values'][ykey] = (op_income / revenue) * 100
                if net_income is not None:
                    growth_rates['net_margin_values'][ykey] = (net_income / revenue) * 100

        # === 신규: ROE / PER / PEG (key-metrics API) ===
        quarterly_metrics = get_key_metrics_fmp(ticker, 'quarter')
        annual_metrics = get_key_metrics_fmp(ticker, 'annual')

        # 분기 ROE / PER (q1~q3) + PEG (q1만)
        for i in range(min(3, len(quarterly_metrics))):
            m = quarterly_metrics[i]
            qkey = f'q{i+1}'
            growth_rates['roe_values'][qkey] = m.get('roe')
            growth_rates['per_values'][qkey] = m.get('peRatio')
            if i == 0:
                # FMP에서 PEG 시도, 없으면 직접 계산 (PEG = PER / EPS 성장률)
                peg = m.get('pegRatio') or m.get('priceEarningsToGrowthRatio')
                if peg is None:
                    per_q1 = growth_rates['per_values'].get('q1')
                    eps_growth_q1 = growth_rates['eps_growth'].get('q1')
                    if per_q1 is not None and eps_growth_q1 is not None and eps_growth_q1 != 0:
                        peg = per_q1 / eps_growth_q1
                growth_rates['peg_values']['q1'] = peg

        # 연간 ROE / PER (y1~y3)
        for i in range(min(3, len(annual_metrics))):
            m = annual_metrics[i]
            ykey = f'y{i+1}'
            growth_rates['roe_values'][ykey] = m.get('roe')
            growth_rates['per_values'][ykey] = m.get('peRatio')

    except Exception as e:
        print(f"성장률 계산 중 에러 발생: {str(e)}")
    return growth_rates

def get_stock_data(ticker: str) -> Dict:
    now = datetime.now()
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
    
    # 시장 상태 확인
    status_url = "https://api.polygon.io/v1/marketstatus/now"
    try:
        status_response = requests.get(status_url, params={'apiKey': POLYGON_API_KEY})
        if status_response.status_code == 200:
            market_status = status_response.json().get('market')
            if market_status != 'open':
                # 휴장일이면 무조건 이전 거래일 데이터 사용
                url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/prev"
                params = {'apiKey': POLYGON_API_KEY, 'adjusted': 'true'}
                endpoint_used = 'prev'
                # return 문을 제거하고 아래 로직으로 계속 진행되도록 함
    except Exception as e:
        print(f"시장 상태 확인 중 에러: {str(e)}")
    
    # 휴장일이 아닐 경우 시간 체크
    if not 'url' in locals():  # url이 아직 설정되지 않은 경우에만
        if now < market_open:
            url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/prev"
            params = {'apiKey': POLYGON_API_KEY, 'adjusted': 'true'}
            endpoint_used = 'prev'
        elif now >= market_close:
            today = now.strftime("%Y-%m-%d")
            url = f"https://api.polygon.io/v1/open-close/{ticker}/{today}"
            params = {'apiKey': POLYGON_API_KEY, 'adjusted': 'true'}
            endpoint_used = 'open-close'
        else:
            print(f"{ticker} 현재는 장중입니다. 장전 또는 장마감 후에 실행하세요.")
            return {}
    
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            if endpoint_used == 'prev':
                if data.get('status') == 'OK' and data.get('results'):
                    result = data['results'][0]
                    transformed = {
                        'c': result.get('c', 0),  # 종가
                        'o': result.get('o', 0),  # 시가
                        'h': result.get('h', 0),  # 고가
                        'l': result.get('l', 0),  # 저가
                        'v': result.get('v', 0)   # 거래량
                    }
                else:
                    print(f"데이터 없음 ({ticker}): {data}")
                    return {}
            else:  # open-close 엔드포인트 사용 시
                if data.get('status') == 'OK':
                    transformed = {
                        'c': data.get('close', 0),
                        'o': data.get('open', 0),
                        'h': data.get('high', 0),
                        'l': data.get('low', 0),
                        'v': data.get('volume', 0)
                    }
                else:
                    print(f"데이터 없음 ({ticker}): {data}")
                    return {}
            if transformed['o'] != 0:
                transformed['todaysChangePerc'] = ((transformed['c'] - transformed['o']) / transformed['o']) * 100
            else:
                transformed['todaysChangePerc'] = 0
            transformed['ticker'] = ticker
            return {'day': transformed, 'ticker': ticker}
        print(f"주식 데이터 조회 실패 ({ticker}): {response.status_code}")
        return {}
    except Exception as e:
        print(f"주식 데이터 조회 중 에러 발생 ({ticker}): {str(e)}")
        return {}

def get_stock_details(ticker: str) -> Dict:
    """Polygon API를 사용하여 주식 상세 정보 조회"""
    url = f"https://api.polygon.io/v3/reference/tickers/{ticker}"
    params = {'apiKey': POLYGON_API_KEY}
    
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json().get('results', {})
        print(f"종목 상세정보 조회 실패 ({ticker}): {response.status_code}")
        return {}
    except Exception as e:
        print(f"종목 상세정보 조회 중 에러 발생 ({ticker}): {str(e)}")
        return {}

def update_airtable(stock_data: List, category: str):
    """Airtable에 데이터 업데이트 (기존 '마크미너비니' 뷰의 레코드 업데이트)"""
    airtable = Airtable(TARGET_BASE_ID, TARGET_TABLE_NAME, AIRTABLE_API_KEY)
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    for stock in stock_data:
        try:
            print(f"\n{stock['ticker']} 처리 중...")

            ticker = stock['ticker']

            # 한글명 결정: 기존 Airtable 캐시 > 네이버 > Claude API
            # (이미 채워진 종목은 API 호출 안 함 → 비용 절감)
            existing_records = airtable.search('티커', ticker, view='마크미너비니')
            existing_korean = ''
            if existing_records:
                existing_korean = existing_records[0]['fields'].get('한글명', '') or ''

            if existing_korean:
                korean_name = existing_korean
            else:
                korean_name = get_korean_name_naver(ticker)
                if not korean_name:
                    korean_name = get_korean_name_llm(ticker, stock.get('name', ''))

            growth_rates = calculate_growth_rates_fmp(ticker)
            
            record = {
                '티커': stock.get('ticker', ''),
                '종목명': stock.get('name', ''),
                '한글명': korean_name or '',  # 네이버 한글명 (없으면 빈 문자열)
                '현재가': float(stock.get('day', {}).get('c', 0)),
                '등락률': float(stock.get('day', {}).get('todaysChangePerc', 0)),
                '거래량': int(stock.get('day', {}).get('v', 0)),
                '시가총액': float(stock.get('market_cap', 0)),
                '업데이트 날짜': current_date,
                '분류': category,

                # EPS 값 추가
                'EPS_최신분기': growth_rates['eps_values']['q1'],
                'EPS_전분기': growth_rates['eps_values']['q2'],
                'EPS_전전분기': growth_rates['eps_values']['q3'],
                'EPS_4분기전': growth_rates['eps_values']['q4'],
                'EPS_5분기전': growth_rates['eps_values']['q5'],
                'EPS_6분기전': growth_rates['eps_values']['q6'],
                'EPS_7분기전': growth_rates['eps_values']['q7'],
                'EPS_8분기전': growth_rates['eps_values']['q8'],
                'EPS_1년': growth_rates['eps_values']['y1'],
                'EPS_2년': growth_rates['eps_values']['y2'],
                'EPS_3년': growth_rates['eps_values']['y3'],
                'EPS_4년': growth_rates['eps_values']['y4'],
                'EPS_5년': growth_rates['eps_values']['y5'],
                'EPS_6년': growth_rates['eps_values']['y6'],
                
                # EPS 성장률과 날짜
                'EPS성장률_최신분기': growth_rates['eps_growth']['q1'],
                'EPS성장률_전분기': growth_rates['eps_growth']['q2'],
                'EPS성장률_전전분기': growth_rates['eps_growth']['q3'],
                'EPS성장률_1년': growth_rates['eps_growth']['y1'],
                'EPS성장률_2년': growth_rates['eps_growth']['y2'],
                'EPS성장률_3년': growth_rates['eps_growth']['y3'],
                
                'EPS성장률_최신분기(날짜)': growth_rates['dates']['quarters'].get('q1'),
                'EPS성장률_전분기(날짜)': growth_rates['dates']['quarters'].get('q2'),
                'EPS성장률_전전분기(날짜)': growth_rates['dates']['quarters'].get('q3'),
                'EPS성장률_1년(날짜)': growth_rates['dates']['years'].get('y1'),
                'EPS성장률_2년(날짜)': growth_rates['dates']['years'].get('y2'),
                'EPS성장률_3년(날짜)': growth_rates['dates']['years'].get('y3'),
                
                # 영업이익 성장률과 날짜
                '영업이익성장률_최신분기': growth_rates['operating_income_growth']['q1'],
                '영업이익성장률_전분기': growth_rates['operating_income_growth']['q2'],
                '영업이익성장률_전전분기': growth_rates['operating_income_growth']['q3'],
                '영업이익성장률_1년': growth_rates['operating_income_growth']['y1'],
                '영업이익성장률_2년': growth_rates['operating_income_growth']['y2'],
                '영업이익성장률_3년': growth_rates['operating_income_growth']['y3'],
                
                '영업이익성장률_최신분기(날짜)': growth_rates['dates']['quarters'].get('q1'),
                '영업이익성장률_전분기(날짜)': growth_rates['dates']['quarters'].get('q2'),
                '영업이익성장률_전전분기(날짜)': growth_rates['dates']['quarters'].get('q3'),
                '영업이익성장률_1년(날짜)': growth_rates['dates']['years'].get('y1'),
                '영업이익성장률_2년(날짜)': growth_rates['dates']['years'].get('y2'),
                '영업이익성장률_3년(날짜)': growth_rates['dates']['years'].get('y3'),
                
                # 매출액 성장률과 날짜
                '매출액성장률_최신분기': growth_rates['revenue_growth']['q1'],
                '매출액성장률_전분기': growth_rates['revenue_growth']['q2'],
                '매출액성장률_전전분기': growth_rates['revenue_growth']['q3'],
                '매출액성장률_1년': growth_rates['revenue_growth']['y1'],
                '매출액성장률_2년': growth_rates['revenue_growth']['y2'],
                '매출액성장률_3년': growth_rates['revenue_growth']['y3'],
                
                '매출액성장률_최신분기(날짜)': growth_rates['dates']['quarters'].get('q1'),
                '매출액성장률_전분기(날짜)': growth_rates['dates']['quarters'].get('q2'),
                '매출액성장률_전전분기(날짜)': growth_rates['dates']['quarters'].get('q3'),
                '매출액성장률_1년(날짜)': growth_rates['dates']['years'].get('y1'),
                '매출액성장률_2년(날짜)': growth_rates['dates']['years'].get('y2'),
                '매출액성장률_3년(날짜)': growth_rates['dates']['years'].get('y3'),

                # NPM 성장률과 날짜
                'NPM성장률_최신분기': growth_rates['npm_growth']['q1'],
                'NPM성장률_전분기': growth_rates['npm_growth']['q2'],
                'NPM성장률_전전분기': growth_rates['npm_growth']['q3'],
                'NPM성장률_4분기전': growth_rates['npm_growth']['q4'],
                'NPM성장률_1년': growth_rates['npm_growth']['y1'],
                'NPM성장률_2년': growth_rates['npm_growth']['y2'],
                'NPM성장률_3년': growth_rates['npm_growth']['y3'],
                
                'NPM성장률_최신분기(날짜)': growth_rates['dates']['quarters'].get('q1'),
                'NPM성장률_전분기(날짜)': growth_rates['dates']['quarters'].get('q2'),
                'NPM성장률_전전분기(날짜)': growth_rates['dates']['quarters'].get('q3'),
                'NPM성장률_1년(날짜)': growth_rates['dates']['years'].get('y1'),
                'NPM성장률_2년(날짜)': growth_rates['dates']['years'].get('y2'),
                'NPM성장률_3년(날짜)': growth_rates['dates']['years'].get('y3'),

                # === 신규: markmarkmark 평가 시스템 호환 필드 (38개) ===
                # 매출액 raw (분기 8개)
                '매출액_최신분기': growth_rates['revenue_values']['q1'],
                '매출액_전분기': growth_rates['revenue_values']['q2'],
                '매출액_전전분기': growth_rates['revenue_values']['q3'],
                '매출액_4분기전': growth_rates['revenue_values']['q4'],
                '매출액_5분기전': growth_rates['revenue_values']['q5'],
                '매출액_6분기전': growth_rates['revenue_values']['q6'],
                '매출액_7분기전': growth_rates['revenue_values']['q7'],
                '매출액_8분기전': growth_rates['revenue_values']['q8'],

                # 영업이익률(%) raw (분기 3 + 연간 3)
                '영업이익률(%)_최신분기': growth_rates['operating_margin_values']['q1'],
                '영업이익률(%)_전분기': growth_rates['operating_margin_values']['q2'],
                '영업이익률(%)_전전분기': growth_rates['operating_margin_values']['q3'],
                '영업이익률(%)_1년': growth_rates['operating_margin_values']['y1'],
                '영업이익률(%)_2년': growth_rates['operating_margin_values']['y2'],
                '영업이익률(%)_3년': growth_rates['operating_margin_values']['y3'],

                # 순이익률 raw (분기 8 + 연간 3)
                '순이익률_최신분기': growth_rates['net_margin_values']['q1'],
                '순이익률_전분기': growth_rates['net_margin_values']['q2'],
                '순이익률_전전분기': growth_rates['net_margin_values']['q3'],
                '순이익률_4분기전': growth_rates['net_margin_values']['q4'],
                '순이익률_5분기전': growth_rates['net_margin_values']['q5'],
                '순이익률_6분기전': growth_rates['net_margin_values']['q6'],
                '순이익률_7분기전': growth_rates['net_margin_values']['q7'],
                '순이익률_8분기전': growth_rates['net_margin_values']['q8'],
                '순이익률_1년': growth_rates['net_margin_values']['y1'],
                '순이익률_2년': growth_rates['net_margin_values']['y2'],
                '순이익률_3년': growth_rates['net_margin_values']['y3'],

                # ROE (분기 3 + 연간 3)
                'ROE_최신분기': growth_rates['roe_values']['q1'],
                'ROE_전분기': growth_rates['roe_values']['q2'],
                'ROE_전전분기': growth_rates['roe_values']['q3'],
                'ROE_1년': growth_rates['roe_values']['y1'],
                'ROE_2년': growth_rates['roe_values']['y2'],
                'ROE_3년': growth_rates['roe_values']['y3'],

                # PER (분기 3 + 연간 3)
                'PER_최신분기': growth_rates['per_values']['q1'],
                'PER_전분기': growth_rates['per_values']['q2'],
                'PER_전전분기': growth_rates['per_values']['q3'],
                'PER_1년': growth_rates['per_values']['y1'],
                'PER_2년': growth_rates['per_values']['y2'],
                'PER_3년': growth_rates['per_values']['y3'],

                # PEG (1)
                'PEG_최신분기': growth_rates['peg_values']['q1'],
            }
            
            if stock.get('primary_exchange'):
                record['거래소 정보'] = convert_exchange_code(stock['primary_exchange'])

            # existing_records는 한글명 결정 단계에서 이미 fetch됨 (재사용)
            if existing_records:
                record_id = existing_records[0]['id']
                airtable.update(record_id, record)
                print(f"데이터 업데이트 완료 (마크미너비니 뷰): {record['티커']}")
            else:
                print(f"마크미너비니 뷰에서 {record['티커']} 티커를 찾을 수 없습니다.")
            
            time.sleep(1)  # Rate limit 고려
                
        except Exception as e:
            print(f"레코드 처리 중 에러 발생 ({stock.get('ticker', 'Unknown')}): {str(e)}")

def convert_exchange_code(mic: str) -> str:
    """거래소 코드 변환"""
    exchange_map = {
        'XNAS': 'NASDAQ',
        'XNYS': 'NYSE',
        'XASE': 'AMEX'
    }
    return exchange_map.get(mic, mic)

def main():
    try:
        print("데이터 수집 시작...")
        
        # Airtable에서 티커 목록 가져오기
        tickers = get_tickers_from_airtable()
        if not tickers:
            print("티커 목록을 가져오지 못했습니다.")
            return
            
        stock_data = []
        for ticker in tickers:
            try:
                print(f"\n{ticker} 데이터 수집 중...")
                
                # 기본 주식 데이터 조회 (장전 또는 장마감 후에 따라 적절한 엔드포인트 사용)
                data = get_stock_data(ticker)
                if not data:
                    continue
                    
                # 상세 정보 조회 및 데이터 병합
                details = get_stock_details(ticker)
                if details:
                    data['name'] = details.get('name', '')
                    data['market_cap'] = float(details.get('market_cap', 0))
                    data['primary_exchange'] = details.get('primary_exchange', '')
                    
                stock_data.append(data)
                time.sleep(0.5)  # Rate limit 고려
                
            except Exception as e:
                print(f"{ticker} 처리 중 에러 발생: {str(e)}")
                continue
        
        # Airtable 업데이트 (업데이트 형식)
        if stock_data:
            update_airtable(stock_data, "마크미너비니")
            print(f"\n{len(stock_data)}개 종목의 데이터 처리 완료!")
        else:
            print("\n처리할 데이터가 없습니다.")
            
    except Exception as e:
        print(f"프로그램 실행 중 오류 발생: {str(e)}")

if __name__ == "__main__":
    main()
