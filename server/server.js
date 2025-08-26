/**
 * Node.js API server for FT article scraping
 * Uses Puppeteer with bypass-paywalls extension
 */

const express = require('express');
const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// Configuration
const config = {
    port: PORT,
    bypassPaywallsPath: "C:\\Users\\SOUHAIL\\Documents\\bypass-paywalls-chrome-clean-master\\",
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    requestTimeout: 30000,
    contentLoadDelay: 3000
};

// Middleware
app.use(express.json());

// Global browser instance for reuse
let browser = null;

/**
 * Initialize Puppeteer browser with extensions
 */
async function initializeBrowser() {
    console.log('Initializing browser with bypass-paywalls extension...');
    
    try {
        browser = await puppeteer.launch({
            headless: true,
            defaultViewport: null,
            args: [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-web-security',
                `--disable-extensions-except=${config.bypassPaywallsPath}`,
                `--load-extension=${config.bypassPaywallsPath}`
            ],
            pipe: true,
        });
        
        console.log('Browser initialized successfully');
        return true;
    } catch (error) {
        console.error('Failed to initialize browser:', error.message);
        return false;
    }
}

/**
 * Helper function for delays (compatible with all Puppeteer versions)
 */
async function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Cleanup browser on process exit
 */
process.on('SIGINT', async () => {
    if (browser) {
        console.log('Closing browser...');
        await browser.close();
    }
    process.exit(0);
});

/**
 * Health check endpoint
 */
app.get('/health', (req, res) => {
    res.json({ 
        status: 'OK', 
        browserReady: browser !== null,
        timestamp: new Date().toISOString()
    });
});

/**
 * Article scraping endpoint
 */
app.post('/scrape', async (req, res) => {
    const { url } = req.body;
    
    if (!url) {
        return res.status(400).json({ 
            success: false,
            error: 'URL is required' 
        });
    }

    if (!browser) {
        return res.status(503).json({
            success: false,
            error: 'Browser not initialized'
        });
    }

    console.log(`Scraping: ${url}`);
    
    let page = null;
    
    try {
        // Create new page
        page = await browser.newPage();
        
        // Set user agent
        await page.setUserAgent(config.userAgent);
        
        // Navigate to URL
        await page.goto(url, { 
            waitUntil: 'networkidle2',
            timeout: config.requestTimeout 
        });
        
        // Wait for dynamic content to load
        await delay(config.contentLoadDelay);
        
        // Get HTML content
        const htmlContent = await page.content();
        
        console.log(`Successfully scraped: ${url} (${htmlContent.length} chars)`);
        
        // Return success response
        res.json({
            success: true,
            url: url,
            html: htmlContent,
            timestamp: new Date().toISOString()
        });
        
    } catch (error) {
        console.error(`Error scraping ${url}:`, error.message);
        
        res.status(500).json({
            success: false,
            url: url,
            error: error.message,
            timestamp: new Date().toISOString()
        });
    } finally {
        // Always close the page
        if (page) {
            try {
                await page.close();
            } catch (closeError) {
                console.error('Error closing page:', closeError.message);
            }
        }
    }
});

/**
 * Get article count from sitemap data
 */
app.get('/articles/count', (req, res) => {
    try {
        const sitemapPath = path.join(__dirname, '..', 'data', 'raw', 'sitemap_data.json');
        
        if (!fs.existsSync(sitemapPath)) {
            return res.status(404).json({ 
                error: 'Sitemap data not found' 
            });
        }
        
        const data = JSON.parse(fs.readFileSync(sitemapPath, 'utf8'));
        const articleCount = data.filter(item => item.loc && !item.errors).length;
        
        res.json({
            totalArticles: articleCount,
            totalEntries: data.length,
            timestamp: new Date().toISOString()
        });
        
    } catch (error) {
        res.status(500).json({ 
            error: error.message 
        });
    }
});

/**
 * Start the server
 */
async function startServer() {
    try {
        const browserReady = await initializeBrowser();
        
        if (!browserReady) {
            console.error('Failed to initialize browser. Server will not start.');
            process.exit(1);
        }
        
        app.listen(config.port, () => {
            console.log('='.repeat(60));
            console.log('FT Scraper API Server Started');
            console.log('='.repeat(60));
            console.log(`Server running on: http://localhost:${config.port}`);
            console.log(`Health check: http://localhost:${config.port}/health`);
            console.log(`Article count: http://localhost:${config.port}/articles/count`);
            console.log(`Scrape endpoint: POST http://localhost:${config.port}/scrape`);
            console.log('='.repeat(60));
        });
        
    } catch (error) {
        console.error('Failed to start server:', error);
        process.exit(1);
    }
}

// Start the server
startServer();