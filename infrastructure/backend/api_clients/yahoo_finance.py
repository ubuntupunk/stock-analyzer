"""
Yahoo Finance API Client
Primary data source - FREE, no API key required, no rate limits
"""

import requests
import aiohttp
from typing import Dict, List, Optional


class YahooFinanceClient:
    """Client for Yahoo Finance API - unofficial but reliable"""
    
    def __init__(self):
        self.base_url = "https://query2.finance.yahoo.com/v10/finance/quoteSummary"
    
    def fetch_data(self, symbol: str, modules: str = None) -> Optional[Dict]:
        """
        Fetch data from Yahoo Finance with specified modules
        
        Default modules include: price, summaryDetail, defaultKeyStatistics, financialData, 
        earningsTrend, incomeStatementHistory, balanceSheetHistory, cashflowStatementHistory
        
        This unified method fetches ALL data in a single request to minimize API calls.
        """
        try:
            url = f"{self.base_url}/{symbol}"
            
            # Default: fetch ALL modules in one request for maximum efficiency
            if modules is None:
                modules = 'price,summaryDetail,defaultKeyStatistics,financialData,earningsTrend,incomeStatementHistory,balanceSheetHistory,cashflowStatementHistory'
            
            params = {'modules': modules}
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                result = data.get('quoteSummary', {}).get('result', [])
                if result:
                    return result[0]
            return None
        except Exception as e:
            print(f"YFinance error for {symbol}: {str(e)}")
            return None
    
    async def fetch_data_async(self, session: aiohttp.ClientSession, symbol: str, modules: str = None) -> tuple:
        """
        Async version of fetch_data for concurrent requests
        Returns: (symbol, data) tuple
        """
        try:
            url = f"{self.base_url}/{symbol}"
            
            if modules is None:
                modules = 'price,summaryDetail,defaultKeyStatistics,financialData,earningsTrend,incomeStatementHistory,balanceSheetHistory,cashflowStatementHistory'
            
            params = {'modules': modules}
            
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    result = data.get('quoteSummary', {}).get('result', [])
                    if result:
                        return (symbol, result[0])
            return (symbol, None)
        except Exception as e:
            print(f"YFinance async error for {symbol}: {str(e)}")
            return (symbol, None)
    
    def parse_price(self, data: Dict) -> Dict:
        """Parse Yahoo Finance price data"""
        price_info = {}
        try:
            price_data = data.get('price', {})
            
            def get_value(obj, default=0):
                if isinstance(obj, dict):
                    return obj.get('raw', default)
                return obj or default
            
            price_info['price'] = get_value(price_data.get('regularMarketPrice'), 0)
            price_info['open'] = get_value(price_data.get('regularMarketOpen'), 0)
            price_info['high'] = get_value(price_data.get('regularMarketDayHigh'), 0)
            price_info['low'] = get_value(price_data.get('regularMarketDayLow'), 0)
            price_info['volume'] = get_value(price_data.get('regularMarketVolume'), 0)
            price_info['previous_close'] = get_value(price_data.get('regularMarketPreviousClose'), 0)
            price_info['change'] = get_value(price_data.get('regularMarketChange'), 0)
            price_info['change_percent'] = get_value(price_data.get('regularMarketChangePercent'), 0)
        except Exception as e:
            print(f"Error parsing Yahoo Finance price: {str(e)}")
        
        return price_info
    
    def parse_metrics(self, data: Dict) -> Dict:
        """Parse Yahoo Finance data into standard metrics format"""
        metrics = {}
        
        try:
            price_data = data.get('price', {})
            summary = data.get('summaryDetail', {})
            key_stats = data.get('defaultKeyStatistics', {})
            financial = data.get('financialData', {})
            
            # Helper function to extract value
            def get_value(obj, default=None):
                if isinstance(obj, dict):
                    return obj.get('raw', default)
                return obj or default
            
            metrics['company_name'] = get_value(price_data.get('shortName'), 'N/A')
            metrics['current_price'] = get_value(price_data.get('regularMarketPrice'), 0)
            metrics['market_cap'] = get_value(price_data.get('marketCap'), 0)
            metrics['pe_ratio'] = get_value(summary.get('trailingPE'), 0)
            metrics['forward_pe'] = get_value(summary.get('forwardPE'), 0)
            metrics['peg_ratio'] = get_value(key_stats.get('pegRatio'), 0)
            metrics['price_to_book'] = get_value(key_stats.get('priceToBook'), 0)
            metrics['dividend_yield'] = get_value(summary.get('dividendYield'), 0)
            metrics['52_week_high'] = get_value(summary.get('fiftyTwoWeekHigh'), 0)
            metrics['52_week_low'] = get_value(summary.get('fiftyTwoWeekLow'), 0)
            metrics['50_day_avg'] = get_value(summary.get('fiftyDayAverage'), 0)
            metrics['200_day_avg'] = get_value(summary.get('twoHundredDayAverage'), 0)
            metrics['volume'] = get_value(price_data.get('regularMarketVolume'), 0)
            metrics['avg_volume'] = get_value(price_data.get('averageDailyVolume10Day'), 0)
            metrics['beta'] = get_value(key_stats.get('beta'), 0)
            metrics['eps'] = get_value(key_stats.get('trailingEps'), 0)
            metrics['revenue_growth'] = get_value(financial.get('revenueGrowth'), 0)
            metrics['earnings_growth'] = get_value(financial.get('earningsGrowth'), 0)
            metrics['profit_margin'] = get_value(financial.get('profitMargins'), 0)
            metrics['operating_margin'] = get_value(financial.get('operatingMargins'), 0)
            metrics['roe'] = get_value(financial.get('returnOnEquity'), 0)
            metrics['roa'] = get_value(financial.get('returnOnAssets'), 0)
            metrics['debt_to_equity'] = get_value(financial.get('debtToEquity'), 0)
            metrics['current_ratio'] = get_value(financial.get('currentRatio'), 0)
            metrics['free_cash_flow'] = get_value(financial.get('freeCashflow'), 0)
            metrics['operating_cash_flow'] = get_value(financial.get('operatingCashflow'), 0)
            
        except Exception as e:
            print(f"Error parsing Yahoo Finance metrics: {str(e)}")
        
        return metrics
    
    def parse_estimates(self, data: Dict) -> Dict:
        """Parse Yahoo Finance analyst estimates"""
        estimates = {}
        try:
            earnings_trend = data.get('earningsTrend', {}).get('trend', [])
            
            earnings_list = []
            revenue_list = []
            
            for trend in earnings_trend:
                period = trend.get('period', '')
                
                # Earnings estimates
                earnings_est = trend.get('earningsEstimate', {})
                if earnings_est:
                    earnings_list.append({
                        'period': period,
                        'avg': earnings_est.get('avg', {}).get('raw', 0),
                        'low': earnings_est.get('low', {}).get('raw', 0),
                        'high': earnings_est.get('high', {}).get('raw', 0),
                        'num_analysts': earnings_est.get('numberOfAnalysts', {}).get('raw', 0)
                    })
                
                # Revenue estimates
                revenue_est = trend.get('revenueEstimate', {})
                if revenue_est:
                    revenue_list.append({
                        'period': period,
                        'avg': revenue_est.get('avg', {}).get('raw', 0),
                        'low': revenue_est.get('low', {}).get('raw', 0),
                        'high': revenue_est.get('high', {}).get('raw', 0),
                        'num_analysts': revenue_est.get('numberOfAnalysts', {}).get('raw', 0)
                    })
            
            estimates['earnings_estimates'] = earnings_list
            estimates['revenue_estimates'] = revenue_list
            
        except Exception as e:
            print(f"Error parsing Yahoo Finance estimates: {str(e)}")
        
        return estimates
    
    def parse_financials(self, data: Dict) -> Dict:
        """Parse Yahoo Finance financial statements"""
        parsed = {}
        
        try:
            # Income Statement
            income_history = data.get('incomeStatementHistory', {}).get('incomeStatementHistory', [])
            income_statements = []
            for statement in income_history:
                stmt = statement.get('incomeStatement', {})
                income_statements.append({
                    'fiscal_date': statement.get('endDate', {}).get('fmt', ''),
                    'revenue': stmt.get('totalRevenue', {}).get('raw', 0),
                    'cost_of_revenue': stmt.get('costOfRevenue', {}).get('raw', 0),
                    'gross_profit': stmt.get('grossProfit', {}).get('raw', 0),
                    'operating_income': stmt.get('operatingIncome', {}).get('raw', 0),
                    'net_income': stmt.get('netIncome', {}).get('raw', 0),
                    'ebitda': stmt.get('ebitda', {}).get('raw', 0)
                })
            parsed['income_statement'] = income_statements
            
            # Balance Sheet
            balance_history = data.get('balanceSheetHistory', {}).get('balanceSheetStatements', [])
            balance_statements = []
            for statement in balance_history:
                stmt = statement.get('balanceSheet', {})
                balance_statements.append({
                    'fiscal_date': statement.get('endDate', {}).get('fmt', ''),
                    'total_assets': stmt.get('totalAssets', {}).get('raw', 0),
                    'current_assets': stmt.get('totalCurrentAssets', {}).get('raw', 0),
                    'total_liabilities': stmt.get('totalLiab', {}).get('raw', 0),
                    'current_liabilities': stmt.get('totalCurrentLiabilities', {}).get('raw', 0),
                    'shareholders_equity': stmt.get('totalStockholderEquity', {}).get('raw', 0),
                    'cash': stmt.get('cash', {}).get('raw', 0)
                })
            parsed['balance_sheet'] = balance_statements
            
            # Cash Flow
            cashflow_history = data.get('cashflowStatementHistory', {}).get('cashflowStatements', [])
            cashflow_statements = []
            for statement in cashflow_history:
                stmt = statement.get('cashflowStatement', {})
                operating_cf = stmt.get('totalCashFromOperatingActivities', {}).get('raw', 0)
                capex = stmt.get('capitalExpenditures', {}).get('raw', 0)
                cashflow_statements.append({
                    'fiscal_date': statement.get('endDate', {}).get('fmt', ''),
                    'operating_cashflow': operating_cf,
                    'capex': capex,
                    'free_cash_flow': operating_cf - abs(capex),
                    'dividends_paid': stmt.get('dividendsPaid', {}).get('raw', 0)
                })
            parsed['cash_flow'] = cashflow_statements
            
        except Exception as e:
            print(f"Error parsing Yahoo Finance financials: {str(e)}")
        
        return parsed
