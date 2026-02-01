/**
 * DynamoDB Service Layer
 * Handles all DynamoDB operations for users, watchlists, and stocks
 * Uses existing tables from template.yaml:
 *   - stock-watchlist (userId + symbol)
 *   - stock-factors (userId + factorId)
 *   - stock-universe (symbol)
 */

/**
 * Get environment variable safely (works in both Node.js and browser)
 */
function getEnvVar(name, defaultValue) {
    // Check if process.env is available (Node.js)
    if (typeof process !== 'undefined' && process.env && process.env[name]) {
        return process.env[name];
    }
    // Check window.env if defined (browser with script tag config)
    if (typeof window !== 'undefined' && window.env && window.env[name]) {
        return window.env[name];
    }
    return defaultValue;
}

class DynamoDBService {
    constructor(config = {}) {
        this.config = {
            region: config.region || getEnvVar('AWS_REGION', 'us-east-1'),
            endpoint: config.endpoint || getEnvVar('DYNAMODB_ENDPOINT', undefined),
            accessKeyId: config.accessKeyId || getEnvVar('AWS_ACCESS_KEY_ID', undefined),
            secretAccessKey: config.secretAccessKey || getEnvVar('AWS_SECRET_ACCESS_KEY', undefined),
            // Use table names from template.yaml environment variables or defaults
            watchlistTable: config.watchlistTable || getEnvVar('WATCHLIST_TABLE', 'stock-watchlist'),
            factorsTable: config.factorsTable || getEnvVar('FACTORS_TABLE', 'stock-factors'),
            universeTable: config.universeTable || getEnvVar('STOCK_UNIVERSE_TABLE', 'stock-universe'),
            usersTable: config.usersTable || getEnvVar('USERS_TABLE', 'stock-users')
        };
        
        this.dynamoDB = null;
        this.docClient = null;
        this.isInitialized = false;
    }
    
    /**
     * Initialize DynamoDB connection
     */
    async initialize() {
        if (this.isInitialized) return;
        
        try {
            // Check if we're in browser or Node.js
            if (typeof window !== 'undefined') {
                // Browser environment - use API calls instead of direct DynamoDB
                console.log('DynamoDB Service: Browser mode - using API calls');
                this.isInitialized = true;
                return;
            }
            
            // Node.js environment - use AWS SDK v3
            const { DynamoDBClient } = await import('@aws-sdk/client-dynamodb');
            const { DynamoDBDocumentClient, PutCommand, GetCommand, UpdateCommand, DeleteCommand, QueryCommand, ScanCommand } = await import('@aws-sdk/lib-dynamodb');
            
            const clientConfig = {
                region: this.config.region
            };
            
            // Add endpoint for local development
            if (this.config.endpoint) {
                clientConfig.endpoint = this.config.endpoint;
                clientConfig.credentials = {
                    accessKeyId: this.config.accessKeyId || 'local',
                    secretAccessKey: this.config.secretAccessKey || 'local'
                };
            }
            
            this.dynamoDB = new DynamoDBClient(clientConfig);
            this.docClient = DynamoDBDocumentClient.from(this.dynamoDB, {
                marshallOptions: {
                    removeUndefinedValues: true
                }
            });
            
            this.isInitialized = true;
            console.log('DynamoDB Service: Initialized successfully');
        } catch (error) {
            console.error('DynamoDB Service: Initialization failed:', error);
            this.isInitialized = true; // Mark as initialized to prevent retry loops
        }
    }
    
    /**
     * Get table name
     */
    getTableName(table = 'watchlist') {
        const tables = {
            watchlist: this.config.watchlistTable,
            factors: this.config.factorsTable,
            universe: this.config.universeTable,
            users: this.config.usersTable
        };
        return tables[table] || this.config.watchlistTable;
    }
    
    // ============================================
    // USER OPERATIONS (uses single-table design with prefix)
    // ============================================
    
    /**
     * Create a new user
     * @param {object} userData - User data
     * @returns {Promise} Created user
     */
    async createUser(userData) {
        const { userId, email, name } = userData;
        const timestamp = new Date().toISOString();
        
        const userItem = {
            PK: `USER#${userId}`,
            SK: 'PROFILE',
            entityType: 'USER',
            userId,
            email: email.toLowerCase(),
            name: name || email.split('@')[0],
            createdAt: timestamp,
            updatedAt: timestamp,
            preferences: {
                theme: 'dark',
                notifications: true,
                defaultView: 'dashboard'
            }
        };
        
        await this.putItem(userItem, 'users');
        return userItem;
    }
    
    /**
     * Get user by ID
     * @param {string} userId - User ID
     * @returns {Promise} User data
     */
    async getUser(userId) {
        const result = await this.getItem({
            PK: `USER#${userId}`,
            SK: 'PROFILE'
        }, 'users');
        return result;
    }
    
    /**
     * Get user by email
     * @param {string} email - User email
     * @returns {Promise} User data
     */
    async getUserByEmail(email) {
        // Note: For production, add a GSI to users table for email lookup
        // For now, we scan (not recommended for large tables)
        const result = await this.scan({
            FilterExpression: 'entityType = :type AND email = :email',
            ExpressionAttributeValues: {
                ':type': 'USER',
                ':email': email.toLowerCase()
            }
        }, 'users');
        return result.Items?.[0];
    }
    
    /**
     * Update user profile
     * @param {string} userId - User ID
     * @param {object} updates - Fields to update
     * @returns {Promise} Updated user
     */
    async updateUser(userId, updates) {
        const timestamp = new Date().toISOString();
        
        // Build update expression
        const updateParts = ['updatedAt = :timestamp'];
        const expressionValues = {
            ':timestamp': timestamp
        };
        
        Object.entries(updates).forEach(([key, value], index) => {
            updateParts.push(`${key} = :val${index}`);
            expressionValues[`:val${index}`] = value;
        });
        
        const result = await this.updateItem({
            Key: {
                PK: `USER#${userId}`,
                SK: 'PROFILE'
            },
            UpdateExpression: `SET ${updateParts.join(', ')}`,
            ExpressionAttributeValues: expressionValues,
            ReturnValues: 'ALL_NEW'
        }, 'users');
        
        return result.Attributes;
    }
    
    /**
     * Delete user
     * @param {string} userId - User ID
     */
    async deleteUser(userId) {
        // First, get all user's watchlist items to delete them
        const watchlist = await this.getUserWatchlist(userId);
        
        // Delete all watchlist items
        for (const item of watchlist) {
            await this.deleteItem({
                PK: userId,
                SK: item.symbol
            }, 'watchlist');
        }
        
        // Delete user profile
        await this.deleteItem({
            PK: `USER#${userId}`,
            SK: 'PROFILE'
        }, 'users');
    }
    
    // ============================================
    // WATCHLIST OPERATIONS (uses stock-watchlist table)
    // ============================================
    
    /**
     * Add stock to user's watchlist
     * @param {string} userId - User ID
     * @param {object} stockData - Stock data
     * @returns {Promise} Created item
     */
    async addToWatchlist(userId, stockData) {
        const { symbol, name, notes, alertPrice, tags } = stockData;
        const timestamp = new Date().toISOString();
        
        const watchlistItem = {
            PK: userId,              // userId as partition key
            SK: symbol.toUpperCase(), // symbol as sort key
            userId,
            symbol: symbol.toUpperCase(),
            name: name || this.formatSymbolAsName(symbol),
            notes: notes || '',
            alertPrice: alertPrice || null,
            tags: tags || [],
            addedAt: timestamp
        };
        
        await this.putItem(watchlistItem, 'watchlist');
        return watchlistItem;
    }
    
    /**
     * Get user's entire watchlist
     * @param {string} userId - User ID
     * @returns {Promise} Array of watchlist items
     */
    async getUserWatchlist(userId) {
        const result = await this.query({
            KeyConditionExpression: 'PK = :pk',
            ExpressionAttributeValues: {
                ':pk': userId
            }
        }, 'watchlist');
        
        return result.Items || [];
    }
    
    /**
     * Get single watchlist item
     * @param {string} userId - User ID
     * @param {string} symbol - Stock symbol
     * @returns {Promise} Watchlist item
     */
    async getWatchlistItem(userId, symbol) {
        const result = await this.getItem({
            PK: userId,
            SK: symbol.toUpperCase()
        }, 'watchlist');
        return result;
    }
    
    /**
     * Update watchlist item
     * @param {string} userId - User ID
     * @param {string} symbol - Stock symbol
     * @param {object} updates - Fields to update
     * @returns {Promise} Updated item
     */
    async updateWatchlistItem(userId, symbol, updates) {
        const timestamp = new Date().toISOString();
        
        // Build update expression
        const updateParts = ['updatedAt = :timestamp'];
        const expressionValues = {
            ':timestamp': timestamp
        };
        
        Object.entries(updates).forEach(([key, value], index) => {
            // Skip partition/sort keys
            if (['PK', 'SK', 'userId', 'symbol', 'addedAt'].includes(key)) return;
            updateParts.push(`${key} = :val${index}`);
            expressionValues[`:val${index}`] = value;
        });
        
        const result = await this.updateItem({
            Key: {
                PK: userId,
                SK: symbol.toUpperCase()
            },
            UpdateExpression: `SET ${updateParts.join(', ')}`,
            ExpressionAttributeValues: expressionValues,
            ReturnValues: 'ALL_NEW'
        }, 'watchlist');
        
        return result.Attributes;
    }
    
    /**
     * Remove stock from watchlist
     * @param {string} userId - User ID
     * @param {string} symbol - Stock symbol
     */
    async removeFromWatchlist(userId, symbol) {
        await this.deleteItem({
            PK: userId,
            SK: symbol.toUpperCase()
        }, 'watchlist');
    }
    
    /**
     * Check if stock is in user's watchlist
     * @param {string} userId - User ID
     * @param {string} symbol - Stock symbol
     * @returns {Promise} Boolean
     */
    async isOnWatchlist(userId, symbol) {
        const item = await this.getWatchlistItem(userId, symbol);
        return !!item;
    }
    
    /**
     * Get watchlist count for user
     * @param {string} userId - User ID
     * @returns {Promise} Count
     */
    async getWatchlistCount(userId) {
        const result = await this.query({
            KeyConditionExpression: 'PK = :pk',
            Select: 'COUNT',
            ExpressionAttributeValues: {
                ':pk': userId
            }
        }, 'watchlist');
        return result.Count || 0;
    }
    
    // ============================================
    // FACTORS OPERATIONS (uses stock-factors table)
    // ============================================
    
    /**
     * Save user's factor
     * @param {string} userId - User ID
     * @param {object} factorData - Factor data
     * @returns {Promise} Created/updated item
     */
    async saveFactor(userId, factorData) {
        const { factorId, name, weight, category } = factorData;
        const timestamp = new Date().toISOString();
        
        const factorItem = {
            PK: userId,
            SK: factorId || `FACTOR#${Date.now()}`,
            userId,
            factorId: factorId || `FACTOR#${Date.now()}`,
            name,
            weight: weight || 1.0,
            category: category || 'custom',
            createdAt: timestamp,
            updatedAt: timestamp
        };
        
        await this.putItem(factorItem, 'factors');
        return factorItem;
    }
    
    /**
     * Get user's factors
     * @param {string} userId - User ID
     * @returns {Promise} Array of factors
     */
    async getUserFactors(userId) {
        const result = await this.query({
            KeyConditionExpression: 'PK = :pk AND begins_with(SK, :prefix)',
            ExpressionAttributeValues: {
                ':pk': userId,
                ':prefix': 'FACTOR#'
            }
        }, 'factors');
        
        return result.Items || [];
    }
    
    /**
     * Delete factor
     * @param {string} userId - User ID
     * @param {string} factorId - Factor ID
     */
    async deleteFactor(userId, factorId) {
        await this.deleteItem({
            PK: userId,
            SK: factorId
        }, 'factors');
    }
    
    // ============================================
    // STOCK UNIVERSE OPERATIONS (uses stock-universe table)
    // ============================================
    
    /**
     * Get stock by symbol
     * @param {string} symbol - Stock symbol
     * @returns {Promise} Stock data
     */
    async getStockBySymbol(symbol) {
        const result = await this.getItem({
            PK: symbol.toUpperCase(),
            SK: 'INFO'
        }, 'universe');
        return result;
    }
    
    /**
     * Search stocks
     * @param {string} query - Search query
     * @param {number} limit - Max results
     * @returns {Promise} Array of stocks
     */
    async searchStocks(query, limit = 10) {
        // Note: For production, use a GSI with search capability
        // For now, we scan with filter
        const result = await this.scan({
            FilterExpression: 'contains(#name, :query) OR contains(PK, :queryUpper)',
            ExpressionAttributeNames: {
                '#name': 'name'
            },
            ExpressionAttributeValues: {
                ':query': query.toLowerCase(),
                ':queryUpper': query.toUpperCase()
            },
            Limit: limit
        }, 'universe');
        
        return result.Items || [];
    }
    
    /**
     * Get popular stocks
     * @param {number} limit - Max results
     * @returns {Promise} Array of stocks
     */
    async getPopularStocks(limit = 12) {
        const result = await this.scan({
            Limit: limit,
            FilterExpression: 'attribute_exists(PK)'
        }, 'universe');
        
        return result.Items || [];
    }
    
    /**
     * Get stocks by sector
     * @param {string} sector - Sector name
     * @returns {Promise} Array of stocks
     */
    async getStocksBySector(sector) {
        // Use GSI if available, otherwise scan
        const result = await this.query({
            IndexName: 'sector-index',
            KeyConditionExpression: 'sector = :sector',
            ExpressionAttributeValues: {
                ':sector': sector
            }
        }, 'universe');
        
        return result.Items || [];
    }
    
    // ============================================
    // STOCK METADATA OPERATIONS
    // ============================================
    
    /**
     * Store stock metadata (for caching)
     * @param {string} symbol - Stock symbol
     * @param {object} stockData - Stock data
     */
    async saveStockMetadata(symbol, stockData) {
        const item = {
            PK: `STOCK#${symbol.toUpperCase()}`,
            SK: 'METADATA#info',
            entityType: 'STOCK_METADATA',
            symbol: symbol.toUpperCase(),
            ...stockData,
            cachedAt: new Date().toISOString()
        };
        
        await this.putItem(item);
        return item;
    }
    
    /**
     * Get stock metadata
     * @param {string} symbol - Stock symbol
     * @returns {Promise} Stock metadata
     */
    async getStockMetadata(symbol) {
        const result = await this.getItem({
            PK: `STOCK#${symbol.toUpperCase()}`,
            SK: 'METADATA#info'
        });
        return result;
    }
    
    // ============================================
    // HELPER METHODS
    // ============================================
    
    /**
     * Format symbol as readable name
     * @param {string} symbol - Stock symbol
     * @returns {string} Company name
     */
    formatSymbolAsName(symbol) {
        const stockNames = {
            'AAPL': 'Apple Inc.',
            'MSFT': 'Microsoft Corporation',
            'GOOGL': 'Alphabet Inc.',
            'AMZN': 'Amazon.com Inc.',
            'NVDA': 'NVIDIA Corporation',
            'META': 'Meta Platforms Inc.',
            'TSLA': 'Tesla Inc.',
            'JPM': 'JPMorgan Chase & Co.',
            'V': 'Visa Inc.',
            'JNJ': 'Johnson & Johnson',
            'WMT': 'Walmart Inc.',
            'PG': 'Procter & Gamble Co.',
            'MA': 'Mastercard Inc.',
            'HD': 'The Home Depot Inc.',
            'DIS': 'The Walt Disney Company',
            'NFLX': 'Netflix Inc.',
            'ADBE': 'Adobe Inc.',
            'CRM': 'Salesforce Inc.',
            'PYPL': 'PayPal Holdings Inc.',
            'INTC': 'Intel Corporation',
            'AMD': 'Advanced Micro Devices Inc.',
            'QCOM': 'Qualcomm Inc.',
            'TXN': 'Texas Instruments Inc.',
            'NKE': 'Nike Inc.',
            'MCD': "McDonald's Corporation",
            'KO': 'The Coca-Cola Company',
            'PEP': 'PepsiCo Inc.',
            'COST': 'Costco Wholesale Corporation',
            'MRK': 'Merck & Co. Inc.',
            'ABBV': 'AbbVie Inc.',
            'LLY': 'Eli Lilly and Company',
            'UNH': 'UnitedHealth Group Inc.',
            'GS': 'Goldman Sachs Group Inc.',
            'BAC': 'Bank of America Corp.',
            'C': 'Citigroup Inc.',
            'WFC': 'Wells Fargo & Company',
            'MS': 'Morgan Stanley',
            'BLK': 'BlackRock Inc.',
            'SCHW': 'Charles Schwab Corporation',
            'AXP': 'American Express Company',
            'USB': 'U.S. Bancorp',
            'PNC': 'PNC Financial Services Group',
            'TFC': 'Truist Financial Corporation',
            'COF': 'Capital One Financial Corp.',
            'SPGI': 'S&P Global Inc.',
            'MCO': "Moody's Corporation",
            'CME': 'CME Group Inc.',
            'ICE': 'Intercontinental Exchange Inc.',
            'MSCI': 'MSCI Inc.',
            'NDAQ': 'Nasdaq Inc.',
            'CBRE': 'CBRE Group Inc.',
            'DHI': 'D.R. Horton Inc.',
            'LEN': 'Lennar Corporation',
            'PLD': 'Prologis Inc.',
            'AMT': 'American Tower Corporation',
            'EQIX': 'Equinix Inc.',
            'CCI': 'Crown Castle Inc.',
            'PSA': 'Public Storage',
            'SPG': 'Simon Property Group Inc.',
            'O': 'Realty Income Corporation',
            'WELL': 'Welltower Inc.',
            'SNY': 'Sanofi',
            'NVS': 'Novartis AG',
            'AZN': 'AstraZeneca PLC',
            'BMY': 'Bristol-Myers Squibb Company',
            'GSK': 'GSK PLC',
            'CVS': 'CVS Health Corporation',
            'CI': 'Cigna Group',
            'ELV': 'Elevance Health Inc.',
            'HUM': 'Humana Inc.',
            'CNC': 'Centene Corporation',
            'BC': 'Brunswick Corporation',
            'MAR': 'Marriott International Inc.',
            'HLT': 'Hilton Worldwide Holdings Inc.',
            'H': 'Hyatt Hotels Corporation',
            'CCL': 'Carnival Corporation',
            'RCL': 'Royal Caribbean Cruises Ltd.',
            'NCLH': 'Norwegian Cruise Line Holdings Ltd.',
            'DAL': 'Delta Air Lines Inc.',
            'UAL': 'United Airlines Holdings Inc.',
            'AAL': 'American Airlines Group Inc.',
            'LUV': 'Southwest Airlines Co.',
            'GE': 'General Electric Company',
            'BA': 'The Boeing Company',
            'RTX': 'RTX Corporation',
            'LMT': 'Lockheed Martin Corporation',
            'NOC': 'Northrop Grumman Corporation',
            'GD': 'General Dynamics Corporation',
            'CAT': 'Caterpillar Inc.',
            'DE': 'Deere & Company',
            'MMM': '3M Company',
            'HON': 'Honeywell International Inc.',
            'UPS': 'United Parcel Service Inc.',
            'FDX': 'FedEx Corporation',
            'ABB': 'ABB Ltd.',
        };
        
        return stockNames[symbol.toUpperCase()] || symbol;
    }
    
    // ============================================
    // DYNAMODB PRIMITIVE OPERATIONS
    // ============================================
    
    /**
     * Put item (create or update)
     */
    async putItem(item) {
        if (!this.docClient) {
            console.warn('DynamoDB: DocClient not available, item:', item);
            return item;
        }
        
        const command = new PutCommand({
            TableName: this.getTableName(),
            Item: item
        });
        
        return this.docClient.send(command);
    }
    
    /**
     * Get single item
     */
    async getItem(key) {
        if (!this.docClient) {
            console.warn('DynamoDB: DocClient not available');
            return null;
        }
        
        const command = new GetCommand({
            TableName: this.getTableName(),
            Key: key
        });
        
        const result = await this.docClient.send(command);
        return result.Item || null;
    }
    
    /**
     * Update item
     */
    async updateItem(params) {
        if (!this.docClient) {
            console.warn('DynamoDB: DocClient not available');
            return { Attributes: {} };
        }
        
        const command = new UpdateCommand({
            TableName: this.getTableName(),
            ...params
        });
        
        const result = await this.docClient.send(command);
        return result;
    }
    
    /**
     * Delete item
     */
    async deleteItem(key) {
        if (!this.docClient) {
            console.warn('DynamoDB: DocClient not available');
            return null;
        }
        
        const command = new DeleteCommand({
            TableName: this.getTableName(),
            Key: key
        });
        
        const result = await this.docClient.send(command);
        return result;
    }
    
    /**
     * Query items
     */
    async query(params) {
        if (!this.docClient) {
            console.warn('DynamoDB: DocClient not available');
            return { Items: [] };
        }
        
        const command = new QueryCommand({
            TableName: this.getTableName(),
            ...params
        });
        
        const result = await this.docClient.send(command);
        return result;
    }
    
    /**
     * Scan all items (use sparingly - expensive operation)
     */
    async scan(params) {
        if (!this.docClient) {
            console.warn('DynamoDB: DocClient not available');
            return { Items: [] };
        }
        
        const command = new ScanCommand({
            TableName: this.getTableName(),
            ...params
        });
        
        const result = await this.docClient.send(command);
        return result;
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DynamoDBService;
} else {
    window.DynamoDBService = DynamoDBService;
}