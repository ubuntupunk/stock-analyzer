# Flake8 Code Quality Refactoring Plan

**Date:** 2026-02-13  
**Current Status:** ✅ Phase 1 Milestone - 3 high-impact files completed and committed  
**Starting Violations:** 1,254 across 24 files  
**Current Violations:** ~1,112 (142 violations reduced so far in 3 files)  
**Target:** Reduce to ~400-500 violations (60-70% reduction)  
**Strategy:** Focus on high-impact structural improvements first

**Git Commit:** `6ae91d7` - Phase 1 improvements committed

**Progress Summary:**

- ✅ constants.py created (200+ constants extracted) - COMMITTED
- ✅ stock_universe_api.py: 150 → 38 (75% reduction) - COMMITTED
- ✅ yahoo_finance.py: 250 → 57 (77% reduction) - COMMITTED
- ✅ alpha_vantage.py: 150 → 47 (69% reduction) - COMMITTED
- 🔄 Next: stock_api.py (~200 violations) - Large file (1005 lines), requires significant refactoring
- 🔄 Next: local_server.py (~130 violations)

**Total Violations Reduced:** ~408 violations reduced to ~142 (65% reduction in completed files)

**Key Achievements:**

- All refactored code passes existing tests
- No breaking changes introduced
- Significantly improved code maintainability
- Established patterns for remaining files

---

## Phase 1: High-Impact Files (Priority 1)

### 1.1 stock_universe_api.py (~150 violations → 38 violations)

**Status:** ✅ COMPLETED  
**Complexity:** Reduced from extreme to manageable
**Time Spent:** ~1 hour

**Actions Completed:**

- [x] Created constants.py module with all repeated strings and magic numbers
- [x] Extracted helper methods to reduce complexity
- [x] Renamed generic variables (`items` → `stock_items`, `err` → `fetch_error`)
- [x] Split lambda_handler into focused helper functions
- [x] Reduced cognitive complexity significantly
- [x] Improved code readability and maintainability

**Remaining Issues (38 violations):**

- WPS421: 9 print statements (intentionally kept for debugging)
- WPS229: 12 try blocks >1 statement (acceptable for error handling)
- WPS214: Too many methods (18 > 7) - class is cohesive, acceptable
- WPS235: Too many imports from constants (58 > 8) - necessary for constants
- Minor: variable naming, pass keyword, nested try

**Result:** 75% reduction in violations (150 → 38)

---

### 1.2 yahoo_finance.py (~250 violations → 57 violations)

**Status:** ✅ COMPLETED  
**Complexity:** Reduced from extreme (216) to manageable
**Time Spent:** ~1 hour

**Actions Completed:**

- [x] Added Yahoo Finance specific constants to constants.py
- [x] Extracted helper methods for parsing (news, financials, estimates)
- [x] Reduced nesting depth significantly
- [x] Split large parsing functions into focused methods
- [x] Renamed variables (`err` → `fetch_error`, `info` → `ticker_info`)
- [x] Improved code readability dramatically

**Remaining Issues (57 violations):**

- WPS421: 22 print statements (intentionally kept for debugging)
- WPS229: 14 try blocks >1 statement (acceptable for error handling)
- WPS214: Too many methods (28 > 7) - class is cohesive, acceptable
- WPS235: Too many imports from constants (92 > 8) - necessary
- WPS231: 2 functions with high complexity (parse_metrics, parse_estimates)
- Minor: variable naming, string literal over-use

**Result:** 77% reduction in violations (250 → 57)

---

### 1.3 alpha_vantage.py (~150 violations → 47 violations)

**Status:** ✅ COMPLETED  
**Complexity:** Reduced from high to manageable
**Time Spent:** ~45 minutes

**Actions Completed:**

- [x] Added Alpha Vantage specific constants to constants.py
- [x] Extracted helper methods for parsing (earnings, income, balance, cashflow)
- [x] Reduced nesting depth
- [x] Renamed variables (`err` → `fetch_error`, `result` → `fetch_result`)
- [x] Simplified rate limiting logic with helper methods
- [x] Improved error handling

**Remaining Issues (47 violations):**

- WPS421: 13 print statements (intentionally kept for debugging)
- WPS229: 7 try blocks >1 statement (acceptable for error handling)
- WPS214: Too many methods (24 > 7) - class is cohesive, acceptable
- WPS235: Too many imports from constants (85 > 8) - necessary
- WPS110: 14 generic variable names (`params`, `data`, `value`)
- WPS220: 5 deep nesting (24 > 20) - in \_fetch_with_retry
- Minor: cognitive complexity in parse_metrics

**Result:** 69% reduction in violations (150 → 47)

---

### 1.4 stock_api.py (~200 violations)

**Status:** 🔴 Not Started  
**Complexity:** High (22 methods)  
**Estimated Time:** 3-4 hours

**Actions:**

- [ ] Identify method groupings (validation, fetching, processing)
- [ ] Extract related methods into separate service classes
- [ ] Reduce total methods from 22 to <15
- [ ] Rename generic parameters
- [ ] Extract repeated validation logic
- [ ] Test all API endpoints

**Refactoring Strategy:**

- Create `StockValidator` service for validation methods
- Create `StockDataFetcher` service for data retrieval
- Keep core orchestration in main class

---

### 1.5 local_server.py (~130 violations)

**Status:** 🔴 Not Started  
**Complexity:** Medium (many print calls, complex handlers)  
**Estimated Time:** 2-3 hours

**Actions:**

- [ ] Extract route handler logic into separate methods
- [ ] Rename generic variables in handlers
- [ ] Simplify complex conditional logic
- [ ] Extract constants for routes and status codes
- [ ] Test server endpoints

---

## Phase 2: Quick Wins (Priority 2)

### 2.1 Variable Naming (~370 violations)

**Status:** 🔴 Not Started  
**Estimated Time:** 2-3 hours across all files

**Common Renames:**

- `data` → `stock_data`, `response_data`, `parsed_data`
- `result` → `fetch_result`, `validation_result`, `api_result`
- `params` → `query_params`, `request_params`, `api_params`
- `e` → `error`, `exception`
- `k` → `key`, `field_name`
- `v` → `value`, `field_value`
- `s` → `symbol`, `stock_symbol`
- `i` → `index`, `item`

**Approach:**

- Use IDE refactoring tools for safety
- Do one file at a time
- Run tests after each file

---

### 2.2 Extract Constants (~90 violations)

**Status:** 🔴 Not Started  
**Estimated Time:** 1-2 hours

**Actions:**

- [ ] Create `constants.py` module in backend/
- [ ] Extract HTTP status codes
- [ ] Extract repeated string literals
- [ ] Extract magic numbers
- [ ] Update imports across files

**Constants to Define:**

```python
# HTTP Status Codes
HTTP_OK = 200
HTTP_BAD_REQUEST = 400
HTTP_RATE_LIMIT = 429
HTTP_SERVER_ERROR = 500

# API Response Keys
KEY_SYMBOL = "symbol"
KEY_ERROR = "error"
KEY_STATUS_CODE = "statusCode"
KEY_BODY = "body"
KEY_SUCCESS = "success"

# Cache/Rate Limiting
CACHE_TTL_SECONDS = 3600
RATE_LIMIT_DELAY = 0.05
RETRY_DELAY = 0.10

# Validation
MAX_SYMBOLS_PER_REQUEST = 100
MIN_SYMBOL_LENGTH = 1
MAX_SYMBOL_LENGTH = 10
```

---

## Phase 3: Remaining Files (Priority 3)

### 3.1 Medium Complexity Files

**Status:** 🔴 Not Started  
**Estimated Time:** 4-6 hours total

**Files:**

- [ ] stock_universe_seed.py (~120 violations)
- [ ] screener_api.py (~100 violations)
- [ ] circuit_breaker.py (~80 violations)
- [ ] stock_validator.py (~60 violations)

**Actions per file:**

- Extract constants
- Rename variables
- Reduce nesting
- Simplify complex functions

---

### 3.2 Index Fetchers (~210 violations combined)

**Status:** 🔴 Not Started  
**Estimated Time:** 3-4 hours total

**Files:**

- [ ] jse_fetcher.py (~60 violations)
- [ ] russell_fetcher.py (~50 violations)
- [ ] sp500_fetcher.py (~50 violations)
- [ ] base.py (~20 violations)

**Common Actions:**

- Extract parsing constants
- Rename variables
- Simplify parsing logic
- Reduce print statements if possible (keep for debugging)

---

### 3.3 API Clients (~100 violations combined)

**Status:** 🔴 Not Started  
**Estimated Time:** 2-3 hours total

**Files:**

- [ ] polygon.py (~50 violations)
- [ ] alpaca.py (~50 violations)

**Actions:**

- Extract constants
- Reduce complexity
- Limit magic numbers
- Rename variables

---

### 3.4 Low Priority Files (~80 violations combined)

**Status:** 🔴 Not Started  
**Estimated Time:** 1-2 hours total

**Files:**

- [ ] stock_metrics.py (~50 violations)
- [ ] lambda_handler.py (~40 violations)
- [ ] index_config.py (~15 violations)
- [ ] diagnostics/\*.py (~15 violations)
- [ ] **init**.py files (~10 violations)

---

## Implementation Guidelines

### Before Each File:

1. Read the entire file to understand structure
2. Run existing tests to establish baseline
3. Create a backup or commit current state

### During Refactoring:

1. Extract constants first (lowest risk)
2. Rename variables using IDE tools
3. Reduce nesting with early returns
4. Break down complex functions last (highest risk)
5. Keep changes focused and atomic

### After Each File:

1. Run flake8 to verify violation reduction
2. Run unit tests
3. Run integration tests if available
4. Commit changes with descriptive message

### Testing Strategy:

- Run `pytest tests/` after each major change
- Verify API responses match expected format
- Check integration points between modules
- Manual smoke test critical endpoints

---

## What NOT to Fix

- **Print statements (WPS421):** Keep for debugging (~450 violations)
- **Intentional design patterns:** Don't over-refactor working code
- **External API response formats:** Don't change data structures

---

## Progress Tracking

### Violations by Phase:

- **Phase 1 (High-Impact):** ~850 violations → Target: ~200-300
- **Phase 2 (Quick Wins):** ~460 violations → Target: ~100-150
- **Phase 3 (Remaining):** ~400 violations → Target: ~150-200

### Expected Final State:

- **Total Violations:** 1,254 → ~450-650 (50-65% reduction)
- **Critical Complexity Issues:** Resolved
- **Code Maintainability:** Significantly improved
- **Functionality:** 100% preserved

---

## Execution Order

**Week 1:**

1. Create constants.py module
2. Refactor stock_universe_api.py
3. Refactor yahoo_finance.py

**Week 2:** 4. Refactor alpha_vantage.py 5. Refactor stock_api.py 6. Refactor local_server.py

**Week 3:** 7. Apply variable naming improvements across all files 8. Refactor medium complexity files 9. Refactor index fetchers and remaining API clients

**Week 4:** 10. Final cleanup and testing 11. Documentation updates 12. Final flake8 report

---

## Success Metrics

- [ ] Reduce violations by 50-65%
- [ ] No functions with complexity >20
- [ ] No nesting depth >20
- [ ] All tests passing
- [ ] No regression in functionality
- [ ] Improved code readability

---

## Notes

- Keep print statements for debugging (team decision)
- Use IDE refactoring tools for variable renames
- Test thoroughly after each file
- Commit frequently with clear messages
- Document any breaking changes (should be none)

---

**Next Step:** Start with creating `constants.py` and refactoring `stock_universe_api.py`

---

## Next Steps & Recommendations

### Immediate Next Actions (Priority Order)

1. **stock_api.py** (~200 violations, 1005 lines)

   - This is a large orchestrator file with 22 methods
   - Recommended approach:
     - Extract APIMetrics class into separate file
     - Split into multiple service classes (PriceFetcher, MetricsFetcher, etc.)
     - Extract parallel fetching logic into separate module
     - Apply same constant extraction patterns
   - Estimated time: 4-6 hours
   - Expected reduction: 200 → 60-80 violations

2. **local_server.py** (~130 violations)

   - Extract route handlers into separate functions
   - Apply constants for routes and status codes
   - Simplify complex conditional logic
   - Estimated time: 2-3 hours
   - Expected reduction: 130 → 40-50 violations

3. **Medium complexity files** (screener_api, circuit_breaker, validators, fetchers)
   - Apply established patterns from Phase 1
   - Extract constants, rename variables, reduce nesting
   - Estimated time: 6-8 hours total
   - Expected reduction: ~400 → 150-200 violations

### Patterns Established (Use for Remaining Files)

1. **Constants Extraction**

   - All repeated strings → constants.py
   - All magic numbers → constants.py with descriptive names
   - Group related constants together

2. **Helper Methods**

   - Extract nested logic into private helper methods
   - Name helpers with `_verb_noun` pattern (e.g., `_parse_news_item`)
   - Keep methods focused on single responsibility

3. **Variable Naming**

   - `err` → `{context}_error` (e.g., `fetch_error`, `parse_error`)
   - `data` → `{type}_data` (e.g., `response_data`, `stock_data`)
   - `result` → `{action}_result` (e.g., `fetch_result`, `parse_result`)
   - `params` → `{type}_params` (e.g., `query_params`, `api_params`)

4. **Error Handling**

   - Keep try blocks focused
   - Use descriptive exception variable names
   - Print statements are acceptable for debugging (WPS421)

5. **Acceptable Violations**
   - WPS421 (print statements) - kept for debugging
   - WPS229 (long try blocks) - acceptable for error handling
   - WPS214 (too many methods) - acceptable if class is cohesive
   - WPS235 (too many imports) - acceptable for constants module

### Testing Strategy

After each file refactoring:

1. Run `pytest tests/` to ensure no regressions
2. Run `flake8 {file}` to verify violation reduction
3. Manual smoke test of affected endpoints
4. Commit changes with descriptive message

### Success Metrics

- ✅ Phase 1: 65% reduction in 3 files (ACHIEVED)
- 🎯 Phase 2: Target 50-60% reduction in remaining high-impact files
- 🎯 Overall: Target 50-65% total reduction (1,254 → 450-650)

### Time Investment Summary

- Phase 1 (Completed): ~3 hours
- Phase 2 (Remaining high-impact): ~6-9 hours
- Phase 3 (Medium complexity): ~6-8 hours
- Total estimated: ~15-20 hours for 50-65% reduction

---

## Lessons Learned

1. **Constants module is essential** - Reduces violations by 20-30% immediately
2. **Helper methods reduce complexity** - Breaking down large functions is most impactful
3. **Patterns are reusable** - Once established, subsequent files go faster
4. **Pre-commit hooks help** - Black formatting ensures consistency
5. **Incremental commits** - Easier to review and rollback if needed

---

## Conclusion

Phase 1 successfully demonstrated that significant code quality improvements are achievable without breaking functionality. The patterns established provide a clear roadmap for the remaining files. The refactored code is more maintainable, readable, and follows Python best practices while preserving all original behavior.

**Recommendation:** Continue with stock_api.py next, as it's the largest remaining high-impact file and will benefit most from the established patterns.
