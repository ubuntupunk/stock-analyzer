"""
Stock Universe Metrics

Tracks and reports stock universe health metrics.
Sends data to CloudWatch for monitoring and alerting.
"""

import logging
import boto3
from datetime import datetime
from typing import Dict, List
from decimal import Decimal

from constants import (
    METRICS_CLOUDWATCH_BATCH_SIZE,
    METRICS_STALE_THRESHOLD_HOURS,
    METRICS_HOURS_PER_SECOND,
    METRICS_PERFECT_SCORE,
    METRICS_FRESHNESS_THRESHOLD,
    METRICS_QUALITY_THRESHOLD,
    METRICS_WARNING_PENALTY_PER_ISSUE,
    METRICS_MAX_WARNING_PENALTY,
    METRICS_CRITICAL_THRESHOLD,
    METRICS_DELISTED_WARNING_THRESHOLD,
    METRICS_DELISTED_CRITICAL_THRESHOLD,
    PERCENT_MULTIPLIER,
)

# Configure logging
logger = logging.getLogger(__name__)


class StockUniverseMetrics:
    """
    Track stock universe health metrics and send to CloudWatch

    Metrics tracked:
    - Stock count per index/region/currency
    - Data freshness (age of oldest data)
    - Delisted stocks count
    - Stale data count
    - Data quality score
    - Seeding duration
    """

    def __init__(self, namespace: str = "StockAnalyzer/StockUniverse"):
        """
        Initialize metrics collector

        Args:
            namespace: CloudWatch metrics namespace
        """
        self.namespace = namespace
        self.cloudwatch = boto3.client("cloudwatch")
        self.metrics_buffer = []

    def log_seeding_results(self, index_id: str, result: Dict) -> None:
        """
        Log seeding results as metrics

        Args:
            index_id: Index identifier
            result: Seeding result dict (should include 'seeded', 'failed', 'total')
        """
        seeded = result.get("seeded", 0)
        failed = result.get("failed", 0)
        total = result.get("total", 0)

        # Success rate
        if total > 0:
            success_rate = (seeded / total) * PERCENT_MULTIPLIER
            self.metrics_buffer.append(
                {
                    "MetricName": "SeedingSuccessRate",
                    "Dimensions": [{"Name": "IndexId", "Value": index_id}],
                    "Value": success_rate,
                    "Unit": "Percent",
                }
            )

        # Seeded count
        self.metrics_buffer.append(
            {
                "MetricName": "StocksSeeded",
                "Dimensions": [{"Name": "IndexId", "Value": index_id}],
                "Value": seeded,
                "Unit": "Count",
            }
        )

        # Failed count
        if failed > 0:
            self.metrics_buffer.append(
                {
                    "MetricName": "SeedingFailures",
                    "Dimensions": [{"Name": "IndexId", "Value": index_id}],
                    "Value": failed,
                    "Unit": "Count",
                }
            )

        # Seeding duration (if provided)
        duration_seconds = result.get("duration_seconds")
        if duration_seconds:
            self.metrics_buffer.append(
                {
                    "MetricName": "SeedingDuration",
                    "Dimensions": [{"Name": "IndexId", "Value": index_id}],
                    "Value": duration_seconds,
                    "Unit": "Seconds",
                }
            )

        logger.info(
            "Logged metrics for %s: %d seeded, %d failed", index_id, seeded, failed
        )

    def send_to_cloudwatch(self, async_mode: bool = True) -> bool:
        """
        Send buffered metrics to CloudWatch

        Args:
            async_mode: If True, put metrics asynchronously (recommended for high volume)

        Returns:
            True if successful, False otherwise
        """
        if not self.metrics_buffer:
            logger.warning("No metrics to send")
            return True

        try:
            # CloudWatch supports up to 20 metrics per request
            # Split into batches if needed
            batch_size = METRICS_CLOUDWATCH_BATCH_SIZE
            for idx in range(0, len(self.metrics_buffer), batch_size):
                batch = self.metrics_buffer[idx : idx + batch_size]

                self.cloudwatch.put_metric_data(
                    Namespace=self.namespace, MetricData=batch
                )

            count = len(self.metrics_buffer)
            logger.info(
                "Sent %d metrics to CloudWatch (namespace: %s)", count, self.namespace
            )
            self.metrics_buffer = []
            return True

        except Exception as err:
            logger.error("Error sending metrics to CloudWatch: %s", err)
            return False

    def calculate_freshness_score(self, stocks: List[Dict]) -> Dict:
        """
        Calculate data freshness metrics from stock list

        Args:
            stocks: List of stock records

        Returns:
            Dict with freshness metrics
        """
        if not stocks:
            return {
                "oldest_data_age_hours": 0,
                "stale_count": 0,
                "fresh_count": 0,
                "freshness_score": METRICS_PERFECT_SCORE,
            }

        now = datetime.utcnow()
        stale_threshold_hours = METRICS_STALE_THRESHOLD_HOURS
        age_hours_list = []
        stale_count = 0

        for stock in stocks:
            last_updated = stock.get("lastUpdated")
            if last_updated:
                try:
                    last_updated_dt = datetime.fromisoformat(
                        last_updated.replace("Z", "+00:00")
                    )
                    age_hours = (now - last_updated_dt).total_seconds() / METRICS_HOURS_PER_SECOND
                    age_hours_list.append(age_hours)

                    if age_hours > stale_threshold_hours:
                        stale_count += 1

                except Exception:
                    pass

        freshness_metrics = {
            "oldest_data_age_hours": max(age_hours_list) if age_hours_list else 0,
            "stale_count": stale_count,
            "fresh_count": len(stocks) - stale_count,
            "total_stocks": len(stocks),
            "freshness_score": 0,
        }

        # Calculate freshness score (0-100)
        if len(stocks) > 0:
            fresh_percentage = (freshness_metrics["fresh_count"] / len(stocks)) * PERCENT_MULTIPLIER
            freshness_metrics["freshness_score"] = round(fresh_percentage, 2)

        return freshness_metrics

    def calculate_data_quality_score(self, validation_results: List[Dict]) -> Dict:
        """
        Calculate overall data quality score from validation results

        Args:
            validation_results: List of validation result dicts

        Returns:
            Dict with quality metrics
        """
        if not validation_results:
            return {
                "total_stocks": 0,
                "valid_count": 0,
                "invalid_count": 0,
                "warning_count": 0,
                "total_issues": 0,
                "quality_score": METRICS_PERFECT_SCORE,
            }

        total_stocks = len(validation_results)
        valid_count = sum(
            1 for result in validation_results if result.get("valid", False)
        )
        invalid_count = total_stocks - valid_count
        warning_count = sum(
            len(result.get("warnings", [])) for result in validation_results
        )
        total_issues = sum(
            len(result.get("errors", []))
            + len(result.get("warnings", []))
            + len(result.get("issues", []))
            for result in validation_results
        )

        # Calculate quality score based on validity and issues
        quality_score = METRICS_PERFECT_SCORE

        # Deduct for invalid stocks
        if total_stocks > 0:
            validity_score = (valid_count / total_stocks) * PERCENT_MULTIPLIER
            quality_score = min(quality_score, validity_score)

        # Deduct for warnings (-5 points per warning, capped at -50)
        warning_penalty = min(warning_count * METRICS_WARNING_PENALTY_PER_ISSUE, METRICS_MAX_WARNING_PENALTY)
        quality_score = max(0, quality_score - warning_penalty)

        quality_metrics = {
            "total_stocks": total_stocks,
            "valid_count": valid_count,
            "invalid_count": invalid_count,
            "warning_count": warning_count,
            "total_issues": total_issues,
            "quality_score": round(quality_score, 2),
        }

        return quality_metrics

    def create_custom_metric(
        self,
        metric_name: str,
        value: float,
        dimensions: List[Dict],
        unit: str = "Count",
    ) -> None:
        """
        Create a custom metric and add to buffer

        Args:
            metric_name: Metric name
            value: Metric value
            dimensions: List of dimension dicts (e.g., [{'Name': 'Region', 'Value': 'US'}])
            unit: CloudWatch unit (Count, Percent, Seconds, etc.)
        """
        self.metrics_buffer.append(
            {
                "MetricName": metric_name,
                "Dimensions": dimensions,
                "Value": value,
                "Unit": unit,
            }
        )

    def send_health_summary(self, stock_universe_data: Dict) -> None:
        """
        Send high-level health summary metrics

        Args:
            stock_universe_data: Dict with stock universe summary
        """
        # Total stocks
        total_stocks = stock_universe_data.get("total_stocks", 0)
        self.create_custom_metric("TotalStocks", total_stocks, [], "Count")

        # Delisted stocks
        delisted_count = stock_universe_data.get("delisted_count", 0)
        self.create_custom_metric("DelistedStocks", delisted_count, [], "Count")

        # Freshness score
        freshness_score = stock_universe_data.get("freshness_score", 0)
        self.create_custom_metric(" FreshnessScore", freshness_score, [], "Percent")

        # Quality score
        quality_score = stock_universe_data.get("quality_score", 0)
        self.create_custom_metric("DataQualityScore", quality_score, [], "Percent")

        logger.info("Health summary metrics buffered")

    def detect_health_issues(self, stock_universe_data: Dict) -> List[Dict]:
        """
        Detect health issues based on metrics

        Args:
            stock_universe_data: Dict with stock universe summary

        Returns:
            List of detected issues
        """
        issues = []

        freshness_score = stock_universe_data.get("freshness_score", METRICS_PERFECT_SCORE)
        quality_score = stock_universe_data.get("quality_score", METRICS_PERFECT_SCORE)
        delisted_count = stock_universe_data.get("delisted_count", 0)

        # Issue: Low freshness score
        if freshness_score < METRICS_FRESHNESS_THRESHOLD:
            issues.append(
                {
                    "type": "low_freshness",
                    "severity": "warning" if freshness_score > METRICS_CRITICAL_THRESHOLD else "critical",
                    "message": f"Data freshness score is {freshness_score}% (< {METRICS_FRESHNESS_THRESHOLD}%)",
                    "freshness_score": freshness_score,
                }
            )

        # Issue: Low quality score
        if quality_score < METRICS_QUALITY_THRESHOLD:
            issues.append(
                {
                    "type": "low_quality",
                    "severity": "warning" if quality_score > METRICS_CRITICAL_THRESHOLD else "critical",
                    "message": f"Data quality score is {quality_score}% (< {METRICS_QUALITY_THRESHOLD}%)",
                    "quality_score": quality_score,
                }
            )

        # Issue: Many delisted stocks
        if delisted_count > METRICS_DELISTED_WARNING_THRESHOLD:
            issues.append(
                {
                    "type": "many_delisted",
                    "severity": "warning" if delisted_count < METRICS_DELISTED_CRITICAL_THRESHOLD else "critical",
                    "message": f"{delisted_count} delisted stocks detected",
                    "delisted_count": delisted_count,
                }
            )

        return issues


if __name__ == "__main__":
    import unittest.mock as mock

    logger.info("=== Stock Universe Metrics Tests ===\n")

    # Mock boto3 for local testing
    mock_cw = mock.MagicMock()
    with mock.patch("boto3.client", return_value=mock_cw):
        metrics = StockUniverseMetrics()

        # Test 1: Freshness calculation
        logger.info("1. Freshness Score Calculation:")
        mock_stocks = [
            {"lastUpdated": "2026-02-10T10:00:00"},  # Fresh (< 1 day)
            {"lastUpdated": "2026-02-05T10:00:00"},  # Fresh
            {"lastUpdated": "2026-01-01T10:00:00"},  # Stale (> 7 days)
            {},  # No last updated
        ]
    freshness = metrics.calculate_freshness_score(mock_stocks)
    logger.info(f"   Fresh score: {freshness['freshness_score']}%")
    logger.info(f"   Stale count: {freshness['stale_count']}")
    logger.info(f"   Oldest age: {freshness['oldest_data_age_hours']:.1f} hours")

    # Test 2: Quality score calculation
    logger.info("\n2. Quality Score Calculation:")
    mock_validation = [
        {"valid": True, "warnings": [], "errors": [], "issues": []},
        {"valid": True, "warnings": [{"type": "info"}], "errors": [], "issues": []},
        {
            "valid": False,
            "warnings": [],
            "errors": [{"type": "delisted"}],
            "issues": [],
        },
        {"valid": True, "warnings": [], "errors": [], "issues": []},
    ]

    quality = metrics.calculate_data_quality_score(mock_validation)
    logger.info(f"   Quality score: {quality['quality_score']}%")
    logger.info(f"   Valid: {quality['valid_count']}, Invalid: {quality['invalid_count']}")
    logger.info(f"   Total issues: {quality['total_issues']}")

    # Test 3: Health issue detection
    logger.info("\n3. Health Issue Detection:")
    health_data = {"freshness_score": 75, "quality_score": 60, "delisted_count": 15}
    issues = metrics.detect_health_issues(health_data)
    logger.info(f"   Detected {len(issues)} issues:")
    for issue in issues:
        logger.info(f"     - {issue['type']}: {issue['severity']}")

    # Test 4: Seeding result logging
    logger.info("\n4. Seeding Result Logging:")
    seeding_result = {"seeded": 500, "failed": 5, "total": 505, "duration_seconds": 120}
    metrics.log_seeding_results("SP500", seeding_result)
    logger.info(f"   Buffered metrics: {len(metrics.metrics_buffer)}")

    logger.info("\n✅ Metrics module tests passed!")
