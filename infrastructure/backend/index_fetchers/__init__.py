"""
Index Fetcher Strategy Pattern

Provides base class and implementations for fetching stock constituents
from various indices (S&P 500, Russell 3000, JSE, etc.).
"""

from .base import IndexFetcher
from .sp500_fetcher import SP500Fetcher
from .russell_fetcher import Russell3000Fetcher
from .jse_fetcher import JSEFetcher

__all__ = [
    'IndexFetcher',
    'SP500Fetcher',
    'Russell3000Fetcher',
    'JSEFetcher',
]
