import json
import boto3
import yfinance as yf
from datetime import datetime
from decimal import Decimal
import os

from index_config import get_default_config
from index_fetchers import SP500Fetcher, Russell3000Fetcher, JSEFetcher


class StockUniverseSeeder:
    """
    Multi-index stock universe seeder

    Supports seeding multiple stock indices (S&P 500, Russell 3000, JSE, etc.)
    with automatic FX conversion for non-USD currencies.
    """

    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(os.environ.get('STOCK_UNIVERSE_TABLE', 'stock-universe'))
        self.index_config = get_default_config()
        self.fetchers = {
            'SP500': SP500Fetcher,
            'RUSSELL3000': Russell3000Fetcher,
            'JSE_ALSI': JSEFetcher,
        }

    def seed_index(self, index_id: str, enrich: bool = True) -> dict:
        """
        Seed a specific index to DynamoDB

        Args:
            index_id: Index identifier (e.g., 'SP500', 'RUSSELL3000')
            enrich: If True, fetch market data from yfinance

        Returns:
            Dict with seeding results
        """
        index_config = self.index_config.get_index(index_id)
        if not index_config:
            return {'error': f'Unknown index: {index_id}'}

        fetcher_class = self.fetchers.get(index_id)
        if not fetcher_class:
            return {'error': f'No fetcher for index: {index_id}'}

        print(f"\n{'='*60}")
        print(f"Seeding {index_config['name']} ({index_config['id']})")
        print(f"{'='*60}")

        # Fetch constituents using the fetcher
        fetcher = fetcher_class(index_config)
        stocks = fetcher.fetch_constituents()

        if not stocks:
            return {'error': f'No stocks fetched for {index_id}', 'seeded': 0, 'failed': 0}

        print(f"Found {len(stocks)} stocks to seed")

        # Add index-specific metadata
        for stock in stocks:
            stock['indexId'] = index_id
            stock['indexIds'] = [index_id]

        # Enrich with market data from yfinance
        market_data = {}
        if enrich:
            market_data = self._enrich_stocks(stocks, index_config, fetcher)

        # Seed to DynamoDB
        return self._seed_to_database(stocks, market_data, index_config)

    def seed_all_indices(self, enrich: bool = True) -> dict:
        """
        Seed all configured indices

        Args:
            enrich: If True, fetch market data from yfinance

        Returns:
            Dict with results for each index
        """
        results = {}

        for index_config in self.index_config.get_all_indices():
            index_id = index_config['id']
            result = self.seed_index(index_id, enrich)
            results[index_id] = result

        # Merge overlapping stocks (stocks in multiple indices)
        self._merge_index_memberships()

        return results

    def _enrich_stocks(self, stocks: list, index_config: dict, fetcher) -> dict:
        """
        Fetch market data from yfinance with currency handling

        Args:
            stocks: List of stock dicts from fetcher
            index_config: Index configuration
            fetcher: IndexFetcher instance for FX conversion

        Returns:
            Dict mapping symbol -> market data
        """
        symbols = [s['symbol'] for s in stocks]
        print(f"\nFetching market data for {len(symbols)} symbols...")

        # Use yfinance in batches to avoid timeouts
        market_data = {}
        batch_size = 100

        for i in range(0, len(symbols), batch_size):
            batch_symbols = symbols[i:i + batch_size]
            print(f"  Batch {i//batch_size + 1}/{(len(symbols) + batch_size - 1)//batch_size}: {len(batch_symbols)} symbols")

            try:
                tickers = yf.Tickers(' '.join(batch_symbols))

                for symbol in batch_symbols:
                    try:
                        ticker = tickers.tickers.get(symbol)
                        if ticker:
                            info = ticker.info
                            market_cap = info.get('marketCap', 0) or 0

                            # Get FX rate for non-USD currencies
                            fx_rate = None
                            if index_config['currency'] != 'USD':
                                fx_rate = fetcher.get_fx_rate()

                            market_cap_usd = fetcher.apply_fx_conversion(market_cap, fx_rate)

                            market_data[symbol] = {
                                'marketCap': market_cap,
                                'marketCapUSD': market_cap_usd,
                                'exchange': info.get('exchange', index_config['exchange']),
                                'country': info.get('country', index_config['region']),
                                'industry': info.get('industry', ''),
                                'isActive': True,  # Will validate separately
                            }

                            if not market_cap:
                                print(f"    ⚠️  No market cap for {symbol}")
                    except Exception as e:
                        print(f"    ⚠️  Error fetching {symbol}: {str(e)[:50]}")
                        market_data[symbol] = {}

            except Exception as e:
                print(f"  ⚠️  Batch error: {e}")

        print(f"✅ Successfully fetched data for {len([s for s in market_data.values() if s])} symbols")
        return market_data

    def _seed_to_database(self, stocks: list, market_data: dict, index_config: dict) -> dict:
        """
        Seed stocks to DynamoDB

        Args:
            stocks: List of stock dicts
            market_data: Market data dict from yfinance
            index_config: Index configuration

        Returns:
            Dict with seeding results
        """
        seeded = 0
        failed = 0

        print(f"\nSeeding to DynamoDB...")

        with self.table.batch_writer() as batch:
            for stock in stocks:
                symbol = stock['symbol']
                md = market_data.get(symbol, {})

                try:
                    market_cap = md.get('marketCap', 0) or 0
                    market_cap_usd = md.get('marketCapUSD', 0) or 0

                    # Determine market cap bucket based on USD value
                    market_cap_bucket = 'unknown'
                    if market_cap_usd > 0:
                        thresholds = index_config.get('marketCapThresholds', {})
                        mega = thresholds.get('mega', 200_000_000_000)
                        large = thresholds.get('large', 10_000_000_000)
                        mid = thresholds.get('mid', 2_000_000_000)

                        if market_cap_usd >= mega:
                            market_cap_bucket = 'mega'
                        elif market_cap_usd >= large:
                            market_cap_bucket = 'large'
                        elif market_cap_usd >= mid:
                            market_cap_bucket = 'mid'
                        else:
                            market_cap_bucket = 'small'

                    item = {
                        'symbol': symbol,
                        'name': stock['name'],
                        'sector': stock.get('sector', 'Unknown'),
                        'subSector': stock.get('subSector', ''),
                        'industry': md.get('industry', ''),
                        'region': index_config['region'],
                        'currency': index_config['currency'],
                        'exchange': md.get('exchange', index_config['exchange']),
                        'exchangeSuffix': index_config.get('exchangeSuffix', ''),
                        'indexId': index_config['id'],
                        'indexIds': [index_config['id']],
                        'marketCap': Decimal(str(market_cap)) if market_cap else Decimal('0'),
                        'marketCapUSD': Decimal(str(market_cap_usd)) if market_cap_usd else Decimal('0'),
                        'marketCapBucket': market_cap_bucket,
                        'lastUpdated': datetime.utcnow().isoformat(),
                        'lastValidated': datetime.utcnow().isoformat(),
                        'isActive': md.get('isActive', True),
                        'dataSource': 'yfinance',
                        'country': md.get('country', index_config['region'])
                    }

                    # Add headquarters if available from stock dict
                    if 'headquarters' in stock:
                        item['headquarters'] = stock['headquarters']

                    batch.put_item(Item=item)
                    seeded += 1

                    if seeded % 50 == 0:
                        print(f"  {seeded}/{len(stocks)} stocks seeded...")

                except Exception as e:
                    print(f"  ⚠️  Failed to seed {symbol}: {str(e)[:50]}")
                    failed += 1

        print(f"✅ Seeding complete: {seeded} succeeded, {failed} failed")
        return {'seeded': seeded, 'failed': failed, 'total': len(stocks)}

    def _merge_index_memberships(self):
        """
        Merge stocks that belong to multiple indices

        E.g., AAPL exists in both SP500 and RUSSELL3000
        Updates the indexIds list to include all index memberships
        """
        print(f"\nMerging index memberships...")

        # Scan all stocks and group by symbol
        response = self.table.scan(
            ProjectionExpression='symbol, indexIds, #nm, sector',
            ExpressionAttributeNames={'#nm': 'name'}
        )

        stocks_by_symbol = {}
        for item in response.get('Items', []):
            symbol = item['symbol']
            if symbol not in stocks_by_symbol:
                stocks_by_symbol[symbol] = item
            else:
                # Merge indexIds
                existing = stocks_by_symbol[symbol]
                existing_ids = set(id for id in existing.get('indexIds', []))

                new_ids = set(id for id in item.get('indexIds', []))
                merged_ids = existing_ids.union(new_ids)

                if len(merged_ids) > 1:
                    existing['indexIds'] = sorted(list(merged_ids))
                    print(f"  Merging {symbol}: {sorted(list(merged_ids))}")

        # Update merged items
        updated = 0
        with self.table.batch_writer() as batch:
            for symbol, item in stocks_by_symbol.items():
                if len(item.get('indexIds', [])) > 1:
                    try:
                        batch.put_item(Item=item)
                        updated += 1
                    except Exception as e:
                        print(f"  ⚠️  Failed to merge {symbol}: {e}")

        print(f"✅ {updated} stocks belong to multiple indices")

    def update_market_data(self, symbols: list = None, index_id: str = None):
        """
        Update only market data for specified symbols or all symbols

        Args:
            symbols: List of symbols to update, or None for all
            index_id: Optional index ID to filter stocks

        Returns:
            Dict with update results
        """
        if symbols is None:
            # Fetch all symbols from DynamoDB
            print("Fetching all symbols from DynamoDB...")

            scan_kwargs = {'ProjectionExpression': 'symbol, region, currency'}
            if index_id:
                # Filter by index ID (require index-id-index GSI when deployed)
                scan_kwargs['FilterExpression'] = 'contains(indexIds, :idxId)'
                scan_kwargs['ExpressionAttributeValues'] = {':idxId': index_id}

            response = self.table.scan(**scan_kwargs)
            symbols_data = response.get('Items', [])

            # Group by region/currency for FX conversion
            symbols_by_currency = {}
            for item in symbols_data:
                currency = item.get('currency', 'USD')
                if currency not in symbols_by_currency:
                    symbols_by_currency[currency] = []
                symbols_by_currency[currency].append(item['symbol'])

            # Flatten all symbols
            symbols = [item['symbol'] for item in symbols_data]

        print(f"Updating market data for {len(symbols)} symbols...")

        # TODO: Implement batch update with proper currency handling
        # This is a placeholder for the full implementation

        return {'updated': 0}

    # ============================================================
    # Legacy Methods (for backward compatibility)
    # ============================================================

    def get_sp500_list(self) -> list:
        """Legacy method - use seed_index('SP500') instead"""
        fetcher = SP500Fetcher(self.index_config.get_index('SP500'))
        return fetcher.fetch_constituents()

    def enrich_stock_data_yfinance(self, symbols: list) -> dict:
        """Legacy method - use _enrich_stocks instead"""
        # This is kept for backward compatibility with existing code
        index_config = self.index_config.get_index('SP500')
        return self._enrich_stocks(
            [{'symbol': s} for s in symbols],
            index_config,
            SP500Fetcher(index_config)
        )

    def get_market_cap_bucket(self, market_cap: float) -> str:
        """Legacy method - use fetcher.get_market_cap_bucket() instead"""
        if market_cap >= 200_000_000_000:
            return 'mega'
        elif market_cap >= 10_000_000_000:
            return 'large'
        elif market_cap >= 2_000_000_000:
            return 'mid'
        else:
            return 'small'

    def seed_database(self, enrich: bool = True, batch_size: int = 25):
        """Legacy method - use seed_index() or seed_all_indices() instead"""
        return self.seed_index('SP500', enrich)


def lambda_handler(event, context):
    """
    Lambda handler for seeding stock universe

    Can be invoked manually or scheduled via EventBridge

    Event formats:
    - Full seed: { "enrich": true }
    - Specific index: { "indexId": "SP500", "operation": "seed" }
    - All indices: { "operation": "seed_all" }
    """

    # Check if this is an EventBridge scheduled event
    is_scheduled = event.get('source') == 'aws.events'

    # Check operation type
    operation = event.get('operation', 'seed')
    index_id = event.get('indexId')

    # For scheduled updates, always enrich
    enrich = event.get('enrich', is_scheduled)

    print(f"Starting stock universe {operation} (enrich={enrich})...")

    try:
        seeder = StockUniverseSeeder()

        if operation == 'seed_all':
            # Seed all indices
            result = seeder.seed_all_indices(enrich=enrich)
        elif operation == 'update_market':
            # Quick update of just market data
            symbols = event.get('symbols')
            index_id = event.get('indexId')
            result = seeder.update_market_data(symbols, index_id)
        else:
            # Seed specific index (default SP500 for backward compatibility)
            target_index = index_id or 'SP500'
            result = seeder.seed_index(target_index, enrich=enrich)

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Stock universe {operation} completed',
                'result': result
            })
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'Failed to {operation} stock universe',
                'message': str(e)
            })
        }


if __name__ == '__main__':
    import sys

    # Local testing
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == '--seed-all':
            print("Running seed for all indices...")
            seeder = StockUniverseSeeder()
            result = seeder.seed_all_indices(enrich=False)  # Start without enrichment
            print(json.dumps(result, indent=2))

        elif command.startswith('--seed='):
            index_id = command.split('=')[1]
            print(f"Running seed for {index_id}...")
            seeder = StockUniverseSeeder()
            result = seeder.seed_index(index_id, enrich=False)
            print(json.dumps(result, indent=2))

        elif command == '--quick-update':
            print("Running quick market data update...")
            seeder = StockUniverseSeeder()
            result = seeder.update_market_data()
            print(json.dumps(result, indent=2))

        else:
            print(f"Unknown command: {command}")
            print("Usage: python stock_universe_seed.py --seed-all | --seed=INDEX_ID | --quick-update")
    else:
        print("Running default SP500 seed...")
        seeder = StockUniverseSeeder()
        result = seeder.seed_index('SP500', enrich=False)
        print(json.dumps(result, indent=2))
