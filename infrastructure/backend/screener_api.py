import json
import boto3
from decimal import Decimal
from typing import Dict, List, Tuple, Optional
import requests
import os

from logger_config import setup_logger

# Initialize logger
logger = setup_logger(__name__)


def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


class CriteriaValidator:
    """Validates screening criteria for logical consistency and valid ranges"""

    # Valid factor names that can be used in screening
    VALID_FACTORS = {
        "pe_ratio",
        "roic",
        "revenue_growth",
        "debt_to_equity",
        "current_ratio",
        "price_to_fcf",
        "profit_margin",
        "fcf_margin",
        "market_cap",
        "shares_outstanding",
        "cash_flow_growth",
        "net_income_growth",
        "ltl_fcf",
    }

    # Factor constraints: (min_allowed, max_allowed, is_percentage)
    FACTOR_CONSTRAINTS = {
        "pe_ratio": (0, 1000, False),
        "roic": (0, 100, True),  # Stored as decimal (0.15 = 15%)
        "revenue_growth": (-100, 1000, True),
        "debt_to_equity": (0, 100, False),
        "current_ratio": (0, 50, False),
        "price_to_fcf": (0, 1000, False),
        "profit_margin": (-100, 100, True),
        "fcf_margin": (-100, 100, True),
        "market_cap": (0, None, False),  # No upper limit
        "cash_flow_growth": (-100, 1000, True),
        "net_income_growth": (-100, 1000, True),
    }

    @classmethod
    def validate_criteria(cls, criteria: Dict) -> Tuple[bool, List[str], List[str]]:
        """
        Validate screening criteria for logical consistency.

        Returns:
            Tuple of (is_valid, errors, warnings)
            - is_valid: Boolean indicating if criteria can be used
            - errors: List of error messages (blocking issues)
            - warnings: List of warning messages (non-blocking suggestions)
        """
        errors = []
        warnings = []

        if not criteria:
            errors.append("No screening criteria provided")
            return False, errors, warnings

        if not isinstance(criteria, dict):
            errors.append("Criteria must be a dictionary")
            return False, errors, warnings

        # Check each factor in criteria
        for factor, conditions in criteria.items():
            # Validate factor name
            if factor not in cls.VALID_FACTORS:
                warnings.append(
                    f"Unknown factor '{factor}' - will be ignored if not present in stock data"
                )

            # Validate conditions structure
            if not isinstance(conditions, dict):
                errors.append(f"Conditions for '{factor}' must be a dictionary")
                continue

            # Check for valid condition keys
            valid_keys = {"min", "max", "direction", "period", "exact"}
            invalid_keys = set(conditions.keys()) - valid_keys
            if invalid_keys:
                warnings.append(
                    f"Factor '{factor}' has unknown condition keys: {', '.join(invalid_keys)}"
                )

            # Validate min/max values
            min_val = conditions.get("min")
            max_val = conditions.get("max")

            # Check for contradictory ranges
            if min_val is not None and max_val is not None:
                if min_val > max_val:
                    errors.append(
                        f"{factor}: Minimum value ({min_val}) cannot exceed maximum value ({max_val})"
                    )
                if min_val == max_val:
                    warnings.append(
                        f"{factor}: Minimum and maximum are both {min_val} - consider using 'exact' condition instead"
                    )

            # Validate against factor constraints
            if factor in cls.FACTOR_CONSTRAINTS:
                constraint_min, constraint_max, is_pct = cls.FACTOR_CONSTRAINTS[factor]

                for val, label in [(min_val, "minimum"), (max_val, "maximum")]:
                    if val is None:
                        continue
                    
                    cls._validate_constraint_bounds(
                        factor, val, label, constraint_min, constraint_max, is_pct, errors
                    )
                    cls._check_extreme_growth_values(
                        factor, val, label, is_pct, warnings
                    )

        # Check for impossible factor combinations
        cls._check_contradictory_factors(criteria, errors, warnings)

        return len(errors) == 0, errors, warnings

    @classmethod
    def _validate_constraint_bounds(
        cls, factor: str, val: float, label: str, 
        constraint_min: float, constraint_max: float, 
        is_pct: bool, errors: List[str]
    ) -> None:
        """Validate value against constraint bounds"""
        pct_label = "%" if is_pct else ""
        
        # Check minimum constraint
        if constraint_min is not None and val < constraint_min:
            errors.append(
                f"{factor}: {label} value ({val}{pct_label}) is below allowed minimum ({constraint_min}{pct_label})"
            )

        # Check maximum constraint
        if constraint_max is not None and val > constraint_max:
            errors.append(
                f"{factor}: {label} value ({val}{pct_label}) exceeds allowed maximum ({constraint_max}{pct_label})"
            )

    @classmethod
    def _check_extreme_growth_values(
        cls, factor: str, val: float, label: str, 
        is_pct: bool, warnings: List[str]
    ) -> None:
        """Check for extreme growth values that might limit results"""
        if not is_pct:
            return
            
        growth_factors = ["revenue_growth", "cash_flow_growth", "net_income_growth"]
        if factor not in growth_factors:
            return
            
        if val > 1.0:  # > 100%
            warnings.append(
                f"{factor}: {label} value ({val*100:.0f}%) is very high - results may be limited"
            )

    @classmethod
    def _check_contradictory_factors(
        cls, criteria: Dict, errors: List[str], warnings: List[str]
    ):
        """Check for logically contradictory factor combinations"""

        # Check for P/E and Price/FCF conflict (both measure valuation)
        pe_ratio = criteria.get("pe_ratio", {})
        price_to_fcf = criteria.get("price_to_fcf", {})

        if pe_ratio and price_to_fcf:
            pe_max = pe_ratio.get("max")
            pfcf_max = price_to_fcf.get("max")
            if pe_max and pfcf_max:
                # Very restrictive valuation criteria might yield no results
                if pe_max < 10 and pfcf_max < 10:
                    warnings.append(
                        "Very restrictive valuation criteria (P/E < 10 AND Price/FCF < 10) - may yield few results"
                    )

        # Check for growth vs profitability conflict
        revenue_growth = criteria.get("revenue_growth", {})
        profit_margin = criteria.get("profit_margin", {})

        if revenue_growth and profit_margin:
            growth_min = revenue_growth.get("min")
            margin_min = profit_margin.get("min")
            if growth_min and margin_min:
                if (
                    growth_min > 0.20 and margin_min > 0.20
                ):  # >20% growth AND >20% margin
                    warnings.append(
                        "High growth (>20%) AND high profit margin (>20%) criteria - rare combination"
                    )

        # Check for debt and current ratio conflict
        debt_to_equity = criteria.get("debt_to_equity", {})
        current_ratio = criteria.get("current_ratio", {})

        if debt_to_equity and current_ratio:
            de_max = debt_to_equity.get("max")
            cr_min = current_ratio.get("min")
            if de_max and cr_min:
                if de_max < 0.5 and cr_min > 2.0:
                    warnings.append(
                        "Very conservative financial health criteria - may yield few results"
                    )

    @classmethod
    def sanitize_criteria(cls, criteria: Dict) -> Dict:
        """Remove invalid factors and conditions from criteria"""
        sanitized = {}
        for factor, conditions in criteria.items():
            if factor not in cls.VALID_FACTORS:
                continue
            if not isinstance(conditions, dict):
                continue
            # Only keep valid condition keys
            sanitized_conditions = {
                condition_key: condition_value
                for condition_key, condition_value in conditions.items()
                if condition_key in {"min", "max", "direction", "period", "exact"}
            }
            if sanitized_conditions:
                sanitized[factor] = sanitized_conditions
        return sanitized


class StockScreener:
    """Stock screening based on custom factors"""

    def __init__(self):
        self.dynamodb = boto3.resource("dynamodb")
        # Use single-table design with the main StockAnalyzer table
        table_name = os.environ.get(
            "TABLE_NAME", os.environ.get("FACTORS_TABLE", "StockAnalyzer")
        )
        self.table = self.dynamodb.Table(table_name)
        self.stock_universe_table = self.dynamodb.Table(
            os.environ.get("STOCK_UNIVERSE_TABLE", "stock-universe")
        )

    def screen_stocks(self, criteria: Dict) -> Dict:
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

        Returns:
            Dict with 'stocks', 'validation', 'data_quality', and 'metadata' keys
        """
        # Validate criteria first
        is_valid, errors, warnings = CriteriaValidator.validate_criteria(criteria)

        if not is_valid:
            return {
                "stocks": [],
                "validation": {"valid": False, "errors": errors, "warnings": warnings},
                "data_quality": {},
                "metadata": {"total_stocks_checked": 0, "criteria_applied": criteria},
            }

        # Sanitize criteria to remove unknown factors
        sanitized_criteria = CriteriaValidator.sanitize_criteria(criteria)

        matching_stocks = []
        data_quality_issues = []
        stocks_checked = 0

        try:
            # Scan the stock universe table
            response = self.stock_universe_table.scan()
            stocks = response.get("Items", [])

            # Handle pagination if needed
            while "LastEvaluatedKey" in response:
                response = self.stock_universe_table.scan(
                    ExclusiveStartKey=response["LastEvaluatedKey"]
                )
                stocks.extend(response.get("Items", []))

            # If no stocks found (empty DB), use fallback
            if not stocks:
                raise Exception("No stocks in database")

        except Exception as err:
            logger.warning(f"Error scanning stock universe (using fallback data): {str(err)}")
            # Fallback mock data for demonstration/resilience
            stocks = [
                {
                    "symbol": "AAPL",
                    "name": "Apple Inc.",
                    "pe_ratio": 28.5,
                    "roic": 58.2,
                    "revenue_growth": 12.5,
                    "debt_to_equity": 1.2,
                    "current_ratio": 1.1,
                    "price_to_fcf": 25.4,
                    "sector": "Technology",
                },
                {
                    "symbol": "MSFT",
                    "name": "Microsoft Corp.",
                    "pe_ratio": 32.1,
                    "roic": 29.4,
                    "revenue_growth": 14.2,
                    "debt_to_equity": 0.8,
                    "current_ratio": 1.8,
                    "price_to_fcf": 30.1,
                    "sector": "Technology",
                },
                {
                    "symbol": "GOOGL",
                    "name": "Alphabet Inc.",
                    "pe_ratio": 24.8,
                    "roic": 31.5,
                    "revenue_growth": 16.8,
                    "debt_to_equity": 0.3,
                    "current_ratio": 2.1,
                    "price_to_fcf": 22.8,
                    "sector": "Technology",
                },
                {
                    "symbol": "AMZN",
                    "name": "Amazon.com Inc.",
                    "pe_ratio": 45.2,
                    "roic": 12.8,
                    "revenue_growth": 18.5,
                    "debt_to_equity": 1.5,
                    "current_ratio": 0.9,
                    "price_to_fcf": 35.6,
                    "sector": "Consumer Discretionary",
                },
                {
                    "symbol": "TSLA",
                    "name": "Tesla Inc.",
                    "pe_ratio": 65.4,
                    "roic": 18.2,
                    "revenue_growth": 22.1,
                    "debt_to_equity": 0.5,
                    "current_ratio": 1.6,
                    "price_to_fcf": 55.2,
                    "sector": "Automotive",
                },
                {
                    "symbol": "NVDA",
                    "name": "NVIDIA Corp.",
                    "pe_ratio": 72.1,
                    "roic": 45.6,
                    "revenue_growth": 42.5,
                    "debt_to_equity": 0.4,
                    "current_ratio": 3.2,
                    "price_to_fcf": 68.4,
                    "sector": "Technology",
                },
                {
                    "symbol": "JPM",
                    "name": "JPMorgan Chase",
                    "pe_ratio": 10.5,
                    "roic": 14.2,
                    "revenue_growth": 8.5,
                    "debt_to_equity": 2.5,
                    "current_ratio": 1.1,
                    "price_to_fcf": 8.4,
                    "sector": "Financials",
                },
                {
                    "symbol": "WMT",
                    "name": "Walmart Inc.",
                    "pe_ratio": 22.1,
                    "roic": 18.5,
                    "revenue_growth": 5.2,
                    "debt_to_equity": 1.8,
                    "current_ratio": 0.8,
                    "price_to_fcf": 18.2,
                    "sector": "Retail",
                },
            ]

        # Filter stocks based on criteria
        for stock in stocks:
            stocks_checked += 1

            # Check data quality for this stock
            missing_fields = []
            for factor in sanitized_criteria.keys():
                if stock.get(factor) is None:
                    missing_fields.append(factor)

            if missing_fields:
                data_quality_issues.append(
                    {
                        "symbol": stock.get("symbol", "UNKNOWN"),
                        "missing_fields": missing_fields,
                    }
                )

            if self._matches_criteria(stock, sanitized_criteria):
                # Add data quality indicator to each matching stock
                stock_with_quality = stock.copy()
                stock_with_quality["_data_quality"] = {
                    "complete": len(missing_fields) == 0,
                    "missing_fields": missing_fields,
                }
                matching_stocks.append(stock_with_quality)

        # Build summary of data quality issues
        data_quality_summary = {}
        if data_quality_issues:
            # Count stocks missing each field
            field_counts = {}
            for issue in data_quality_issues:
                for field in issue["missing_fields"]:
                    field_counts[field] = field_counts.get(field, 0) + 1

            data_quality_summary = {
                "stocks_with_missing_data": len(data_quality_issues),
                "total_stocks_checked": stocks_checked,
                "fields_missing_counts": field_counts,
                "warning": f"{len(data_quality_issues)} out of {stocks_checked} stocks have incomplete data for screening criteria",
            }

        return {
            "stocks": matching_stocks,
            "validation": {"valid": True, "errors": errors, "warnings": warnings},
            "data_quality": data_quality_summary,
            "metadata": {
                "total_stocks_checked": stocks_checked,
                "matching_stocks": len(matching_stocks),
                "criteria_applied": sanitized_criteria,
            },
        }

    def _matches_criteria(self, stock: Dict, criteria: Dict) -> bool:
        """Check if a stock matches the screening criteria"""
        for factor, conditions in criteria.items():
            stock_value = stock.get(factor)

            if stock_value is None:
                return False

            # Check min/max conditions
            if "min" in conditions and stock_value < conditions["min"]:
                return False
            if "max" in conditions and stock_value > conditions["max"]:
                return False

            # Check directional conditions (increasing/decreasing)
            if "direction" in conditions:
                # Would need historical data to verify trend
                pass

        return True

    def save_factor(self, user_id: str, factor_data: Dict) -> Dict:
        """Save a custom factor using single-table design"""
        try:
            factor_id = factor_data.get("factorId")
            item = {
                "PK": f"USER#{user_id}",
                "SK": f"FACTOR#{factor_id}",
                "userId": user_id,
                "factorId": factor_id,
                "name": factor_data.get("name"),
                "description": factor_data.get("description", ""),
                "criteria": factor_data.get("criteria"),
                "createdAt": factor_data.get("createdAt"),
                "entityType": "CUSTOM_FACTOR",
            }

            self.table.put_item(Item=item)
            return {"success": True, "factor": item}
        except Exception as err:
            return {"success": False, "error": str(err)}

    def get_user_factors(self, user_id: str) -> List[Dict]:
        """Get all saved factors for a user using single-table design"""
        try:
            from boto3.dynamodb.conditions import Key

            response = self.table.query(
                KeyConditionExpression=Key("PK").eq(f"USER#{user_id}")
                & Key("SK").begins_with("FACTOR#")
            )
            return response.get("Items", [])
        except Exception as err:
            return {"error": str(err)}

    def delete_factor(self, user_id: str, factor_id: str) -> Dict:
        """Delete a custom factor using single-table design"""
        try:
            self.table.delete_item(
                Key={"PK": f"USER#{user_id}", "SK": f"FACTOR#{factor_id}"}
            )
            return {"success": True, "message": "Factor deleted successfully"}
        except Exception as err:
            return {"success": False, "error": str(err)}


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
        current_price = params.get("currentPrice")
        assumptions = params.get("assumptions", {})
        years = params.get("yearsToProject", 10)

        # Extract assumptions with scenario (low, mid, high)
        revenue_growth = assumptions.get("revenueGrowth", {})
        profit_margin = assumptions.get("profitMargin", {})
        fcf_margin = assumptions.get("fcfMargin", {})
        discount_rate = assumptions.get("discountRate", {})
        terminal_growth = assumptions.get("terminalGrowthRate", {})
        desired_return = assumptions.get("desiredReturn", {})

        results = {}

        for scenario in ["low", "mid", "high"]:
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
            pv_fcf = sum(
                [fcf / ((1 + dr) ** (idx + 1)) for idx, fcf in enumerate(projected_fcf)]
            )

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
                "intrinsicValue": round(intrinsic_value, 2),
                "expectedReturn": round(expected_return * 100, 2),
                "discountedCashFlowValue": round(pv_fcf, 2),
                "terminalValue": round(pv_terminal, 2),
                "projectedFCF": [round(fcf, 2) for fcf in projected_fcf],
            }

        results["currentPrice"] = current_price
        return results


def lambda_handler(event, context):
    """Handler for screening and analysis endpoints"""

    if event["httpMethod"] == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key",
                "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
            },
            "body": "",
        }

    path = event.get("path", "")
    method = event.get("httpMethod", "GET")

    try:
        if "/api/screen" in path:
            screener = StockScreener()

            if method == "POST":
                body = json.loads(event.get("body", "{}"))
                criteria = body.get("criteria", {})
                result = screener.screen_stocks(criteria)

                # If validation failed, return 400 with error details
                if not result.get("validation", {}).get("valid", True):
                    return {
                        "statusCode": 400,
                        "headers": {
                            "Access-Control-Allow-Origin": "*",
                            "Content-Type": "application/json",
                        },
                        "body": json.dumps(result, default=decimal_default),
                    }
            else:
                result = {"error": "Method not allowed"}

        elif "/api/factors" in path:
            screener = StockScreener()

            if method == "POST":
                # Require authentication for saving factors
                authorizer = event.get("requestContext", {}).get("authorizer", {})
                claims = authorizer.get("claims", {})
                user_id = claims.get("sub")

                if not user_id:
                    result = {
                        "error": "Unauthorized - Authentication required to save factors"
                    }
                else:
                    body = json.loads(event.get("body", "{}"))
                    result = screener.save_factor(user_id, body)

            elif method == "DELETE":
                # DELETE factor - require authentication
                authorizer = event.get("requestContext", {}).get("authorizer", {})
                claims = authorizer.get("claims", {})
                user_id = claims.get("sub")

                if not user_id:
                    result = {"error": "Unauthorized - Authentication required"}
                else:
                    # Extract factor_id from path
                    factor_id = path.split("/")[-1]
                    result = screener.delete_factor(user_id, factor_id)

            else:
                # GET factors - require authentication
                authorizer = event.get("requestContext", {}).get("authorizer", {})
                claims = authorizer.get("claims", {})
                user_id = claims.get("sub")

                if not user_id:
                    result = {"error": "Unauthorized - Authentication required"}
                else:
                    result = screener.get_user_factors(user_id)

        elif "/api/dcf" in path:
            analyzer = DCFAnalyzer()

            if method == "POST":
                body = json.loads(event.get("body", "{}"))
                result = analyzer.calculate_dcf(body)
            else:
                result = {"error": "Method not allowed"}

        else:
            result = {"error": "Invalid endpoint"}

        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Content-Type": "application/json",
            },
            "body": json.dumps(result, default=decimal_default),
        }

    except Exception as err:
        return {
            "statusCode": 500,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Content-Type": "application/json",
            },
            "body": json.dumps({"error": str(err)}),
        }
