# Plan for Factor Data Pipeline

This plan outlines the steps to create a data pipeline for populating the `stock-universe` DynamoDB table with comprehensive factor data, leveraging existing API access and functions.

**Current Resources:**
*   **External APIs:** Yahoo Finance, Alpaca, Polygon.io, Alpha Vantage (accessed via `api_clients/`).
*   **Factor Data Retrieval:** `StockDataAPI.get_stock_factors(symbol)` in `stock_api.py` already computes various factors for a single stock using multiple sources and fallback mechanisms.
*   **Target Database:** `stock-universe` DynamoDB table.
*   **Existing `stock_universe_api.py`:** Handles querying the `stock-universe` table (search, popular, sectors, filter, get by symbol) but lacks initial ingestion or factor data updates.

---

### **Phase 1: Define and Populate the Core Stock Universe**

**Objective:** Establish and maintain a foundational list of active stock symbols in the `stock-universe` DynamoDB table.

1.  **Identify Reliable Stock Universe Source:**
    *   **Action:** Research and select the most suitable external API (e.g., Yahoo Finance's screener, Alpaca's asset list, or a similar service that provides a list of actively traded stocks) to reliably fetch a broad list of active stock symbols (e.g., major exchanges like NASDAQ, NYSE).
    *   **Rationale:** We need a consistent and comprehensive list of symbols to gather factor data for.

2.  **Enhance `stock_universe_api.py` for Universe Management & Initial Population Script:**
    *   **Action:**
        *   **Modify `stock_universe_api.py`:** Add new methods to the `StockUniverseManager` class:
            *   `get_all_symbols() -> List[str]`: To retrieve all existing symbols from the `stock-universe` table.
            *   `add_stock_to_universe(symbol: str, name: str)`: To add a new stock with basic info.
            *   `bulk_upsert_stocks(stock_list: List[Dict])`: To efficiently add or update multiple stocks at once.
        *   **Create a new script (`populate_stock_universe.py`):** This script will:
            *   Call the chosen external API to fetch the initial universe of stock symbols and names.
            *   Use the `bulk_upsert_stocks` method in `StockUniverseManager` to populate the `stock-universe` DynamoDB table.
    *   **Rationale:** Centralize universe management logic and create a foundational list in DynamoDB. The initial population will be a separate, often one-time or infrequent, process.

---

### **Phase 2: Develop Factor Data Ingestion/Update Mechanism (New Lambda Function)**

**Objective:** Regularly enrich the `stock-universe` DynamoDB table with up-to-date factor data for all stocks in the universe.

1.  **Create `factor_ingestion_lambda.py` (New Module/Lambda Function):**
    *   **Action:** Develop a new Python module (`infrastructure/backend/factor_ingestion_lambda.py`) that will be designed to run as an AWS Lambda function.
    *   **Rationale:** Decouple factor ingestion from other API logic for modularity, scalability, and serverless execution.

2.  **Iterate and Fetch Factor Data:**
    *   **Action:** Within `factor_ingestion_lambda.py`:
        *   Retrieve all active symbols from the `stock-universe` DynamoDB table using `StockUniverseManager.get_all_symbols()`.
        *   For each `symbol`, call `StockDataAPI.get_stock_factors(symbol)` to obtain the computed factor data.
    *   **Rationale:** Leverage the existing robust `StockDataAPI` for factor computation and multi-source fallback.

3.  **Implement Batching and Rate Limiting:**
    *   **Action:** Integrate mechanisms within `factor_ingestion_lambda.py` to:
        *   Process symbols in batches to optimize DynamoDB writes (e.g., using `batch_writer`).
        *   Respect external API rate limits, especially for Alpha Vantage and Polygon.io, potentially using adaptive delays or a token bucket algorithm.
        *   Consider `asyncio` for concurrent API calls to non-rate-limited sources (like Yahoo Finance) to speed up processing within Lambda's execution limits.
    *   **Rationale:** Ensure efficient and compliant data fetching from external APIs, handling potential service limitations gracefully.

4.  **Update `stock-universe` DynamoDB with Factor Data:**
    *   **Action:** For each fetched stock's factor data:
        *   Use the `StockUniverseManager.update_stock_factors(symbol, factors_data)` method (a new method added to `StockUniverseManager`) to merge the factor attributes (e.g., `pe_ratio`, `roic`, `revenue_growth`) into the corresponding stock item in the `stock-universe` table.
        *   Include a `last_factors_updated` timestamp to track data freshness.
    *   **Rationale:** Store the computed factor data directly alongside the stock symbol in the `stock-universe` table, making it accessible for screening and analysis.

---

### **Phase 3: Scheduling and Automation**

**Objective:** Automate the execution of the factor data ingestion process.

1.  **Automate Initial Universe Population:**
    *   **Action:** Execute `populate_stock_universe.py` as a one-time run (or infrequently) to seed the `stock-universe` table initially.
    *   **Rationale:** Provide the base data for the factor ingestion process.

2.  **Automate Factor Data Ingestion Schedule:**
    *   **Action:** Deploy `factor_ingestion_lambda.py` as an AWS Lambda function, triggered by an Amazon EventBridge (CloudWatch Events) rule on a recurring schedule (e.g., daily after market close, or weekly, depending on data freshness requirements).
    *   **Rationale:** Ensure the factor data is regularly refreshed and kept up-to-date.

3.  **Implement Robust Monitoring and Error Handling:**
    *   **Action:** Add comprehensive logging within `factor_ingestion_lambda.py` to CloudWatch Logs.
    *   Configure CloudWatch alarms to notify on ingestion failures, API rate limit breaches, or other anomalies.
    *   Implement retry mechanisms (e.g., Lambda Dead-Letter Queues or in-function retries) for transient API/DB errors.
    *   **Rationale:** Guarantee the reliability and maintainability of the data pipeline.

---

### **Phase 4: Refinement of `screener_api.py`**

**Objective:** Ensure the `StockScreener` utilizes the dynamic factor data.

1.  **Remove Hardcoded Fallback Data:**
    *   **Action:** Modify `screener_api.py` to remove the hardcoded fallback stock data within the `screen_stocks` method.
    *   **Rationale:** The `StockScreener` will now rely entirely on the dynamic, updated data from the `stock-universe` DynamoDB table, ensuring real-time relevance.
