/**
 * DynamoDB Service Layer
 * Handles all DynamoDB operations for users, watchlists, and stocks
 * Uses AWS SDK v3 for DynamoDB
 */

class DynamoDBService {
    constructor(config = {}) {
        this.config = {
            region: config.region || process.env.AWS_REGION || 'us-east-1',
            endpoint: config.endpoint || process.env.DYNAMODB_ENDPOINT,
            accessKeyId: config.accessKeyId || process.env.AWS_ACCESS_KEY_ID,
            secretAccessKey: config.secretAccessKey || process.env.AWS_SECRET_ACCESS_KEY,
            tableName: config.tableName || process.env.DYNAMODB_TABLE_NAME || 'StockAnalyzer'
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
    getTableName() {
        return this.config.tableName;
    }
    
    // ============================================
    // USER OPERATIONS
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
            SK: 'METADATA#profile',
            entityType: 'USER',
            userId,
            email,
            name: name || email.split('@')[0],
            createdAt: timestamp,
            updatedAt: timestamp,
            preferences: {
                theme: 'dark',
                notifications: true,
                defaultView: 'dashboard'
            },
            // GSI for email lookup
            emailIndex: {
                email: email.toLowerCase(),
                userId
            }
        };
        
        await this.putItem(userItem);
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
            SK: 'METADATA#profile'
        });
        return result;
    }
    
    /**
     * Get user by email
     * @param {string} email - User email
     * @returns {Promise} User data
     */
    async getUserByEmail(email) {
        // In a real implementation, you would use a GSI query
        // For now, we'll use scan with filter (not recommended for production)
        const result = await this.scan({
            FilterExpression: 'entityType = :type AND email = :email',
            ExpressionAttributeValues: {
                ':type': 'USER',
                ':email': email.toLowerCase()
            }
        });
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
                SK: 'METADATA#profile'
            },
            UpdateExpression: `SET ${updateParts.join(', ')}`,
            ExpressionAttributeValues: expressionValues,
            ReturnValues: 'ALL_NEW'
        });
        
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
                PK: `USER#${userId}`,
                SK: `WATCHLIST#${item.symbol}`
            });
        }
        
        // Delete user profile
        await this.deleteItem({
            PK: `USER#${userId}`,
            SK: 'METADATA#profile'
        });
    }
    
    // ============================================
    // WATCHLIST OPERATIONS
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
            PK: `USER#${userId}`,
            SK: `WATCHLIST#${symbol}`,
            entityType: 'WATCHLIST_ITEM',
            symbol: symbol.toUpperCase(),
            name: name || this.formatSymbolAsName(symbol),
            notes: notes || '',
            alertPrice: alertPrice || null,
            tags: tags || [],
            addedAt: timestamp,
            userId
        };
        
        await this.putItem(watchlistItem);
        return watchlistItem;
    }
    
    /**
     * Get user's entire watchlist
     * @param {string} userId - User ID
     * @returns {Promise} Array of watchlist items
     */
    async getUserWatchlist(userId) {
        const result = await this.query({
            KeyConditionExpression: 'PK = :pk AND begins_with(SK, :prefix)',
            ExpressionAttributeValues: {
                ':pk': `USER#${userId}`,
                ':prefix': 'WATCHLIST#'
            }
        });
        
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
            PK: `USER#${userId}`,
            SK: `WATCHLIST#${symbol.toUpperCase()}`
        });
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
            // Skip PK, SK, entityType, userId
            if (['PK', 'SK', 'entityType', 'userId', 'symbol', 'addedAt'].includes(key)) return;
            updateParts.push(`${key} = :val${index}`);
            expressionValues[`:val${index}`] = value;
        });
        
        const result = await this.updateItem({
            Key: {
                PK: `USER#${userId}`,
                SK: `WATCHLIST#${symbol.toUpperCase()}`
            },
            UpdateExpression: `SET ${updateParts.join(', ')}`,
            ExpressionAttributeValues: expressionValues,
            ReturnValues: 'ALL_NEW'
        });
        
        return result.Attributes;
    }
    
    /**
     * Remove stock from watchlist
     * @param {string} userId - User ID
     * @param {string} symbol - Stock symbol
     */
    async removeFromWatchlist(userId, symbol) {
        await this.deleteItem({
            PK: `USER#${userId}`,
            SK: `WATCHLIST#${symbol.toUpperCase()}`
        });
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
            KeyConditionExpression: 'PK = :pk AND begins_with(SK, :prefix)',
            Select: 'COUNT',
            ExpressionAttributeValues: {
                ':pk': `USER#${userId}`,
                ':prefix': 'WATCHLIST#'
            }
        });
        return result.Count || 0;
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