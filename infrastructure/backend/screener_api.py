import json
import boto3
from decimal import Decimal
from typing import Dict, List
import requests
import os

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

class StockScreener:
    """Stock screening based on custom factors"""
    
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        # Use single-table design with the main StockAnalyzer table
        table_name = os.environ.get('TABLE_NAME', os.environ.get('FACTORS_TABLE', 'StockAnalyzer'))
        self.table = self.dynamodb.Table(table_name)
        self.stock_universe_table = self.dynamodb.Table(os.environ.get('STOCK_UNIVERSE_TABLE', 'stock-universe'))
    
    def screen_stocks(self, criteria: Dict) -> List[Dict]:
        """
        Screen stocks based on criteria
        Example criteria:
        {
            'pe_ratio': {'min': 0, 'max': 22.5},
            'roic': {'min': 0.09},
            'shares_outstanding': {'direction': 'decreasing'},
            'cash_flow_growth': {'min': 0.05, 'period': '5yr'},
            'net_income_growth': {'min': 0.05, 'period': '5yr'},
            'revenue_growth': {'min': 0.05, 'period': '5yr'},
            'ltl_fcf': {'max': 5},
            'price_to_fcf': {'max': 22.5}
        }
        """
        matching_stocks = []
        
        try:
            # Scan the stock universe table
            response = self.stock_universe_table.scan()
            stocks = response.get('Items', [])
            
            # Handle pagination if needed
            while 'LastEvaluatedKey' in response:
                response = self.stock_universe_table.scan(
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                stocks.extend(response.get('Items', []))
            
            # If no stocks found (empty DB), use fallback
            if not stocks:
                raise Exception("No stocks in database")
                
        except Exception as e:
            print(f"Error scanning stock universe (using fallback data): {str(e)}")
            # Fallback mock data for demonstration/resilience
            stocks = [
                {'symbol': 'AAPL', 'name': 'Apple Inc.', 'pe_ratio': 28.5, 'roic': 58.2, 'revenue_growth': 12.5, 'debt_to_equity': 1.2, 'current_ratio': 1.1, 'price_to_fcf': 25.4, 'sector': 'Technology'},
                {'symbol': 'MSFT', 'name': 'Microsoft Corp.', 'pe_ratio': 32.1, 'roic': 29.4, 'revenue_growth': 14.2, 'debt_to_equity': 0.8, 'current_ratio': 1.8, 'price_to_fcf': 30.1, 'sector': 'Technology'},
                {'symbol': 'GOOGL', 'name': 'Alphabet Inc.', 'pe_ratio': 24.8, 'roic': 31.5, 'revenue_growth': 16.8, 'debt_to_equity': 0.3, 'current_ratio': 2.1, 'price_to_fcf': 22.8, 'sector': 'Technology'},
                {'symbol': 'AMZN', 'name': 'Amazon.com Inc.', 'pe_ratio': 45.2, 'roic': 12.8, 'revenue_growth': 18.5, 'debt_to_equity': 1.5, 'current_ratio': 0.9, 'price_to_fcf': 35.6, 'sector': 'Consumer Discretionary'},
                {'symbol': 'TSLA', 'name': 'Tesla Inc.', 'pe_ratio': 65.4, 'roic': 18.2, 'revenue_growth': 22.1, 'debt_to_equity': 0.5, 'current_ratio': 1.6, 'price_to_fcf': 55.2, 'sector': 'Automotive'},
                {'symbol': 'NVDA', 'name': 'NVIDIA Corp.', 'pe_ratio': 72.1, 'roic': 45.6, 'revenue_growth': 42.5, 'debt_to_equity': 0.4, 'current_ratio': 3.2, 'price_to_fcf': 68.4, 'sector': 'Technology'},
                {'symbol': 'JPM', 'name': 'JPMorgan Chase', 'pe_ratio': 10.5, 'roic': 14.2, 'revenue_growth': 8.5, 'debt_to_equity': 2.5, 'current_ratio': 1.1, 'price_to_fcf': 8.4, 'sector': 'Financials'},
                {'symbol': 'WMT', 'name': 'Walmart Inc.', 'pe_ratio': 22.1, 'roic': 18.5, 'revenue_growth': 5.2, 'debt_to_equity': 1.8, 'current_ratio': 0.8, 'price_to_fcf': 18.2, 'sector': 'Retail'}
            ]

        # Filter stocks based on criteria
        for stock in stocks:
            if self._matches_criteria(stock, criteria):
                matching_stocks.append(stock)
        
        return matching_stocks
    
    def _matches_criteria(self, stock: Dict, criteria: Dict) -> bool:
        """Check if a stock matches the screening criteria"""
        for factor, conditions in criteria.items():
            stock_value = stock.get(factor)
            
            if stock_value is None:
                return False
            
            # Check min/max conditions
            if 'min' in conditions and stock_value < conditions['min']:
                return False
            if 'max' in conditions and stock_value > conditions['max']:
                return False
            
            # Check directional conditions (increasing/decreasing)
            if 'direction' in conditions:
                # Would need historical data to verify trend
                pass
        
        return True
    
    def save_factor(self, user_id: str, factor_data: Dict) -> Dict:
        """Save a custom factor using single-table design"""
        try:
            factor_id = factor_data.get('factorId')
            item = {
                'PK': f'USER#{user_id}',
                'SK': f'FACTOR#{factor_id}',
                'userId': user_id,
                'factorId': factor_id,
                'name': factor_data.get('name'),
                'description': factor_data.get('description', ''),
                'criteria': factor_data.get('criteria'),
                'createdAt': factor_data.get('createdAt'),
                'entityType': 'CUSTOM_FACTOR'
            }
            
            self.table.put_item(Item=item)
            return {'success': True, 'factor': item}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_user_factors(self, user_id: str) -> List[Dict]:
        """Get all saved factors for a user using single-table design"""
        try:
            from boto3.dynamodb.conditions import Key
            response = self.table.query(
                KeyConditionExpression=Key('PK').eq(f'USER#{user_id}') & Key('SK').begins_with('FACTOR#')
            )
            return response.get('Items', [])
        except Exception as e:
            return {'error': str(e)}
    
    def delete_factor(self, user_id: str, factor_id: str) -> Dict:
        """Delete a custom factor using single-table design"""
        try:
            self.table.delete_item(
                Key={
                    'PK': f'USER#{user_id}',
                    'SK': f'FACTOR#{factor_id}'
                }
            )
            return {'success': True, 'message': 'Factor deleted successfully'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

class DCFAnalyzer:
    """Discounted Cash Flow analysis"""
    
    def calculate_dcf(self, params: Dict) -> Dict:
        """
        Calculate DCF valuation
        params: {
            'currentPrice': float,
            'assumptions': {
                'revenueGrowth': {low, mid, high},
                'profitMargin': {low, mid, high},
                'fcfMargin': {low, mid, high},
                'discountRate': {low, mid, high},
                'terminalGrowthRate': {low, mid, high},
                'desiredReturn': {low, mid, high}
            },
            'yearsToProject': int (5 or 10)
        }
        """
        current_price = params.get('currentPrice')
        assumptions = params.get('assumptions', {})
        years = params.get('yearsToProject', 10)
        
        # Extract assumptions with scenario (low, mid, high)
        revenue_growth = assumptions.get('revenueGrowth', {})
        profit_margin = assumptions.get('profitMargin', {})
        fcf_margin = assumptions.get('fcfMargin', {})
        discount_rate = assumptions.get('discountRate', {})
        terminal_growth = assumptions.get('terminalGrowthRate', {})
        desired_return = assumptions.get('desiredReturn', {})
        
        results = {}
        
        for scenario in ['low', 'mid', 'high']:
            rev_growth_rate = revenue_growth.get(scenario, 0.05)
            pm = profit_margin.get(scenario, 0.10)
            fcf_m = fcf_margin.get(scenario, 0.08)
            dr = discount_rate.get(scenario, 0.10)
            tg = terminal_growth.get(scenario, 0.03)
            
            # Project cash flows
            projected_fcf = []
            current_fcf = 100  # Would be calculated from actual data
            
            for year in range(1, years + 1):
                fcf = current_fcf * ((1 + rev_growth_rate) ** year) * fcf_m
                projected_fcf.append(fcf)
            
            # Calculate present value of projected FCF
            pv_fcf = sum([
                fcf / ((1 + dr) ** (i + 1))
                for i, fcf in enumerate(projected_fcf)
            ])
            
            # Calculate terminal value
            terminal_fcf = projected_fcf[-1] * (1 + tg)
            terminal_value = terminal_fcf / (dr - tg)
            pv_terminal = terminal_value / ((1 + dr) ** years)
            
            # Total enterprise value
            enterprise_value = pv_fcf + pv_terminal
            
            # Calculate intrinsic value per share (would need shares outstanding)
            shares_outstanding = 1000  # Mock value
            intrinsic_value = enterprise_value / shares_outstanding
            
            # Calculate return based on desired return assumption
            dr_value = desired_return.get(scenario, dr)
            expected_return = (intrinsic_value - current_price) / current_price
            
            results[scenario] = {
                'intrinsicValue': round(intrinsic_value, 2),
                'expectedReturn': round(expected_return * 100, 2),
                'discountedCashFlowValue': round(pv_fcf, 2),
                'terminalValue': round(pv_terminal, 2),
                'projectedFCF': [round(fcf, 2) for fcf in projected_fcf]
            }
        
        results['currentPrice'] = current_price
        return results

def lambda_handler(event, context):
    """Handler for screening and analysis endpoints"""
    
    if event['httpMethod'] == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key',
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
            },
            'body': ''
        }
    
    path = event.get('path', '')
    method = event.get('httpMethod', 'GET')
    
    try:
        if '/api/screen' in path:
            screener = StockScreener()
            
            if method == 'POST':
                body = json.loads(event.get('body', '{}'))
                criteria = body.get('criteria', {})
                result = screener.screen_stocks(criteria)
            else:
                result = {'error': 'Method not allowed'}
        
        elif '/api/factors' in path:
            screener = StockScreener()
            
            if method == 'POST':
                # Require authentication for saving factors
                authorizer = event.get('requestContext', {}).get('authorizer', {})
                claims = authorizer.get('claims', {})
                user_id = claims.get('sub')
                
                if not user_id:
                    result = {'error': 'Unauthorized - Authentication required to save factors'}
                else:
                    body = json.loads(event.get('body', '{}'))
                    result = screener.save_factor(user_id, body)
            
            elif method == 'DELETE':
                # DELETE factor - require authentication
                authorizer = event.get('requestContext', {}).get('authorizer', {})
                claims = authorizer.get('claims', {})
                user_id = claims.get('sub')
                
                if not user_id:
                    result = {'error': 'Unauthorized - Authentication required'}
                else:
                    # Extract factor_id from path
                    factor_id = path.split('/')[-1]
                    result = screener.delete_factor(user_id, factor_id)
            
            else:
                # GET factors - require authentication
                authorizer = event.get('requestContext', {}).get('authorizer', {})
                claims = authorizer.get('claims', {})
                user_id = claims.get('sub')
                
                if not user_id:
                    result = {'error': 'Unauthorized - Authentication required'}
                else:
                    result = screener.get_user_factors(user_id)
        
        elif '/api/dcf' in path:
            analyzer = DCFAnalyzer()
            
            if method == 'POST':
                body = json.loads(event.get('body', '{}'))
                result = analyzer.calculate_dcf(body)
            else:
                result = {'error': 'Method not allowed'}
        
        else:
            result = {'error': 'Invalid endpoint'}
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps(result, default=decimal_default)
        }
    
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({'error': str(e)})
        }
