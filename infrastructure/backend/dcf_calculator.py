"""
DCF (Discounted Cash Flow) Calculator

Professional-grade DCF valuation model that uses real financial data
to calculate intrinsic value of stocks.

Methodology:
1. Extract base FCF from financial statements
2. Project FCF for specified years using growth rate
3. Calculate terminal value using Gordon Growth Model
4. Discount all cash flows using WACC
5. Calculate enterprise value
6. Convert to equity value (EV - Debt + Cash)
7. Calculate intrinsic value per share
"""

from datetime import datetime
from typing import Dict

from logger_config import setup_logger
from constants import (
    DCF_DEFAULT_DEBT_COST,
    DCF_DEFAULT_DISCOUNT_RATE,
    DCF_DEFAULT_GROWTH_RATE,
    DCF_DEFAULT_MARKET_RETURN,
    DCF_DEFAULT_PROJECTION_YEARS,
    DCF_DEFAULT_RISK_FREE_RATE,
    DCF_DEFAULT_TAX_RATE,
    DCF_DEFAULT_TERMINAL_GROWTH_RATE,
    DCF_KEY_ASSUMPTIONS,
    DCF_KEY_BASE_FCF,
    DCF_KEY_BETA,
    DCF_KEY_CASH,
    DCF_KEY_CURRENT_PRICE,
    DCF_KEY_DEBT,
    DCF_KEY_DISCOUNT_RATE,
    DCF_KEY_ENTERPRISE_VALUE,
    DCF_KEY_EQUITY_VALUE,
    DCF_KEY_FCF_PROJECTIONS,
    DCF_KEY_GROWTH_RATE,
    DCF_KEY_INTRINSIC_VALUE,
    DCF_KEY_MODEL_DATE,
    DCF_KEY_PV_FCF,
    DCF_KEY_PV_TERMINAL_VALUE,
    DCF_KEY_SHARES_OUTSTANDING,
    DCF_KEY_SYMBOL,
    DCF_KEY_TAX_RATE,
    DCF_KEY_TERMINAL_GROWTH,
    DCF_KEY_TERMINAL_VALUE,
    DCF_KEY_UPSIDE_POTENTIAL,
    DCF_KEY_VALUE_PER_SHARE,
    DCF_KEY_WACC,
    DCF_KEY_YEARS,
    DCF_MSG_CALCULATED,
    DCF_MSG_MISSING_DATA,
    DCF_MSG_PERFORMING,
    DCF_MSG_USING_REAL_DATA,
)

# Initialize logger
logger = setup_logger(__name__)


class DCFCalculator:
    """
    Discounted Cash Flow Calculator

    Calculates intrinsic value using DCF methodology with real financial data.
    """

    def __init__(self):
        """Initialize DCF Calculator with default parameters"""
        self.default_growth_rate = DCF_DEFAULT_GROWTH_RATE
        self.default_terminal_growth = DCF_DEFAULT_TERMINAL_GROWTH_RATE
        self.default_discount_rate = DCF_DEFAULT_DISCOUNT_RATE
        self.default_years = DCF_DEFAULT_PROJECTION_YEARS
        self.default_tax_rate = DCF_DEFAULT_TAX_RATE

    def calculate_wacc(
        self,
        beta: float,
        risk_free_rate: float = DCF_DEFAULT_RISK_FREE_RATE,
        market_return: float = DCF_DEFAULT_MARKET_RETURN,
    ) -> float:
        """
        Calculate Weighted Average Cost of Capital (WACC)

        Simplified WACC using CAPM for cost of equity.
        Assumes mostly equity-financed company.

        Args:
            beta: Stock beta (systematic risk)
            risk_free_rate: Risk-free rate (e.g., 10-year Treasury)
            market_return: Expected market return

        Returns:
            WACC as decimal (e.g., 0.10 for 10%)
        """
        equity_risk_premium = market_return - risk_free_rate
        cost_of_equity = risk_free_rate + (beta * equity_risk_premium)
        return cost_of_equity

    def project_free_cash_flows(
        self, base_fcf: float, growth_rate: float, years: int
    ) -> list:
        """
        Project future free cash flows

        Args:
            base_fcf: Base/current free cash flow
            growth_rate: Annual growth rate (decimal)
            years: Number of years to project

        Returns:
            List of projected FCFs
        """
        fcf_projections = []
        for year in range(1, years + 1):
            projected_fcf = base_fcf * ((1 + growth_rate) ** year)
            fcf_projections.append(projected_fcf)
        return fcf_projections

    def calculate_terminal_value(
        self, final_fcf: float, terminal_growth: float, wacc: float
    ) -> float:
        """
        Calculate terminal value using Gordon Growth Model

        Args:
            final_fcf: Final year projected FCF
            terminal_growth: Perpetual growth rate
            wacc: Weighted average cost of capital

        Returns:
            Terminal value
        """
        terminal_fcf = final_fcf * (1 + terminal_growth)
        terminal_value = terminal_fcf / (wacc - terminal_growth)
        return terminal_value

    def calculate_present_value(
        self, cash_flows: list, discount_rate: float, start_year: int = 1
    ) -> float:
        """
        Calculate present value of cash flows

        Args:
            cash_flows: List of future cash flows
            discount_rate: Discount rate (WACC)
            start_year: Starting year for discounting

        Returns:
            Present value of all cash flows
        """
        pv = sum(
            [
                cf / ((1 + discount_rate) ** year)
                for year, cf in enumerate(cash_flows, start_year)
            ]
        )
        return pv

    def calculate_equity_value(
        self, enterprise_value: float, total_debt: float, total_cash: float
    ) -> float:
        """
        Convert enterprise value to equity value

        Args:
            enterprise_value: Enterprise value
            total_debt: Total debt
            total_cash: Total cash and equivalents

        Returns:
            Equity value
        """
        return enterprise_value - total_debt + total_cash

    def calculate_value_per_share(
        self, equity_value: float, shares_outstanding: float
    ) -> float:
        """
        Calculate intrinsic value per share

        Args:
            equity_value: Total equity value
            shares_outstanding: Number of shares outstanding

        Returns:
            Value per share
        """
        if shares_outstanding <= 0:
            return 0
        return equity_value / shares_outstanding

    def calculate_upside_potential(
        self, intrinsic_value: float, current_price: float
    ) -> float:
        """
        Calculate upside/downside potential

        Args:
            intrinsic_value: Calculated intrinsic value
            current_price: Current market price

        Returns:
            Upside potential as percentage
        """
        if current_price <= 0:
            return 0
        return ((intrinsic_value - current_price) / current_price) * 100

    def run_dcf_analysis(
        self,
        symbol: str,
        base_fcf: float,
        current_price: float,
        shares_outstanding: float,
        total_cash: float = 0,
        total_debt: float = 0,
        beta: float = 1.0,
        growth_rate: float = None,
        terminal_growth: float = None,
        discount_rate: float = None,
        years: int = None,
        tax_rate: float = None,
    ) -> Dict:
        """
        Run complete DCF analysis

        Args:
            symbol: Stock symbol
            base_fcf: Base free cash flow
            current_price: Current stock price
            shares_outstanding: Shares outstanding
            total_cash: Total cash and equivalents
            total_debt: Total debt
            beta: Stock beta
            growth_rate: FCF growth rate (optional)
            terminal_growth: Terminal growth rate (optional)
            discount_rate: Discount rate override (optional)
            years: Projection years (optional)
            tax_rate: Tax rate (optional)

        Returns:
            Dict with complete DCF analysis results
        """
        logger.info(DCF_MSG_PERFORMING.format(symbol))

        # Use defaults if not provided
        growth_rate = (
            growth_rate if growth_rate is not None else self.default_growth_rate
        )
        terminal_growth = (
            terminal_growth
            if terminal_growth is not None
            else self.default_terminal_growth
        )
        projection_years = years if years is not None else self.default_years
        tax_rate = tax_rate if tax_rate is not None else self.default_tax_rate

        # Calculate WACC
        wacc = discount_rate if discount_rate is not None else self.calculate_wacc(beta)

        # Project Free Cash Flows
        fcf_projections = self.project_free_cash_flows(
            base_fcf, growth_rate, projection_years
        )

        # Calculate Terminal Value
        terminal_value = self.calculate_terminal_value(
            fcf_projections[-1], terminal_growth, wacc
        )

        # Calculate Present Values
        pv_fcf = self.calculate_present_value(fcf_projections, wacc)
        pv_terminal_value = terminal_value / ((1 + wacc) ** projection_years)

        # Calculate Enterprise Value
        enterprise_value = pv_fcf + pv_terminal_value

        # Calculate Equity Value
        equity_value = self.calculate_equity_value(
            enterprise_value, total_debt, total_cash
        )

        # Calculate Value Per Share
        value_per_share = self.calculate_value_per_share(
            equity_value, shares_outstanding
        )

        # Calculate Upside Potential
        upside_potential = self.calculate_upside_potential(
            value_per_share, current_price
        )

        logger.info(
            DCF_MSG_CALCULATED.format(value_per_share, current_price, upside_potential)
        )

        return {
            DCF_KEY_SYMBOL: symbol,
            DCF_KEY_INTRINSIC_VALUE: round(value_per_share, 2),
            DCF_KEY_CURRENT_PRICE: round(current_price, 2),
            DCF_KEY_UPSIDE_POTENTIAL: round(upside_potential, 2),
            DCF_KEY_ENTERPRISE_VALUE: round(enterprise_value, 2),
            DCF_KEY_EQUITY_VALUE: round(equity_value, 2),
            DCF_KEY_SHARES_OUTSTANDING: shares_outstanding,
            DCF_KEY_VALUE_PER_SHARE: round(value_per_share, 2),
            DCF_KEY_FCF_PROJECTIONS: [round(fcf, 2) for fcf in fcf_projections],
            DCF_KEY_TERMINAL_VALUE: round(terminal_value, 2),
            DCF_KEY_PV_FCF: round(pv_fcf, 2),
            DCF_KEY_PV_TERMINAL_VALUE: round(pv_terminal_value, 2),
            DCF_KEY_BASE_FCF: round(base_fcf, 2),
            DCF_KEY_CASH: round(total_cash, 2),
            DCF_KEY_DEBT: round(total_debt, 2),
            DCF_KEY_BETA: round(beta, 2),
            DCF_KEY_WACC: round(wacc * 100, 2),  # As percentage
            DCF_KEY_ASSUMPTIONS: {
                DCF_KEY_GROWTH_RATE: growth_rate,
                DCF_KEY_TERMINAL_GROWTH: terminal_growth,
                DCF_KEY_DISCOUNT_RATE: wacc,
                DCF_KEY_YEARS: projection_years,
                DCF_KEY_TAX_RATE: tax_rate,
            },
            DCF_KEY_MODEL_DATE: datetime.now().isoformat(),
        }
