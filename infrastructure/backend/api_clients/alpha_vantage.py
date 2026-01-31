"""
Alpha Vantage API Client
Fallback data source - FREE but RATE LIMITED (5 calls/minute on free tier)
"""

import os
import requests
from typing import Dict, List, Optional


class AlphaVantageClient:
    """Client for Alpha Vantage API - rate limited fallback"""
    
    def __init__(self):
        self.api_key = os.environ.get('FINANCIAL_API_KEY', 'demo')
        self.base_url = "https://www.alphavantage.co/query"
    
    def fetch_overview(self, symbol: str) -> Optional[Dict]:
        """Fetch company overview from Alpha Vantage"""
        try:
            params = {
                'function': 'OVERVIEW',
                'symbol': symbol,
                'apikey': self.api_key
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data and 'Symbol' in data:
                    return data
            return None
        except Exception as e:
            print(f"Alpha Vantage error for {symbol}: {str(e)}")
            return None
    
    def fetch_quote(self, symbol: str) -> Optional[Dict]:
        """Fetch real-time quote from Alpha Vantage"""
        try:
            params = {
                'function': 'GLOBAL_QUOTE',
                'symbol': symbol,
                'apikey': self.api_key
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('Global Quote', {})
            return None
        except Exception as e:
            print(f"Alpha Vantage quote error for {symbol}: {str(e)}")
            return None
    
    def fetch_earnings(self, symbol: str) -> Optional[Dict]:
        """Fetch earnings data from Alpha Vantage"""
        try:
            params = {
                'function': 'EARNINGS',
                'symbol': symbol,
                'apikey': self.api_key
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return data
            return None
        except Exception as e:
            print(f"Alpha Vantage earnings error for {symbol}: {str(e)}")
            return None
    
    def fetch_income_statement(self, symbol: str) -> Optional[Dict]:
        """Fetch income statement from Alpha Vantage"""
        try:
            params = {
                'function': 'INCOME_STATEMENT',
                'symbol': symbol,
                'apikey': self.api_key
            }
            response = requests.get(self.base_url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Alpha Vantage income statement error: {str(e)}")
            return None
    
    def fetch_balance_sheet(self, symbol: str) -> Optional[Dict]:
        """Fetch balance sheet from Alpha Vantage"""
        try:
            params = {
                'function': 'BALANCE_SHEET',
                'symbol': symbol,
                'apikey': self.api_key
            }
            response = requests.get(self.base_url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Alpha Vantage balance sheet error: {str(e)}")
            return None
    
    def fetch_cash_flow(self, symbol: str) -> Optional[Dict]:
        """Fetch cash flow from Alpha Vantage"""
        try:
            params = {
                'function': 'CASH_FLOW',
                'symbol': symbol,
                'apikey': self.api_key
            }
            response = requests.get(self.base_url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Alpha Vantage cash flow error: {str(e)}")
            return None
    
    def parse_metrics(self, data: Dict) -> Dict:
        """Parse Alpha Vantage data into standard metrics format"""
        metrics = {}
        
        try:
            def safe_float(value, default=0):
                try:
                    return float(value) if value and value != 'None' else default
                except:
                    return default
            
            metrics['company_name'] = data.get('Name', 'N/A')
            metrics['market_cap'] = safe_float(data.get('MarketCapitalization'))
            metrics['pe_ratio'] = safe_float(data.get('PERatio'))
            metrics['forward_pe'] = safe_float(data.get('ForwardPE'))
            metrics['peg_ratio'] = safe_float(data.get('PEGRatio'))
            metrics['price_to_book'] = safe_float(data.get('PriceToBookRatio'))
            metrics['dividend_yield'] = safe_float(data.get('DividendYield'))
            metrics['52_week_high'] = safe_float(data.get('52WeekHigh'))
            metrics['52_week_low'] = safe_float(data.get('52WeekLow'))
            metrics['50_day_avg'] = safe_float(data.get('50DayMovingAverage'))
            metrics['200_day_avg'] = safe_float(data.get('200DayMovingAverage'))
            metrics['beta'] = safe_float(data.get('Beta'))
            metrics['eps'] = safe_float(data.get('EPS'))
            metrics['revenue_per_share'] = safe_float(data.get('RevenuePerShareTTM'))
            metrics['profit_margin'] = safe_float(data.get('ProfitMargin'))
            metrics['operating_margin'] = safe_float(data.get('OperatingMarginTTM'))
            metrics['roe'] = safe_float(data.get('ReturnOnEquityTTM'))
            metrics['roa'] = safe_float(data.get('ReturnOnAssetsTTM'))
            metrics['revenue_growth_yoy'] = safe_float(data.get('QuarterlyRevenueGrowthYOY'))
            metrics['earnings_growth_yoy'] = safe_float(data.get('QuarterlyEarningsGrowthYOY'))
            
        except Exception as e:
            print(f"Error parsing Alpha Vantage metrics: {str(e)}")
        
        return metrics
    
    def parse_price(self, data: Dict) -> Dict:
        """Parse Alpha Vantage quote data"""
        price_info = {}
        try:
            price_info['price'] = float(data.get('05. price', 0))
            price_info['volume'] = int(data.get('06. volume', 0))
            price_info['previous_close'] = float(data.get('08. previous close', 0))
            price_info['change'] = float(data.get('09. change', 0))
            price_info['change_percent'] = float(data.get('10. change percent', '0').replace('%', ''))
            price_info['timestamp'] = data.get('07. latest trading day', '')
        except Exception as e:
            print(f"Error parsing Alpha Vantage price: {str(e)}")
        
        return price_info
    
    def parse_estimates(self, data: Dict) -> Dict:
        """Parse Alpha Vantage earnings data"""
        estimates = {}
        try:
            quarterly_earnings = data.get('quarterlyEarnings', [])
            
            earnings_list = []
            for quarter in quarterly_earnings[:4]:  # Last 4 quarters
                earnings_list.append({
                    'period': quarter.get('fiscalDateEnding', ''),
                    'reported_eps': float(quarter.get('reportedEPS', 0)),
                    'estimated_eps': float(quarter.get('estimatedEPS', 0)),
                    'surprise': float(quarter.get('surprise', 0)),
                    'surprise_percent': float(quarter.get('surprisePercentage', 0))
                })
            
            estimates['earnings_estimates'] = earnings_list
            
        except Exception as e:
            print(f"Error parsing Alpha Vantage estimates: {str(e)}")
        
        return estimates
    
    def parse_income(self, data: Dict) -> List[Dict]:
        """Parse Alpha Vantage income statement"""
        statements = []
        try:
            annual_reports = data.get('annualReports', [])
            for report in annual_reports[:5]:  # Last 5 years
                statements.append({
                    'fiscal_date': report.get('fiscalDateEnding', ''),
                    'revenue': int(report.get('totalRevenue', 0)),
                    'cost_of_revenue': int(report.get('costOfRevenue', 0)),
                    'gross_profit': int(report.get('grossProfit', 0)),
                    'operating_expenses': int(report.get('operatingExpenses', 0)),
                    'operating_income': int(report.get('operatingIncome', 0)),
                    'net_income': int(report.get('netIncome', 0)),
                    'ebitda': int(report.get('ebitda', 0)),
                    'eps': float(report.get('eps', 0))
                })
        except Exception as e:
            print(f"Error parsing income statement: {str(e)}")
        return statements
    
    def parse_balance(self, data: Dict) -> List[Dict]:
        """Parse Alpha Vantage balance sheet"""
        statements = []
        try:
            annual_reports = data.get('annualReports', [])
            for report in annual_reports[:5]:
                statements.append({
                    'fiscal_date': report.get('fiscalDateEnding', ''),
                    'total_assets': int(report.get('totalAssets', 0)),
                    'current_assets': int(report.get('totalCurrentAssets', 0)),
                    'total_liabilities': int(report.get('totalLiabilities', 0)),
                    'current_liabilities': int(report.get('totalCurrentLiabilities', 0)),
                    'shareholders_equity': int(report.get('totalShareholderEquity', 0)),
                    'cash': int(report.get('cashAndCashEquivalentsAtCarryingValue', 0)),
                    'debt': int(report.get('shortLongTermDebtTotal', 0))
                })
        except Exception as e:
            print(f"Error parsing balance sheet: {str(e)}")
        return statements
    
    def parse_cashflow(self, data: Dict) -> List[Dict]:
        """Parse Alpha Vantage cash flow statement"""
        statements = []
        try:
            annual_reports = data.get('annualReports', [])
            for report in annual_reports[:5]:
                statements.append({
                    'fiscal_date': report.get('fiscalDateEnding', ''),
                    'operating_cashflow': int(report.get('operatingCashflow', 0)),
                    'capex': int(report.get('capitalExpenditures', 0)),
                    'free_cash_flow': int(report.get('operatingCashflow', 0)) - abs(int(report.get('capitalExpenditures', 0))),
                    'dividends_paid': int(report.get('dividendPayout', 0))
                })
        except Exception as e:
            print(f"Error parsing cash flow: {str(e)}")
        return statements
