"""
Index Configuration Registry for Multi-Index Stock Universe

Central registry for all supported stock indices.
Each index defines its metadata and fetch strategy.
"""

class IndexConfig:
    def __init__(self):
        self.indices = {
            'SP500': {
                'id': 'SP500',
                'name': 'S&P 500',
                'description': 'Large-cap US stocks',
                'region': 'US',
                'currency': 'USD',
                'exchange': 'NYSE/NASDAQ',
                'exchangeSuffix': '',
                'approxCount': 500,
                'dataSource': 'wikipedia',
                'url': 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies',
                'fetcher': 'SP500Fetcher',
                'updateFrequency': '7 days',
                'marketCapThresholds': {
                    'mega': 200_000_000_000,
                    'large': 10_000_000_000,
                    'mid': 2_000_000_000
                }
            },
            'RUSSELL3000': {
                'id': 'RUSSELL3000',
                'name': 'Russell 3000',
                'description': 'US total market (small to large cap)',
                'region': 'US',
                'currency': 'USD',
                'exchange': 'NYSE/NASDAQ',
                'exchangeSuffix': '',
                'approxCount': 3000,
                'dataSource': 'ishares_etf',
                'url': 'https://www.ishares.com/us/products/239724/',
                'fetcher': 'Russell3000Fetcher',
                'etfSymbol': 'IWV',
                'fallbackUrl': 'http://www.beatthemarketanalyzer.com/blog/wp-content/uploads/2016/10/Russell-3000-Stock-Tickers-List.xlsx',
                'updateFrequency': '7 days',
                'marketCapThresholds': {
                    'mega': 200_000_000_000,
                    'large': 10_000_000_000,
                    'mid': 2_000_000_000,
                    'small': 300_000_000
                }
            },
            'JSE_ALSI': {
                'id': 'JSE_ALSI',
                'name': 'JSE All Share Index',
                'description': 'South African total market index',
                'region': 'ZA',
                'currency': 'ZAR',
                'exchange': 'JSE',
                'exchangeSuffix': '.JO',
                'approxCount': 350,
                'dataSource': 'wikipedia',
                'url': 'https://en.wikipedia.org/wiki/JSE_Top_40',
                'fetcher': 'JSEFetcher',
                'updateFrequency': '7 days',
                'fxRate': {
                    'from': 'ZAR',
                    'to': 'USD',
                    'symbol': 'ZAR=X',
                    'source': 'yfinance'
                },
                'marketCapThresholds': {
                    'mega': 200_000_000_000,
                    'large': 10_000_000_000,
                    'mid': 2_000_000_000,
                    'small': 500_000_000
                }
            }
        }

    def get_index(self, index_id: str) -> dict:
        """
        Get configuration for a specific index

        Args:
            index_id: Unique identifier for the index (e.g., 'SP500')

        Returns:
            Dictionary with index configuration or None if not found
        """
        return self.indices.get(index_id)

    def get_all_indices(self) -> list:
        """
        Get all configured indices

        Returns:
            List of all index configuration dictionaries
        """
        return list(self.indices.values())

    def get_indices_by_region(self, region: str) -> list:
        """
        Get all indices for a specific region

        Args:
            region: Region code (e.g., 'US', 'ZA')

        Returns:
            List of index configurations matching the region
        """
        return [idx for idx in self.indices.values() if idx['region'] == region]

    def get_indices_by_currency(self, currency: str) -> list:
        """
        Get all indices using a specific currency

        Args:
            currency: Currency code (e.g., 'USD', 'ZAR')

        Returns:
            List of index configurations using the currency
        """
        return [idx for idx in self.indices.values() if idx['currency'] == currency]

    def index_exists(self, index_id: str) -> bool:
        """
        Check if an index ID exists in the registry

        Args:
            index_id: Index identifier to check

        Returns:
            True if index exists, False otherwise
        """
        return index_id in self.indices

    def get_index_display_name(self, index_id: str) -> str:
        """
        Get the display name for an index

        Args:
            index_id: Index identifier

        Returns:
            Display name or the index_id if not found
        """
        index = self.get_index(index_id)
        return index['name'] if index else index_id

    def get_index_ids(self) -> list:
        """
        Get all index IDs

        Returns:
            List of all index IDs
        """
        return list(self.indices.keys())


# Global instance for easy access
_default_config = None

def get_default_config() -> IndexConfig:
    """
    Get or create the default IndexConfig instance

    Returns:
        Default IndexConfig singleton instance
    """
    global _default_config
    if _default_config is None:
        _default_config = IndexConfig()
    return _default_config
