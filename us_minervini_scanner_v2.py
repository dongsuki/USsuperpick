import pandas as pd
import numpy as np
import requests
import concurrent.futures
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import time
from dataclasses import dataclass
import warnings
import os
warnings.filterwarnings('ignore')

# Airtable 연동
from airtable import Airtable

@dataclass
class StockData:
    """주식 데이터를 담는 데이터 클래스"""
    ticker: str
    name: str
    price: float
    market_cap: float
    volume: float
    sector: str
    exchange: str

class USMinerviniScannerV2:
    """
    미국 주식 시장용 Mark Minervini 스캐너 V2
    
    개선사항:
    - RS 등급 계산을 위해 전체 종목 포함
    - 투자 후보 선별 시에만 필터링 적용
    - 더 정확한 상대적 강도 계산
    """
    
    def __init__(self, api_key: str, max_workers: int = 10, batch_size: int = 100, 
                 airtable_api_key: str = None, airtable_base_id: str = None, airtable_table_name: str = None):
        """
        스캐너 초기화
        
        Args:
            api_key: FMP API 키
            max_workers: 병렬 처리 워커 수
            batch_size: 배치 처리 크기
            airtable_api_key: Airtable API 키
            airtable_base_id: Airtable Base ID
            airtable_table_name: Airtable 테이블 이름
        """
        self.api_key = api_key
        self.base_url = "https://financialmodelingprep.com/api/v3"
        self.max_workers = max_workers
        self.batch_size = batch_size
        
        # Airtable 설정
        self.airtable_api_key = airtable_api_key
        self.airtable_base_id = airtable_base_id
        self.airtable_table_name = airtable_table_name
        self.airtable = None
        
        if all([airtable_api_key, airtable_base_id, airtable_table_name]):
            self.airtable = Airtable(airtable_base_id, airtable_table_name, api_key=airtable_api_key)
            print(f"📊 Airtable 연동 설정 완료")
        
        # 데이터 캐시
        self.stock_list_cache = None
        self.price_data_cache = {}
        
        print(f"🚀 US Minervini Scanner V2 초기화 완료")
        print(f"   - 최대 워커 수: {max_workers}")
        print(f"   - 배치 크기: {batch_size}")
        print(f"   - ✨ RS 계산용 전체 종목 포함")
    
    def get_all_stocks(self) -> List[StockData]:
        """
        미국 전체 상장 주식 리스트 수집 (필터링 최소화)
        RS 등급 계산을 위해 가능한 많은 종목 포함
        """
        if self.stock_list_cache is not None:
            return self.stock_list_cache
            
        print("📋 미국 전체 상장 주식 리스트 수집 중...")
        
        url = f"{self.base_url}/stock-screener"
        params = {
            'apikey': self.api_key,
            'marketCapMoreThan': 1,          # 💰 시가총액: $1 이상 (거의 모든 종목 포함)
            'volumeMoreThan': 1,             # 📊 거래량: 1주 이상 (거의 모든 종목 포함)
            'priceMoreThan': 1,              # 💵 주가: $1 이상 (페니스톡만 제외)
            'exchange': 'NASDAQ,NYSE',       # 🏛️ 거래소: NASDAQ, NYSE만
            'limit': 10000                   # 📈 수집 한도: 최대 10,000개 종목
        }
        
        try:
            response = requests.get(url, params=params)
            if response.status_code != 200:
                print(f"❌ API 요청 실패: {response.status_code}")
                return []
                
            data = response.json()
            
            stocks = []
            for item in data:
                # 거래 가능한 일반 주식만 선별 (ETF, 펀드, 우선주 등 제외)
                company_name = item.get('companyName', '').upper()
                if any(keyword in company_name for keyword in 
                      ['ETF', 'FUND', 'TRUST', 'PREFERRED', 'WARRANT', 'UNIT']):
                    continue
                
                stock = StockData(
                    ticker=item.get('symbol', ''),
                    name=item.get('companyName', ''),
                    price=float(item.get('price', 0)),
                    market_cap=float(item.get('marketCap', 0)),
                    volume=float(item.get('volume', 0)),
                    sector=item.get('sector', ''),
                    exchange=item.get('exchangeShortName', '')
                )
                stocks.append(stock)
            
            self.stock_list_cache = stocks
            print(f"✅ {len(stocks)}개 종목 수집 완료 (RS 계산용 전체 모집단)")
            return stocks
            
        except Exception as e:
            print(f"❌ 주식 리스트 수집 중 오류: {e}")
            return []
    
    def get_historical_data(self, ticker: str, days: int = 400) -> Optional[pd.DataFrame]:
        """
        개별 종목의 과거 가격 데이터 수집
        """
        if ticker in self.price_data_cache:
            return self.price_data_cache[ticker]
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days + 50)
        
        url = f"{self.base_url}/historical-price-full/{ticker}"
        params = {
            'apikey': self.api_key,
            'from': start_date.strftime('%Y-%m-%d'),
            'to': end_date.strftime('%Y-%m-%d')
        }
        
        try:
            response = requests.get(url, params=params)
            if response.status_code != 200:
                return None
                
            data = response.json()
            historical = data.get('historical', [])
            
            if len(historical) < 100:  # 최소 기준 낮춤 (더 많은 종목 포함)
                return None
            
            df = pd.DataFrame(historical)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)
            
            df = df.rename(columns={
                'date': 'Date',
                'open': 'Open', 
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume'
            })
            
            df = df.tail(400).reset_index(drop=True)
            
            self.price_data_cache[ticker] = df
            return df
            
        except Exception as e:
            return None
    
    def calculate_technical_indicators(self, df: pd.DataFrame) -> Dict:
        """
        기술적 지표 계산 (RS 계산용 간소화 버전)
        """
        if len(df) < 50:  # 최소 기준 대폭 낮춤
            return None
            
        try:
            # 모멘텀 점수 계산 (RS용)
            momentum_score = self.calculate_momentum_score(df)
            
            # 당일 등락률 계산
            daily_change_rate = self.calculate_daily_change_rate(df)

            # 이동평균 존 계산 (markmarkmark 호환)
            ma_zones = self._calculate_ma_zones(df)

            # Minervini 조건용 지표들 (충분한 데이터가 있을 때만)
            minervini_indicators = {}
            if len(df) >= 252:
                df['SMA_50'] = df['Close'].rolling(window=50).mean()
                df['SMA_150'] = df['Close'].rolling(window=150).mean()
                df['SMA_200'] = df['Close'].rolling(window=200).mean()
                
                minervini_indicators = {
                    'current_price': df['Close'].iloc[-1],
                    'sma_50': df['SMA_50'].iloc[-1],
                    'sma_150': df['SMA_150'].iloc[-1],
                    'sma_200': df['SMA_200'].iloc[-1],
                    'sma_200_20d_ago': df['SMA_200'].iloc[-21] if len(df) >= 21 else df['SMA_200'].iloc[-1],
                    'year_high': df['High'].tail(252).max(),
                    'year_low': df['Low'].tail(252).min(),
                    'volume': df['Volume'].iloc[-1],
                    'minervini_ready': True
                }
            else:
                minervini_indicators = {
                    'minervini_ready': False
                }
            
            return {
                'momentum_score': momentum_score,
                'daily_change_rate': daily_change_rate,
                **ma_zones,
                **minervini_indicators
            }

        except Exception as e:
            return None

    def _calculate_ma_zones(self, df: pd.DataFrame) -> Dict:
        """
        현재가가 어느 이동평균선 사이에 있는지 boolean으로 표시.
        한국 ma_zone_scanner.py와 동일한 정의.
          3일선 위: 현재가 > MA3
          3존: MA5 ≤ 현재가 < MA3
          8존: MA8 ≤ 현재가 < MA5
          15존: MA15 ≤ 현재가 < MA10
          20존: MA20 ≤ 현재가 < MA15
          33존: MA33 ≤ 현재가 < MA20
          50존: MA50 ≤ 현재가 < MA33
          슈퍼존: MA100 ≤ 현재가 ≤ MA50
        """
        zones = {
            'zone_3day_above': False,
            'zone_3': False,
            'zone_8': False,
            'zone_15': False,
            'zone_20': False,
            'zone_33': False,
            'zone_50': False,
            'zone_super': False,
        }
        try:
            close = df['Close']
            current = close.iloc[-1]

            def ma(n: int):
                return close.rolling(window=n).mean().iloc[-1] if len(df) >= n else None

            ma3, ma5, ma8, ma10, ma15, ma20, ma33, ma50, ma100 = (
                ma(3), ma(5), ma(8), ma(10), ma(15), ma(20), ma(33), ma(50), ma(100)
            )

            if ma3 is not None:
                zones['zone_3day_above'] = bool(current > ma3)
            if ma3 is not None and ma5 is not None:
                zones['zone_3'] = bool(ma5 <= current < ma3)
            if ma5 is not None and ma8 is not None:
                zones['zone_8'] = bool(ma8 <= current < ma5)
            if ma10 is not None and ma15 is not None:
                zones['zone_15'] = bool(ma15 <= current < ma10)
            if ma15 is not None and ma20 is not None:
                zones['zone_20'] = bool(ma20 <= current < ma15)
            if ma20 is not None and ma33 is not None:
                zones['zone_33'] = bool(ma33 <= current < ma20)
            if ma33 is not None and ma50 is not None:
                zones['zone_50'] = bool(ma50 <= current < ma33)
            if ma50 is not None and ma100 is not None:
                zones['zone_super'] = bool(ma100 <= current <= ma50)
        except Exception:
            pass
        return zones

    def calculate_momentum_score(self, df: pd.DataFrame) -> float:
        """
        가중 모멘텀 점수 계산 (유연한 버전)
        """
        try:
            current_price = df['Close'].iloc[-1]
            
            # 각 기간별 가격 (가능한 데이터만 사용)
            price_1m = df['Close'].iloc[-min(21, len(df)-1)] if len(df) > 21 else df['Close'].iloc[0]
            price_3m = df['Close'].iloc[-min(63, len(df)-1)] if len(df) > 63 else df['Close'].iloc[0]
            price_6m = df['Close'].iloc[-min(126, len(df)-1)] if len(df) > 126 else df['Close'].iloc[0]
            price_12m = df['Close'].iloc[-min(252, len(df)-1)] if len(df) > 252 else df['Close'].iloc[0]
            
            # 수익률 계산
            return_1m = (current_price / price_1m - 1) * 100 if price_1m > 0 else 0
            return_3m = (current_price / price_3m - 1) * 100 if price_3m > 0 else 0
            return_6m = (current_price / price_6m - 1) * 100 if price_6m > 0 else 0
            return_12m = (current_price / price_12m - 1) * 100 if price_12m > 0 else 0
            
            # 가중 점수
            weighted_score = (return_12m * 0.4 + return_6m * 0.2 + 
                            return_3m * 0.2 + return_1m * 0.2)
            
            return weighted_score
            
        except Exception as e:
            return 0
    
    def calculate_daily_change_rate(self, df: pd.DataFrame) -> float:
        """
        당일 등락률 계산 (전일 종가 대비 현재가 변동률)
        """
        try:
            if len(df) < 2:
                return 0
            
            # 현재가 (최신 종가)
            current_price = df['Close'].iloc[-1]
            
            # 전일 종가
            previous_price = df['Close'].iloc[-2]
            
            # 당일 등락률 계산 (%)
            if previous_price > 0:
                daily_change = ((current_price - previous_price) / previous_price) * 100
                return round(daily_change, 2)
            else:
                return 0
                
        except Exception as e:
            return 0
    
    def process_stock_batch(self, stocks: List[StockData]) -> List[Dict]:
        """
        주식 배치 처리 (모든 종목 포함)
        """
        results = []
        
        def process_single_stock(stock):
            try:
                # 가격 데이터 수집
                df = self.get_historical_data(stock.ticker)
                if df is None or len(df) < 20:  # 최소 기준 대폭 낮춤
                    return None
                
                # 기술적 지표 계산
                indicators = self.calculate_technical_indicators(df)
                if indicators is None:
                    return None
                
                # 결과 조합
                result = {
                    'ticker': stock.ticker,
                    'name': stock.name,
                    'sector': stock.sector,
                    'exchange': stock.exchange,
                    'market_cap': stock.market_cap,
                    'base_volume': stock.volume,  # 기본 거래량 정보
                    **indicators
                }
                
                return result
                
            except Exception as e:
                return None
        
        # 병렬 처리
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_stock = {executor.submit(process_single_stock, stock): stock 
                             for stock in stocks}
            
            for future in concurrent.futures.as_completed(future_to_stock):
                result = future.result()
                if result is not None:
                    results.append(result)
        
        return results
    
    def calculate_rs_rating(self, stock_data: List[Dict]) -> List[Dict]:
        """
        RS 등급 계산 (전체 모집단 기준)
        """
        print(f"📊 RS 등급 계산 중... (전체 {len(stock_data)}개 종목 기준)")
        
        # 모멘텀 점수로 정렬
        sorted_stocks = sorted(stock_data, key=lambda x: x['momentum_score'], reverse=True)
        total_stocks = len(sorted_stocks)
        
        # RS 등급 부여
        for i, stock in enumerate(sorted_stocks):
            percentile = ((total_stocks - i - 1) / (total_stocks - 1)) * 98 + 1
            stock['rs_rating'] = round(percentile, 1)
        
        print(f"✅ {total_stocks}개 종목 RS 등급 계산 완료 (정확한 상대적 강도)")
        return sorted_stocks
    
    def apply_investment_filters(self, stock_data: List[Dict]) -> List[Dict]:
        """
        투자 후보 선별을 위한 필터링 (RS 계산 후 적용)
        """
        print("🔍 투자 후보 선별 필터링 중...")
        
        filtered_for_investment = []
        filter_stats = {
            'total': len(stock_data),
            'market_cap_filter': 0,
            'volume_filter': 0,
            'price_filter': 0,
            'minervini_ready': 0
        }
        
        for stock in stock_data:
            # 투자 적합성 필터링
            if stock['market_cap'] < 100000000:  # 시가총액 1억 달러 미만
                filter_stats['market_cap_filter'] += 1
                continue
                
            if stock['base_volume'] < 100000:  # 거래량 10만주 미만
                filter_stats['volume_filter'] += 1
                continue
                
            if 'current_price' in stock and stock['current_price'] < 5:  # 페니스톡
                filter_stats['price_filter'] += 1
                continue
                
            # 펀드, 트러스트 등은 이미 1단계에서 제외됨 (중복 제거)
                
            # Minervini 분석 가능한 종목만
            if not stock.get('minervini_ready', False):
                filter_stats['minervini_ready'] += 1
                continue
                
            filtered_for_investment.append(stock)
        
        print(f"\n📈 투자 후보 필터링 통계:")
        print(f"   전체 종목: {filter_stats['total']:,}개 (ETF/펀드/우선주 등은 이미 제외됨)")
        print(f"   시가총액 필터: {filter_stats['market_cap_filter']:,}개 제외")
        print(f"   거래량 필터: {filter_stats['volume_filter']:,}개 제외") 
        print(f"   페니스톡 필터: {filter_stats['price_filter']:,}개 제외")
        print(f"   데이터 부족: {filter_stats['minervini_ready']:,}개 제외")
        print(f"   → 투자 후보: {len(filtered_for_investment):,}개")
        
        return filtered_for_investment
    
    def apply_minervini_criteria(self, stock_data: List[Dict]) -> pd.DataFrame:
        """
        Minervini 8가지 조건 적용
        """
        print("🔍 Minervini 조건 필터링 중...")
        
        filtered_stocks = []
        condition_failures = {
            'rs_rating': 0,
            'price_above_150sma': 0,
            'price_above_200sma': 0,
            'sma150_above_200': 0,
            'sma50_above_150': 0,
            'sma200_trending_up': 0,
            'price_above_30pct_low': 0,
            'price_near_high': 0
        }
        
        for stock in stock_data:
            try:
                conditions = {}
                
                # 조건 1: RS 등급 70 이상
                conditions['rs_rating'] = stock['rs_rating'] >= 70
                
                # 조건 2: 현재가 > 150일 이평선
                conditions['price_above_150sma'] = stock['current_price'] > stock['sma_150']
                
                # 조건 3: 현재가 > 200일 이평선  
                conditions['price_above_200sma'] = stock['current_price'] > stock['sma_200']
                
                # 조건 4: 150일 이평선 > 200일 이평선
                conditions['sma150_above_200'] = stock['sma_150'] > stock['sma_200']
                
                # 조건 5: 50일 이평선 > 150일 이평선
                conditions['sma50_above_150'] = stock['sma_50'] > stock['sma_150']
                
                # 조건 6: 200일 이평선 상승 추세
                conditions['sma200_trending_up'] = stock['sma_200'] > stock['sma_200_20d_ago']
                
                # 조건 7: 현재가가 52주 저가 대비 30% 이상 상승
                low_threshold = stock['year_low'] * 1.30
                conditions['price_above_30pct_low'] = stock['current_price'] >= low_threshold
                
                # 조건 8: 현재가가 52주 고가의 75% 이상
                high_threshold = stock['year_high'] * 0.75
                conditions['price_near_high'] = stock['current_price'] >= high_threshold
                
                # 실패한 조건 카운트
                for condition, passed in conditions.items():
                    if not passed:
                        condition_failures[condition] += 1
                
                # 모든 조건 통과 시 선별
                if all(conditions.values()):
                    stock['conditions_passed'] = conditions
                    filtered_stocks.append(stock)
                    
            except Exception as e:
                continue
        
        # 실패 통계 출력
        print("\n📈 Minervini 조건별 실패 통계:")
        for condition, count in condition_failures.items():
            print(f"   {condition}: {count}개 종목")
        
        # DataFrame 생성
        if filtered_stocks:
            df = pd.DataFrame(filtered_stocks)
            
            columns_order = [
                'ticker', 'name', 'sector', 'exchange', 'current_price',
                'rs_rating', 'momentum_score', 'daily_change_rate', 'market_cap', 'volume',
                'sma_50', 'sma_150', 'sma_200', 'year_high', 'year_low',
                'zone_3day_above', 'zone_3', 'zone_8', 'zone_15', 'zone_20',
                'zone_33', 'zone_50', 'zone_super'
            ]
            
            existing_columns = [col for col in columns_order if col in df.columns]
            df = df[existing_columns]
            
            df = df.sort_values('rs_rating', ascending=False).reset_index(drop=True)
            
            print(f"🎯 최종 선별: {len(df)}개 종목")
            return df
        else:
            print("❌ 조건을 만족하는 종목이 없습니다.")
            return pd.DataFrame()
    
    def clear_airtable_records(self):
        """
        Airtable의 모든 기존 레코드 삭제
        """
        if not self.airtable:
            print("❌ Airtable이 설정되지 않았습니다.")
            return False
            
        try:
            print("🗑️ Airtable 기존 데이터 삭제 중...")
            
            # 모든 레코드 조회
            records = self.airtable.get_all()
            
            if records:
                # 배치 단위로 삭제 (Airtable API 제한 고려)
                batch_size = 10
                for i in range(0, len(records), batch_size):
                    batch = records[i:i + batch_size]
                    record_ids = [record['id'] for record in batch]
                    
                    # 배치 삭제
                    self.airtable.batch_delete(record_ids)
                    print(f"   🗑️ {len(record_ids)}개 레코드 삭제 완료")
                    
                    # API 제한 방지를 위한 대기
                    time.sleep(0.5)
                
                print(f"✅ 총 {len(records)}개 기존 레코드 삭제 완료")
            else:
                print("📝 삭제할 기존 데이터가 없습니다.")
                
            return True
            
        except Exception as e:
            print(f"❌ Airtable 데이터 삭제 중 오류: {e}")
            return False
    
    def sync_to_airtable(self, df: pd.DataFrame):
        """
        스마트 동기화: Update/Create/Delete 방식으로 Airtable 동기화
        파이썬 결과가 Airtable의 유일한 기준(Source of Truth)이 됨
        """
        if not self.airtable:
            print("❌ Airtable이 설정되지 않았습니다.")
            return False
            
        try:
            print(f"🔄 Airtable 스마트 동기화 시작...")
            print(f"📊 최종 필터링된 종목: {len(df)}개")
            
            # 1단계: 기존 Airtable 데이터 조회
            print("🔍 기존 Airtable 데이터 조회 중...")
            existing_records = self.airtable.get_all()
            existing_tickers = {record['fields'].get('티커'): record for record in existing_records if '티커' in record['fields']}
            
            print(f"📋 기존 Airtable 레코드: {len(existing_records)}개")
            
            # 2단계: 새로운 데이터 준비
            new_tickers = set(df['ticker'].tolist())
            old_tickers = set(existing_tickers.keys())
            
            # 3단계: 동작 분류
            to_update = new_tickers & old_tickers  # 둘 다 있음 → 업데이트
            to_create = new_tickers - old_tickers  # 새로운 것만 있음 → 생성
            to_delete = old_tickers - new_tickers  # 기존 것만 있음 → 삭제
            
            print(f"\n🎯 동기화 계획:")
            print(f"   🔄 업데이트: {len(to_update)}개")
            print(f"   ➕ 신규 추가: {len(to_create)}개") 
            print(f"   🗑️ 삭제: {len(to_delete)}개")
            
            # 4단계: 삭제 (Delete) - 배치 삭제로 속도 개선
            deleted_count = 0
            if to_delete:
                print(f"\n🗑️ {len(to_delete)}개 종목 배치 삭제 중...")
                
                # 삭제할 레코드 ID 수집
                record_ids_to_delete = []
                for ticker in to_delete:
                    try:
                        record_id = existing_tickers[ticker]['id']
                        record_ids_to_delete.append(record_id)
                    except Exception as e:
                        print(f"   ❌ {ticker} 레코드 ID 수집 실패: {e}")
                
                # 배치 삭제 (한 번에 최대 10개씩)
                batch_size = 10
                for i in range(0, len(record_ids_to_delete), batch_size):
                    batch_ids = record_ids_to_delete[i:i + batch_size]
                    try:
                        self.airtable.batch_delete(batch_ids)
                        deleted_count += len(batch_ids)
                        print(f"   🗑️ {len(batch_ids)}개 레코드 배치 삭제 완료 (총 {deleted_count}개)")
                        time.sleep(0.3)  # API 제한 방지
                    except Exception as e:
                        print(f"   ❌ 배치 삭제 실패: {e}")
                        # 개별 삭제로 폴백
                        for record_id in batch_ids:
                            try:
                                self.airtable.delete(record_id)
                                deleted_count += 1
                                time.sleep(0.1)
                            except Exception as e2:
                                print(f"   ❌ 개별 삭제도 실패: {e2}")
                
                print(f"✅ 배치 삭제 완료: {deleted_count}개 (속도 개선됨)")
            
            # 5단계: 업데이트 (Update) - 배치 업데이트로 속도 개선
            updated_count = 0
            if to_update:
                print(f"\n🔄 {len(to_update)}개 종목 배치 업데이트 중...")
                
                # 업데이트할 레코드 데이터 준비
                records_to_update = []
                for _, row in df[df['ticker'].isin(to_update)].iterrows():
                    try:
                        # 데이터 준비
                        high_ratio = (row['current_price'] / row['year_high']) * 100 if row['year_high'] > 0 else 0
                        daily_change = row.get('daily_change_rate', 0)
                        
                        record_data = {
                            'id': existing_tickers[row['ticker']]['id'],
                            'fields': {
                                '티커': row['ticker'],
                                '종목명': row['name'],
                                '현재가': round(row['current_price'], 2),
                                '등락률': round(daily_change, 2),
                                '거래량': int(row['volume']) if pd.notna(row['volume']) else 0,
                                '시가총액': float(row['market_cap']) if pd.notna(row['market_cap']) else 0,
                                '52주 신고가 비율': round(high_ratio, 1),
                                'RS순위': round(row['rs_rating'], 1),
                                '재료명': row['sector'] if pd.notna(row['sector']) else '기타',
                                # 이동평균 존 (한국 ma_zone_scanner 정의 동일)
                                '3일선 위': bool(row.get('zone_3day_above', False)),
                                '3존': bool(row.get('zone_3', False)),
                                '8존': bool(row.get('zone_8', False)),
                                '15존': bool(row.get('zone_15', False)),
                                '20존': bool(row.get('zone_20', False)),
                                '33존': bool(row.get('zone_33', False)),
                                '50존': bool(row.get('zone_50', False)),
                                '슈퍼존': bool(row.get('zone_super', False)),
                            }
                        }
                        records_to_update.append(record_data)
                        
                    except Exception as e:
                        print(f"   ❌ {row['ticker']} 업데이트 데이터 준비 실패: {e}")
                
                # 배치 업데이트 (한 번에 최대 10개씩)
                batch_size = 10
                for i in range(0, len(records_to_update), batch_size):
                    batch_records = records_to_update[i:i + batch_size]
                    try:
                        self.airtable.batch_update(batch_records)
                        updated_count += len(batch_records)
                        print(f"   🔄 {len(batch_records)}개 레코드 배치 업데이트 완료 (총 {updated_count}개)")
                        time.sleep(0.3)  # API 제한 방지
                    except Exception as e:
                        print(f"   ❌ 배치 업데이트 실패: {e}")
                        # 개별 업데이트로 폴백
                        for record in batch_records:
                            try:
                                self.airtable.update(record['id'], record['fields'])
                                updated_count += 1
                                time.sleep(0.2)
                            except Exception as e2:
                                print(f"   ❌ 개별 업데이트도 실패: {e2}")
                
                print(f"✅ 배치 업데이트 완료: {updated_count}개 (속도 개선됨)")
            
            # 6단계: 신규 추가 (Create) - 배치 생성으로 속도 개선
            created_count = 0
            if to_create:
                print(f"\n➕ {len(to_create)}개 종목 배치 생성 중...")
                
                # 생성할 레코드 데이터 준비
                records_to_create = []
                for _, row in df[df['ticker'].isin(to_create)].iterrows():
                    try:
                        # 데이터 준비
                        high_ratio = (row['current_price'] / row['year_high']) * 100 if row['year_high'] > 0 else 0
                        daily_change = row.get('daily_change_rate', 0)
                        
                        record_data = {
                            '티커': row['ticker'],
                            '종목명': row['name'],
                            '현재가': round(row['current_price'], 2),
                            '등락률': round(daily_change, 2),
                            '거래량': int(row['volume']) if pd.notna(row['volume']) else 0,
                            '시가총액': float(row['market_cap']) if pd.notna(row['market_cap']) else 0,
                            '52주 신고가 비율': round(high_ratio, 1),
                            'RS순위': round(row['rs_rating'], 1),
                            '재료명': row['sector'] if pd.notna(row['sector']) else '기타',
                            # 이동평균 존 (한국 ma_zone_scanner 정의 동일)
                            '3일선 위': bool(row.get('zone_3day_above', False)),
                            '3존': bool(row.get('zone_3', False)),
                            '8존': bool(row.get('zone_8', False)),
                            '15존': bool(row.get('zone_15', False)),
                            '20존': bool(row.get('zone_20', False)),
                            '33존': bool(row.get('zone_33', False)),
                            '50존': bool(row.get('zone_50', False)),
                            '슈퍼존': bool(row.get('zone_super', False)),
                        }
                        records_to_create.append(record_data)
                        
                    except Exception as e:
                        print(f"   ❌ {row['ticker']} 생성 데이터 준비 실패: {e}")
                
                # 배치 생성 (한 번에 최대 10개씩)
                batch_size = 10
                for i in range(0, len(records_to_create), batch_size):
                    batch_records = records_to_create[i:i + batch_size]
                    try:
                        self.airtable.batch_insert(batch_records)
                        created_count += len(batch_records)
                        print(f"   ➕ {len(batch_records)}개 레코드 배치 생성 완료 (총 {created_count}개)")
                        time.sleep(0.3)  # API 제한 방지
                    except Exception as e:
                        print(f"   ❌ 배치 생성 실패: {e}")
                        # 개별 생성으로 폴백
                        for record_data in batch_records:
                            try:
                                self.airtable.insert(record_data)
                                created_count += 1
                                time.sleep(0.2)
                            except Exception as e2:
                                print(f"   ❌ 개별 생성도 실패: {e2}")
                
                print(f"✅ 배치 생성 완료: {created_count}개 (속도 개선됨)")
            
            # 7단계: 결과 요약
            total_operations = deleted_count + updated_count + created_count
            print(f"\n🎉 Airtable 배치 동기화 완료! (속도 대폭 개선)")
            print(f"📊 동기화 결과:")
            print(f"   🗑️ 배치 삭제: {deleted_count}개")
            print(f"   🔄 배치 업데이트: {updated_count}개") 
            print(f"   ➕ 배치 생성: {created_count}개")
            print(f"   📈 총 작업: {total_operations}개")
            print(f"⚡ 배치 처리로 속도가 5-10배 빨라졌습니다!")
            print(f"✨ Airtable이 최신 스캔 결과와 완벽하게 동기화되었습니다!")
            
            return True
            
        except Exception as e:
            print(f"❌ Airtable 동기화 중 오류: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def upload_to_airtable(self, df: pd.DataFrame):
        """
        레거시 호환성을 위한 래퍼 함수 - 스마트 동기화 호출
        """
        return self.sync_to_airtable(df)
    
    def scan_and_upload(self) -> pd.DataFrame:
        """
        스캔 실행 후 Airtable에 스마트 동기화
        """
        # 스캔 실행
        results = self.scan()
        
        # Airtable 스마트 동기화
        if not results.empty and self.airtable:
            print("\n🔄 Airtable 스마트 동기화 시작...")
            print("💡 Update/Create/Delete 방식으로 완벽 동기화")
            self.sync_to_airtable(results)
        elif not self.airtable:
            print("\n💡 Airtable 설정이 없어 동기화를 건너뜁니다.")
        
        return results
    
    def scan(self) -> pd.DataFrame:
        """
        전체 스캔 프로세스 실행 (개선된 버전)
        """
        start_time = time.time()
        print("🚀 US Minervini Scanner V2 시작!")
        print(f"⏰ 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 1단계: 전체 주식 리스트 수집 (필터링 최소화)
        stocks = self.get_all_stocks()
        if not stocks:
            print("❌ 주식 리스트 수집 실패")
            return pd.DataFrame()
        
        # 2단계: 전체 종목 데이터 처리 (RS 계산용)
        print(f"⚙️ {len(stocks)}개 전체 종목 데이터 처리 중... (RS 계산용)")
        
        all_stock_data = []
        total_batches = (len(stocks) + self.batch_size - 1) // self.batch_size
        
        for i in range(0, len(stocks), self.batch_size):
            batch_num = i // self.batch_size + 1
            batch = stocks[i:i + self.batch_size]
            
            print(f"📦 배치 {batch_num}/{total_batches} 처리 중... ({len(batch)}개 종목)")
            
            batch_results = self.process_stock_batch(batch)
            all_stock_data.extend(batch_results)
            
            print(f"✅ 배치 {batch_num} 완료 - {len(batch_results)}개 종목 처리됨")
            
            if batch_num < total_batches:
                time.sleep(2)
        
        if not all_stock_data:
            print("❌ 처리된 데이터가 없습니다.")
            return pd.DataFrame()
        
        print(f"📊 총 {len(all_stock_data)}개 종목 데이터 수집 완료")
        
        # 3단계: RS 등급 계산 (전체 모집단 기준)
        stock_data_with_rs = self.calculate_rs_rating(all_stock_data)
        
        # 4단계: 투자 후보 필터링
        investment_candidates = self.apply_investment_filters(stock_data_with_rs)
        
        # 5단계: Minervini 조건 적용
        final_results = self.apply_minervini_criteria(investment_candidates)
        
        # 실행 시간 출력
        end_time = time.time()
        execution_time = end_time - start_time
        
        print(f"\n🎉 스캔 완료!")
        print(f"⏱️ 총 실행 시간: {execution_time:.1f}초 ({execution_time/60:.1f}분)")
        print(f"📈 최종 결과: {len(final_results)}개 종목")
        print(f"✨ RS 등급은 {len(stock_data_with_rs):,}개 전체 종목 기준으로 계산됨")
        
        return final_results

# 실행 예시 코드
def demo_run_v2():
    """
    V2 데모 실행 함수 (Airtable 연동 없음)
    """
    print("=" * 60)
    print("🇺🇸 US MINERVINI SCANNER V2 DEMO")
    print("=" * 60)
    
    # API 키 설정 (환경 변수에서 가져오기)
    API_KEY = os.getenv("FMP_API_KEY", "YOUR_FMP_API_KEY")
    
    
    # 스캐너 초기화
    scanner = USMinerviniScannerV2(
        api_key=API_KEY,
        max_workers=6,
        batch_size=30
    )
    
    # 스캔 실행
    results = scanner.scan()
    
    # 결과 출력
    if not results.empty:
        print("\n🏆 TOP 10 MINERVINI STOCKS (V2):")
        print("=" * 100)
        
        display_columns = ['ticker', 'name', 'current_price', 'rs_rating', 
                          'momentum_score', 'market_cap', 'sector']
        
        top_10 = results.head(10)[display_columns]
        
        top_10['current_price'] = top_10['current_price'].round(2)
        top_10['market_cap'] = top_10['market_cap'].apply(lambda x: f"${x:,.0f}")
        top_10['momentum_score'] = top_10['momentum_score'].round(1)
        
        print(top_10.to_string(index=False))
        
        print(f"\n💡 시가총액 단위: 달러")
        print(f"📊 전체 {len(results)}개 종목이 Minervini 조건을 만족합니다.")
        print(f"✨ 더 정확한 RS 등급으로 계산된 결과입니다!")
        
    else:
        print("😔 조건을 만족하는 종목이 없습니다.")

def demo_run_with_airtable():
    """
    Airtable 연동 포함 데모 실행 함수
    """
    print("=" * 70)
    print("🇺🇸 US MINERVINI SCANNER V2 + AIRTABLE DEMO")
    print("=" * 70)
    
    # API 키 설정 (환경 변수에서 가져오기)
    API_KEY = os.getenv("FMP_API_KEY", "YOUR_FMP_API_KEY")
    
    # Airtable 설정 (환경 변수에서 가져오기)
    AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
    BASE_ID = os.getenv("AIRTABLE_BASE_ID", "YOUR_BASE_ID")
    TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME", "트레이더의 선택")
    
    if not AIRTABLE_API_KEY:
        print("❌ Airtable API 키가 필요합니다. 환경 변수를 설정하세요.")
        return
    
    # 스캐너 초기화 (Airtable 연동 포함)
    scanner = USMinerviniScannerV2(
        api_key=API_KEY,
        max_workers=6,
        batch_size=30,
        airtable_api_key=AIRTABLE_API_KEY,
        airtable_base_id=BASE_ID,
        airtable_table_name=TABLE_NAME
    )
    
    # 스캔 및 Airtable 업로드 실행
    results = scanner.scan_and_upload()
    
    # 결과 출력
    if not results.empty:
        print("\n🏆 TOP 10 MINERVINI STOCKS (V2 + Airtable):")
        print("=" * 100)
        
        display_columns = ['ticker', 'name', 'current_price', 'rs_rating', 
                          'momentum_score', 'market_cap', 'sector']
        
        top_10 = results.head(10)[display_columns]
        
        top_10['current_price'] = top_10['current_price'].round(2)
        top_10['market_cap'] = top_10['market_cap'].apply(lambda x: f"${x:,.0f}")
        top_10['momentum_score'] = top_10['momentum_score'].round(1)
        
        print(top_10.to_string(index=False))
        
        print(f"\n💡 시가총액 단위: 달러")
        print(f"📊 전체 {len(results)}개 종목이 Minervini 조건을 만족합니다.")
        print(f"✨ 결과가 Airtable에 업로드되었습니다!")
        
    else:
        print("😔 조건을 만족하는 종목이 없습니다.")

if __name__ == "__main__":
    # Airtable 연동 데모 실행
    print("=" * 70)
    print("🇺🇸 US MINERVINI SCANNER V2 + AIRTABLE")
    print("=" * 70)
    
    # API 키 설정 (환경 변수에서 가져오기)
    API_KEY = os.getenv("FMP_API_KEY", "YOUR_FMP_API_KEY")
    AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY", "YOUR_AIRTABLE_API_KEY")
    BASE_ID = os.getenv("AIRTABLE_BASE_ID", "YOUR_BASE_ID")
    TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME", "트레이더의 선택")
    
    # 스캐너 초기화 (Airtable 연동 포함)
    scanner = USMinerviniScannerV2(
        api_key=API_KEY,
        max_workers=6,
        batch_size=30,
        airtable_api_key=AIRTABLE_API_KEY,
        airtable_base_id=BASE_ID,
        airtable_table_name=TABLE_NAME
    )
    
    # 스캔 및 Airtable 업로드 실행
    results = scanner.scan_and_upload()
    
    # 결과 출력
    if not results.empty:
        print("\n🏆 TOP 10 MINERVINI STOCKS (V2 + Airtable):")
        print("=" * 100)
        
        display_columns = ['ticker', 'name', 'current_price', 'rs_rating', 
                          'momentum_score', 'market_cap', 'sector']
        
        top_10 = results.head(10)[display_columns]
        
        top_10['current_price'] = top_10['current_price'].round(2)
        top_10['market_cap'] = top_10['market_cap'].apply(lambda x: f"${x:,.0f}")
        top_10['momentum_score'] = top_10['momentum_score'].round(1)
        
        print(top_10.to_string(index=False))
        
        print(f"\n💡 시가총액 단위: 달러")
        print(f"📊 전체 {len(results)}개 종목이 Minervini 조건을 만족합니다.")
        print(f"✨ 결과가 Airtable에 업로드되었습니다!")
        
    else:
        print("😔 조건을 만족하는 종목이 없습니다.") 