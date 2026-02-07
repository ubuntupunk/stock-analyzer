import yfinance as yf
import pandas as pd
import json

def diagnose_aapl():
    print("=== Diagnosing AAPL Financials ===")
    ticker = yf.Ticker("AAPL")
    
    print("\n--- Income Statement ---")
    financials = ticker.financials
    if financials is not None and not financials.empty:
        print("Index:", financials.index.tolist())
        print("Columns:", financials.columns.tolist())
        print("\nSample Rows:")
        for idx in financials.index:
            print(f"{idx}: {financials.loc[idx].values}")
    else:
        print("Income Statement is EMPTY")

    print("\n--- Balance Sheet ---")
    balance_sheet = ticker.balance_sheet
    if balance_sheet is not None and not balance_sheet.empty:
        print("Index:", balance_sheet.index.tolist())
    else:
        print("Balance Sheet is EMPTY")

    print("\n--- Cash Flow ---")
    cashflow = ticker.cashflow
    if cashflow is not None and not cashflow.empty:
        print("Index:", cashflow.index.tolist())
    else:
        print("Cash Flow is EMPTY")

if __name__ == "__main__":
    diagnose_aapl()
