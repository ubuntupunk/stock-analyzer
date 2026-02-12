# Flake8 Report (WPS - Python linter)

**Date:** 2026-02-12  
**Config:** `.flake8` with `select = WPS`, `max-line-length = 100`

**Updated Configuration:**
```ini
[flake8]
max-line-length = 100
select = WPS
max-cognitive-complexity = 20
max-nested-try-body = 3
max-module-members = 15
```

**Summary:**
- **Total Violations:** 1,254 (reduced from ~1,900)
- **Files Scanned:** 24 backend Python files
- **Reduction:** ~34% fewer violations

---

## Violation Breakdown by Category

| Category | Code | Count | Description |
|----------|------|-------|-------------|
| Wrong function call | WPS421 | ~450 | `print()` calls |
| Wrong variable name | WPS110 | ~300 | Generic names like `data`, `result`, `params` |
| Too deep nesting | WPS220/224 | ~120 | Nesting depth 24-32 (limit: 20) |
| Long try body | WPS229 | ~100 | `try` bodies > 3 statements |
| High cognitive complexity | WPS231 | ~80 | Functions > 20 complexity |
| String literal over-use | WPS226 | ~80 | Same string used >3 times |
| Too short name | WPS111 | ~70 | Names like `e`, `k`, `v`, `s`, `i` |
| Too many methods | WPS214 | ~20 | Classes with >7 methods |
| Module complexity | WPS232 | ~15 | Modules >8 cognitive complexity |
| Nested try block | WPS505 | ~15 | Nested try/except blocks |
| Implicit .get() | WPS529 | ~10 | Implicit dict `.get()` usage |
| Overused expression | WPS204 | ~10 | Same expression >7 times |
| Magic numbers | WPS432 | ~10 | Unnamed numeric constants |

---

## Files Ranked by Violation Count

| Rank | File | Violations | Key Issues |
|------|------|------------|------------|
| 1 | `api_clients/yahoo_finance.py` | ~250 | Deep nesting (24-32), complex parsing, high complexity |
| 2 | `stock_api.py` | ~200 | Too many methods (22), high complexity, print calls |
| 3 | `api_clients/alpha_vantage.py` | ~150 | Deep nesting, too many methods (17), high complexity |
| 4 | `stock_universe_api.py` | ~150 | Complex data processing, nested try blocks |
| 5 | `local_server.py` | ~130 | Many print calls, complex handlers |
| 6 | `stock_universe_seed.py` | ~120 | High complexity, deep nesting, magic numbers |
| 7 | `screener_api.py` | ~100 | Complex validation, many local variables |
| 8 | `circuit_breaker.py` | ~80 | Many methods, print calls, complex logic |
| 9 | `index_fetchers/jse_fetcher.py` | ~60 | Complex parsing, many print calls |
| 10 | `index_fetchers/russell_fetcher.py` | ~50 | High complexity, deep nesting |
| 11 | `api_clients/polygon.py` | ~50 | High complexity, magic numbers |
| 12 | `api_clients/alpaca.py` | ~50 | High complexity, too many returns |
| 13 | `stock_validator.py` | ~60 | Complex validation logic |
| 14 | `index_fetchers/sp500_fetcher.py` | ~50 | Many local variables |
| 15 | `stock_metrics.py` | ~50 | Many print calls, string literals |
| 16 | `lambda_handler.py` | ~40 | High complexity, many returns |
| 17 | `index_fetchers/base.py` | ~20 | Many public attributes |
| 18 | `index_config.py` | ~15 | `global` keyword, many methods |
| 19 | `diagnostics/*.py` | ~15 | Print calls |
| 20 | `__init__.py` files | ~10 | Logic in init, local imports |

---

## Priority Recommendations (for Complexity Agent)

### 1. Reduce Nesting Depth (WPS220/224)
**Files:** `yahoo_finance.py`, `alpha_vantage.py`, `stock_universe_api.py`
- Extract nested logic into helper functions
- Use early returns to flatten control flow
- Combine conditions using boolean operators

### 2. Reduce Cognitive Complexity (WPS231)
**Critical:** `stock_universe_api.py` (complexity 89, 96), `yahoo_finance.py` (216)
- Break large functions into smaller, focused ones
- Extract conditional logic into separate methods
- Use strategy pattern for complex branching

### 3. Shorten Try Bodies (WPS229)
**Files:** Most API clients and fetchers
- Limit `try` blocks to 3 statements
- Extract validation/logic outside try blocks
- Use context managers where possible

### 4. Rename Variables (WPS110, WPS111)
**Common offenders:** `data`, `result`, `params`, `e`, `k`, `v`, `s`, `i`
- Use descriptive names: `stock_data`, `fetch_result`, `error`
- Single-letter vars only in loops or lambdas

### 5. Extract Constants (WPS226, WPS432)
**Common strings:** `symbol`, `error`, `success`, `statusCode`, `body`
**Magic numbers:** `200`, `429`, `0.05`, `0.10`, `3600`
- Define constants at module level
- Use enums for related values

---

## Debug Print Statements (WPS421) - NOT TO REMOVE

**Status:** Keep as-is (per decision)

The codebase heavily uses `print()` for debugging/error reporting. This is intentional and should not be modified at this time.

---

## Files to Focus On (Complexity Reduction)

1. **`stock_universe_api.py`** - Start here (highest total complexity)
2. **`yahoo_finance.py`** - Most violations, complex parsing
3. **`alpha_vantage.py`** - Deep nesting issues
4. **`stock_api.py`** - Too many methods (22 > 7)
5. **`screener_api.py`** - Complex validation logic

---

## Configuration Notes

The WPS linter is strict. Recommended future adjustments:
- `max-cognitive-complexity = 20` (default 12 is very strict)
- `max-nested-try-body = 3` (default 1 is very strict)
- `max-module-members = 15` (default 7 is too low for API modules)
