import { NextRequest, NextResponse } from 'next/server'
import { JSDOM } from 'jsdom';

// Try to import puppeteer, fallback to puppeteer-core
let puppeteer: any
try {
  puppeteer = require('puppeteer')
} catch (e) {
  puppeteer = require('puppeteer-core')
}

// Enhanced email regex pattern
const EMAIL_REGEX = /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g

interface ScrapedData {
  url: string
  domain: string
  emails: string[]
  status: string
  error?: string
}

// Browser pool for concurrent processing
class BrowserPool {
  private browsers: any[] = []
  private maxBrowsers = 3
  private currentIndex = 0

  async getBrowser() {
    if (this.browsers.length < this.maxBrowsers) {
      const browser = await this.createBrowser()
      this.browsers.push(browser)
      return browser
    }
    
    // Round-robin browser selection
    const browser = this.browsers[this.currentIndex]
    this.currentIndex = (this.currentIndex + 1) % this.browsers.length
    return browser
  }

  private async createBrowser() {
    try {
      if (process.env.NODE_ENV === 'production' || process.env.VERCEL) {
        const chromium = require('@sparticuz/chromium-min')
        
        return await puppeteer.launch({
          args: [
            ...chromium.args,
            '--hide-scrollbars',
            '--disable-web-security',
            '--disable-features=VizDisplayCompositor',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            '--single-process',
            '--disable-gpu'
          ],
          defaultViewport: chromium.defaultViewport,
          executablePath: await chromium.executablePath(),
          headless: chromium.headless,
          ignoreHTTPSErrors: true,
        })
      } else {
        return await puppeteer.launch({
          headless: true,
          args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            '--disable-gpu',
            '--disable-web-security'
          ],
          ignoreHTTPSErrors: true,
        })
      }
    } catch (error) {
      console.error('Failed to launch browser:', error)
      throw new Error(`Browser launch failed: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async cleanup() {
    await Promise.all(this.browsers.map(browser => browser.close().catch(() => {})))
    this.browsers = []
  }
}

const browserPool = new BrowserPool()

async function getBrowser() {
  try {
    if (process.env.NODE_ENV === 'production' || process.env.VERCEL) {
      // For Vercel deployment
      const chromium = require('@sparticuz/chromium-min')
      
      return await puppeteer.launch({
        args: [
          ...chromium.args,
          '--hide-scrollbars',
          '--disable-web-security',
          '--disable-features=VizDisplayCompositor',
          '--no-sandbox',
          '--disable-setuid-sandbox',
          '--disable-dev-shm-usage',
          '--disable-accelerated-2d-canvas',
          '--no-first-run',
          '--no-zygote',
          '--single-process',
          '--disable-gpu'
        ],
        defaultViewport: chromium.defaultViewport,
        executablePath: await chromium.executablePath(),
        headless: chromium.headless,
        ignoreHTTPSErrors: true,
      })
    } else {
      // For local development - try different approaches
      try {
        // First try with system Chrome
        return await puppeteer.launch({
          headless: true,
          args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            '--disable-gpu',
            '--disable-web-security'
          ],
          ignoreHTTPSErrors: true,
        })
      } catch (error) {
        console.log('Failed to launch with system Chrome, trying with bundled Chromium...')
        
        // Fallback to bundled Chromium
        return await puppeteer.launch({
          headless: true,
          args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage'
          ],
          ignoreHTTPSErrors: true,
        })
      }
    }
  } catch (error) {
    console.error('Failed to launch browser:', error)
    throw new Error(`Browser launch failed: ${error instanceof Error ? error.message : 'Unknown error'}`)
  }
}

function extractEmails(html: string): string[] {
  const filteredEmails = new Set<string>();
  
  try {
    const dom = new JSDOM(html);
    const document = dom.window.document;
    
    // Advanced email regex - handles various email formats
    const emailPattern = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g;
    
    // 1. Extract from text content
    const emails = html.match(emailPattern) || [];
    for (const email of emails) {
      if (isValidEmail(email)) {
        filteredEmails.add(normalizeEmail(email));
      }
    }
    
    // 2. Extract from data attributes (data-email, data-mail)
    const elementsWithDataEmail = document.querySelectorAll('[data-email], [data-mail]');
    elementsWithDataEmail.forEach(element => {
      const dataEmail = element.getAttribute('data-email') || element.getAttribute('data-mail');
      if (dataEmail && isValidEmail(dataEmail)) {
        filteredEmails.add(normalizeEmail(dataEmail));
      }
    });
    
    // 3. Extract from meta tags
    const metaTags = document.querySelectorAll('meta[content*="@"], meta[name*="email"], meta[property*="email"]');
    metaTags.forEach(meta => {
      const content = meta.getAttribute('content') || '';
      const metaEmails = content.match(emailPattern) || [];
      metaEmails.forEach(email => {
        if (isValidEmail(email)) {
          filteredEmails.add(normalizeEmail(email));
        }
      });
    });
    
    // 4. Extract from HTML comments
    const commentPattern = /<!--[\s\S]*?-->/g;
    const comments = html.match(commentPattern) || [];
    comments.forEach(comment => {
      const commentEmails = comment.match(emailPattern) || [];
      commentEmails.forEach(email => {
        if (isValidEmail(email)) {
          filteredEmails.add(normalizeEmail(email));
        }
      });
    });
    
    // 5. Extract from JSON-LD structured data
    const jsonLdScripts = document.querySelectorAll('script[type="application/ld+json"]');
    jsonLdScripts.forEach(script => {
      try {
        const jsonData = JSON.parse(script.textContent || '');
        const jsonString = JSON.stringify(jsonData);
        const jsonEmails = jsonString.match(emailPattern) || [];
        jsonEmails.forEach(email => {
          if (isValidEmail(email)) {
            filteredEmails.add(normalizeEmail(email));
          }
        });
      } catch (e) {
        // Continue if JSON parsing fails
      }
    });
    
    // 6. Pattern for emails with "at" and "dot" text encoding
    const encodedPattern = /([a-zA-Z0-9._%+-]+)[\s]*(?:\[at\]|@|[\(\[\{]at[\)\]\}]|&#64;|%40)[\s]*([a-zA-Z0-9.-]+)[\s]*(?:\[dot\]|\.|\(dot\)|\[dot\]|&#46;|%2E)[\s]*([a-zA-Z]{2,})/gi;
    let encodedMatch;
    while ((encodedMatch = encodedPattern.exec(html)) !== null) {
      if (encodedMatch[1] && encodedMatch[2] && encodedMatch[3]) {
        const email = `${encodedMatch[1].trim()}@${encodedMatch[2].trim()}.${encodedMatch[3].trim()}`;
        if (isValidEmail(email)) {
          filteredEmails.add(normalizeEmail(email));
        }
      }
    }
    
    // 7. Pattern for JavaScript obfuscated emails
    const jsPattern = /document\.write\(['"]([a-zA-Z0-9._%+-]+)['"][\s]*\+[\s]*['"]@['"][\s]*\+[\s]*['"]([a-zA-Z0-9.-]+)[\s]*['"][\s]*\+[\s]*['"]\.['"]\ s*\+\s*['"]([a-zA-Z]{2,})['"]/g;
    let jsMatch;
    while ((jsMatch = jsPattern.exec(html)) !== null) {
      if (jsMatch[1] && jsMatch[2] && jsMatch[3]) {
        const email = `${jsMatch[1]}@${jsMatch[2]}.${jsMatch[3]}`;
        if (isValidEmail(email)) {
          filteredEmails.add(normalizeEmail(email));
        }
      }
    }
    
    // 8. Pattern for HTML entity encoded emails
    const htmlEntityPattern = /([a-zA-Z0-9._%+-]+)(?:&#64;|&#0*64;|%40)([a-zA-Z0-9.-]+)(?:&#46;|&#0*46;|%2E)([a-zA-Z]{2,})/g;
    let entityMatch;
    while ((entityMatch = htmlEntityPattern.exec(html)) !== null) {
      if (entityMatch[1] && entityMatch[2] && entityMatch[3]) {
        const email = `${entityMatch[1]}@${entityMatch[2]}.${entityMatch[3]}`;
        if (isValidEmail(email)) {
          filteredEmails.add(normalizeEmail(email));
        }
      }
    }
    
    // 9. Pattern for URL encoded emails (user%40example%2Ecom)
    const urlEncodedPattern = /([a-zA-Z0-9._%+-]+)%40([a-zA-Z0-9.-]+)%2E([a-zA-Z]{2,})/g;
    let urlMatch;
    while ((urlMatch = urlEncodedPattern.exec(html)) !== null) {
      if (urlMatch[1] && urlMatch[2] && urlMatch[3]) {
        const email = `${urlMatch[1]}@${urlMatch[2]}.${urlMatch[3]}`;
        if (isValidEmail(email)) {
          filteredEmails.add(normalizeEmail(email));
        }
      }
    }
    
    // 10. Pattern for separated email parts with CSS display tricks
    const cssPattern = /<span[^>]*data-user=["']([^"']+)["'][^>]*>.*?<\/span>.*?<span[^>]*data-domain=["']([^"']+)["'][^>]*>.*?<\/span>/g;
    let cssMatch;
    while ((cssMatch = cssPattern.exec(html)) !== null) {
      if (cssMatch[1] && cssMatch[2]) {
        const email = `${cssMatch[1]}@${cssMatch[2]}`;
        if (isValidEmail(email)) {
          filteredEmails.add(normalizeEmail(email));
        }
      }
    }
    
    // 11. Pattern for unicode obfuscation
    const unicodePattern = /([a-zA-Z0-9._%+-]+)(?:\\u0*40|\\x40)([a-zA-Z0-9.-]+)(?:\\u0*2e|\\x2e)([a-zA-Z]{2,})/g;
    let unicodeMatch;
    while ((unicodeMatch = unicodePattern.exec(html)) !== null) {
      if (unicodeMatch[1] && unicodeMatch[2] && unicodeMatch[3]) {
        const email = `${unicodeMatch[1]}@${unicodeMatch[2]}.${unicodeMatch[3]}`;
        if (isValidEmail(email)) {
          filteredEmails.add(normalizeEmail(email));
        }
      }
    }
    
  } catch (error) {
    console.error('Error in extractEmails:', error);
  }
  
  return Array.from(filteredEmails);
}

// Enhanced email normalization function
function normalizeEmail(email: string): string {
  return email
    .toLowerCase()
    .trim()
    .replace(/['"]/g, '') // Remove quotes
    .replace(/\s+/g, '') // Remove whitespace
    .replace(/[\[\(]?\s*at\s*[\]\)]?/gi, '@') // Convert "at" to @
    .replace(/[\[\(]?\s*dot\s*[\]\)]?/gi, '.') // Convert "dot" to .
    .replace(/&#64;/g, '@') // Convert HTML entity for @
    .replace(/&#46;/g, '.') // Convert HTML entity for .
    .replace(/%40/g, '@') // Convert URL encoded @
    .replace(/%2E/gi, '.'); // Convert URL encoded .
}

function findImageEmails(html: string): string[] {
  const emails: string[] = [];
  const emailPattern = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g;
  
  try {
    const dom = new JSDOM(html);
    const document = dom.window.document;
    
    // Find all images with alt attributes
    const images = document.querySelectorAll('img[alt]');
    images.forEach(img => {
      const altText = img.getAttribute('alt') || '';
      const matches = altText.match(emailPattern) || [];
      matches.forEach(email => {
        if (email.includes('@') && email.includes('.')) {
          emails.push(email.toLowerCase());
        }
      });
    });
    
    // Also check title attributes which sometimes contain emails
    const elementsWithTitle = document.querySelectorAll('[title]');
    elementsWithTitle.forEach(elem => {
      const titleText = elem.getAttribute('title') || '';
      const matches = titleText.match(emailPattern) || [];
      matches.forEach(email => {
        if (email.includes('@') && email.includes('.')) {
          emails.push(email.toLowerCase());
        }
      });
    });
  } catch (error) {
    console.error('Error finding image emails:', error);
  }
  
  return Array.from(new Set(emails));
}

function findMailtoLinks(html: string): string[] {
  const emails: string[] = [];
  
  try {
    const dom = new JSDOM(html);
    const document = dom.window.document;
    
    // Find all mailto links
    const mailtoLinks = document.querySelectorAll('a[href^="mailto:"]');
    mailtoLinks.forEach(link => {
      const href = link.getAttribute('href') || '';
      if (href.startsWith('mailto:')) {
        // Extract email from mailto: link
        const email = href.replace('mailto:', '').trim();
        // Remove any query parameters
        const cleanEmail = email.split('?')[0].trim();
        if (cleanEmail.includes('@') && cleanEmail.includes('.')) {
          emails.push(cleanEmail.toLowerCase());
        }
      }
    });
  } catch (error) {
    console.error('Error finding mailto links:', error);
  }
  
  return Array.from(new Set(emails));
}

// Enhanced email validation function
function isValidEmail(email: string): boolean {
  // Basic validation checks
  if (!email || email.length < 5 || email.length > 254) return false
  
  // More comprehensive email regex validation
  const emailRegex = /^[a-zA-Z0-9]([a-zA-Z0-9._%-]*[a-zA-Z0-9])?@[a-zA-Z0-9]([a-zA-Z0-9.-]*[a-zA-Z0-9])?\.[a-zA-Z]{2,}$/
  if (!emailRegex.test(email)) return false
  
  // Check for invalid patterns
  const invalidPatterns = [
    /\.(png|jpg|jpeg|gif|svg|webp|bmp|ico|pdf|doc|docx|xls|xlsx|ppt|pptx|zip|rar|tar|gz)$/i,
    /^(example|test|sample|demo|placeholder|noreply|no-reply|donotreply|admin|webmaster|postmaster|info|support|sales|marketing|hello|contact)@/i,
    /@(example|test|sample|demo|localhost|domain|yoursite|yourdomain|company|website|site|email|mail|tempmail|10minutemail|guerrillamail|mailinator)\.com$/i,
    /\.(js|css|html|php|asp|jsp|xml|json|txt|log)$/i,
    /\s/,
    /\.{2,}/,
    /@{2,}/,
    /^[.-]/,
    /[.-]$/,
    /@[.-]/,
    /[.-]@/,
    /@.*@/,
    /\.\./,
    /^\.|\.$|@\.|\.@/,
    /@(gmail|yahoo|hotmail|outlook|aol|live|msn|icloud|me|mac)\.co$/i, // Incomplete domains
    /@.*\.(co|ne|or|go)$/i, // Incomplete TLDs
    /image|photo|picture|img|icon|logo|banner/i,
    /\d{10,}/, // Long numbers that might be phone numbers
    /password|login|signin|signup|register/i
  ]
  
  // Check for suspicious patterns
  const suspiciousPatterns = [
    /^[a-z]{1,2}@/, // Very short usernames
    /@[a-z]{1,2}\./i, // Very short domains
    /\.(tk|ml|ga|cf)$/i, // Free domains often used for spam
    /[0-9]{5,}@/, // Long numbers in username
    /@[0-9]+\./i, // Numeric domains
    /\+.*\+/, // Multiple plus signs
    /_{3,}|\.{3,}|-{3,}/, // Repeated special characters
  ]
  
  return !invalidPatterns.some(pattern => pattern.test(email)) && 
         !suspiciousPatterns.some(pattern => pattern.test(email))
}



// Enhanced Cloudflare email decoding (matches Python version)
function decodeCloudflareEmail(encodedEmail: string): string {
  try {
    const encoded = encodedEmail.replace(/[a-zA-Z]/g, '')
    if (!encoded) return ''
    
    const key = parseInt(encoded.substr(0, 2), 16)
    let decoded = ''
    
    for (let i = 2; i < encoded.length; i += 2) {
      const charCode = parseInt(encoded.substr(i, 2), 16) ^ key
      decoded += String.fromCharCode(charCode)
    }
    
    return decoded
  } catch (error) {
    return ''
  }
}

function findCloudflareEmails(html: string): string[] {
  const emails: string[] = []
  
  // Look for Cloudflare protected emails
  const cfPattern = /data-cfemail\s*=\s*["']([a-f0-9]+)["']/gi
  let match
  
  while ((match = cfPattern.exec(html)) !== null) {
    const decoded = decodeCloudflareEmail(match[1])
    if (decoded && EMAIL_REGEX.test(decoded)) {
      emails.push(decoded)
    }
  }
  
  return emails
}

// Enhanced contact page detection with additional page types
function findContactLinks(dom: Document, baseUrl: string): string[] {
  const contactLinks = new Set<string>()
  const domain = new URL(baseUrl).origin
  
  // Enhanced contact page keywords including privacy, terms, etc.
  const contactKeywords = [
    // Contact pages
    'contact', 'contacts', 'contact-us', 'contactus', 'contact_us',
    'about', 'about-us', 'aboutus', 'about_us',
    'team', 'staff', 'people', 'leadership',
    'support', 'help', 'customer-service',
    'reach-us', 'get-in-touch', 'connect',
    // Additional pages that often contain emails
    'privacy', 'privacy-policy', 'privacy_policy', 'privacypolicy',
    'terms', 'terms-and-conditions', 'terms_and_conditions', 'termsandconditions',
    'terms-of-service', 'terms_of_service', 'termsofservice',
    'who-we-are', 'who_we_are', 'whoweare',
    'cookie', 'cookie-policy', 'cookie_policy', 'cookiepolicy',
    'cookies', 'cookies-policy', 'cookies_policy', 'cookiespolicy',
    'legal', 'disclaimer', 'imprint', 'impressum'
  ]
  
  // Find links that might be contact pages
  const links = dom.querySelectorAll('a[href]')
  
  links.forEach(element => {
    const href = element.getAttribute('href')
    const text = element.textContent?.toLowerCase().trim() || ''
    
    if (href) {
      let fullUrl = ''
      
      // Handle relative URLs
      if (href.startsWith('/')) {
        fullUrl = domain + href
      } else if (href.startsWith('http')) {
        // Only include same domain links
        if (href.includes(new URL(baseUrl).hostname)) {
          fullUrl = href
        }
      } else if (!href.startsWith('#') && !href.startsWith('mailto:') && !href.startsWith('tel:')) {
        fullUrl = domain + '/' + href
      }
      
      // Check if URL or text contains contact keywords
      if (fullUrl) {
        const urlLower = fullUrl.toLowerCase()
        const textLower = text.toLowerCase()
        
        const isContactPage = contactKeywords.some(keyword => 
          urlLower.includes(keyword) || textLower.includes(keyword)
        )
        
        if (isContactPage && fullUrl !== baseUrl) {
          contactLinks.add(fullUrl)
        }
      }
    }
  })
  
  return Array.from(contactLinks).slice(0, 5) // Increased to 5 pages for better coverage
}

// New function: Enhanced page discovery for specific page types
function findSpecificPages(dom: Document, baseUrl: string): { [key: string]: string[] } {
  const domain = new URL(baseUrl).origin
  const pageTypes = {
    privacy: ['privacy', 'privacy-policy', 'privacy_policy', 'privacypolicy'],
    terms: ['terms', 'terms-and-conditions', 'terms_and_conditions', 'termsandconditions', 'terms-of-service', 'terms_of_service', 'termsofservice'],
    about: ['about', 'about-us', 'aboutus', 'about_us', 'who-we-are', 'who_we_are', 'whoweare', 'team', 'staff', 'people'],
    contact: ['contact', 'contacts', 'contact-us', 'contactus', 'contact_us', 'support', 'help', 'get-in-touch', 'reach-us']
  }
  
  const foundPages: { [key: string]: string[] } = {
    privacy: [],
    terms: [],
    about: [],
    contact: []
  }
  
  const links = dom.querySelectorAll('a[href]')
  
  links.forEach(element => {
    const href = element.getAttribute('href')
    const text = element.textContent?.toLowerCase().trim() || ''
    
    if (href) {
      let fullUrl = ''
      
      // Handle relative URLs
      if (href.startsWith('/')) {
        fullUrl = domain + href
      } else if (href.startsWith('http')) {
        if (href.includes(new URL(baseUrl).hostname)) {
          fullUrl = href
        }
      } else if (!href.startsWith('#') && !href.startsWith('mailto:') && !href.startsWith('tel:')) {
        fullUrl = domain + '/' + href
      }
      
      if (fullUrl && fullUrl !== baseUrl) {
        const urlLower = fullUrl.toLowerCase()
        const textLower = text.toLowerCase()
        
        // Check each page type
        Object.entries(pageTypes).forEach(([pageType, keywords]) => {
          const matches = keywords.some(keyword => 
            urlLower.includes(keyword) || textLower.includes(keyword)
          )
          
          if (matches && foundPages[pageType].length < 2) { // Limit to 2 per type
            foundPages[pageType].push(fullUrl)
          }
        })
      }
    }
  })
  
  return foundPages
}

// New function: Extract emails from JavaScript content
async function extractJavaScriptEmails(page: any): Promise<string[]> {
  const emails: string[] = []
  
  try {
    // Wait for any dynamic content to load
    await page.waitForTimeout(2000)
    
    // Execute JavaScript to find emails in various ways
    const jsEmails = await page.evaluate(() => {
      const foundEmails: string[] = []
      const emailRegex = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g
      
      // 1. Check all script tags for email patterns
      const scripts = document.querySelectorAll('script')
      scripts.forEach(script => {
        if (script.textContent) {
          const matches = script.textContent.match(emailRegex)
          if (matches) {
            foundEmails.push(...matches)
          }
        }
      })
      
      // 2. Check for emails in data attributes
      const elementsWithData = document.querySelectorAll('[data-email], [data-mail], [data-contact]')
      elementsWithData.forEach(el => {
        const dataEmail = el.getAttribute('data-email') || el.getAttribute('data-mail') || el.getAttribute('data-contact')
        if (dataEmail && emailRegex.test(dataEmail)) {
          foundEmails.push(dataEmail)
        }
      })
      
      // 3. Check for emails in JavaScript variables
      const pageContent = document.documentElement.outerHTML
      const jsVarPatterns = [
        /email\s*[:=]\s*["']([^"']+@[^"']+)["']/gi,
        /mail\s*[:=]\s*["']([^"']+@[^"']+)["']/gi,
        /contact\s*[:=]\s*["']([^"']+@[^"']+)["']/gi,
        /emailAddress\s*[:=]\s*["']([^"']+@[^"']+)["']/gi
      ]
      
      jsVarPatterns.forEach(pattern => {
        let match
        while ((match = pattern.exec(pageContent)) !== null) {
          if (emailRegex.test(match[1])) {
            foundEmails.push(match[1])
          }
        }
      })
      
      // 4. Check for dynamically loaded content
      const dynamicElements = document.querySelectorAll('[id*="email"], [class*="email"], [id*="contact"], [class*="contact"]')
      dynamicElements.forEach(el => {
        const text = el.textContent || el.innerHTML
        if (text) {
          const matches = text.match(emailRegex)
          if (matches) {
            foundEmails.push(...matches)
          }
        }
      })
      
      return foundEmails
    })
    
    emails.push(...jsEmails)
    
    // Wait for AJAX requests to complete
    await page.waitForTimeout(1000)
    
    // Check for emails loaded via AJAX
    const ajaxEmails = await page.evaluate(() => {
      const foundEmails: string[] = []
      const emailRegex = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g
      
      // Check for newly loaded content
      const newContent = document.body.innerHTML
      const matches = newContent.match(emailRegex)
      if (matches) {
        foundEmails.push(...matches)
      }
      
      return foundEmails
    })
    
    emails.push(...ajaxEmails)
    
  } catch (error) {
    console.error('Error extracting JavaScript emails:', error)
  }
  
  return Array.from(new Set(emails.filter(email => isValidEmail(email))))
}

// New function: Extract emails from page source analysis
async function extractPageSourceEmails(page: any): Promise<string[]> {
  const emails: string[] = []
  
  try {
    // Get the raw page source
    const pageSource = await page.content()
    
    // Enhanced email patterns for page source
    const sourcePatterns = [
      // Standard email pattern
      /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g,
      // Emails in comments
      /<!--[\s\S]*?([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})[\s\S]*?-->/g,
      // Emails in meta tags
      /<meta[^>]*content\s*=\s*["']([^"']*[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}[^"']*)["']/gi,
      // Emails in JSON-LD
      /"email"\s*:\s*"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"/gi,
      // Emails in data attributes
      /data-[a-z-]*\s*=\s*["']([^"']*[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}[^"']*)["']/gi,
      // Emails in JavaScript strings
      /["']([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})["']/g,
      // Emails in CSS content
      /content\s*:\s*["']([^"']*[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}[^"']*)["']/gi
    ]
    
    sourcePatterns.forEach(pattern => {
      let match
      while ((match = pattern.exec(pageSource)) !== null) {
        const email = match[1] || match[0]
        if (email && isValidEmail(email)) {
          emails.push(email)
        }
      }
    })
    
    // Look for obfuscated emails in source
    const obfuscatedPatterns = [
      // Emails with [at] or (at)
      /([a-zA-Z0-9._%+-]+)\s*[\[\(]at[\]\)]\s*([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/gi,
      // Emails with [dot] or (dot)
      /([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+)\s*[\[\(]dot[\]\)]\s*([a-zA-Z]{2,})/gi,
      // Emails with spaces
      /([a-zA-Z0-9._%+-]+)\s+@\s+([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/gi
    ]
    
    obfuscatedPatterns.forEach(pattern => {
      let match
      while ((match = pattern.exec(pageSource)) !== null) {
        let email = ''
        if (pattern.source.includes('at')) {
          email = `${match[1]}@${match[2]}`
        } else if (pattern.source.includes('dot')) {
          email = `${match[1]}.${match[2]}`
        } else {
          email = `${match[1]}@${match[2]}`
        }
        
        if (isValidEmail(email)) {
          emails.push(email)
        }
      }
    })
    
  } catch (error) {
    console.error('Error extracting page source emails:', error)
  }
  
  return Array.from(new Set(emails))
}

// New function: Scrape specific page types for emails
async function scrapeSpecificPages(specificPages: { [key: string]: string[] }): Promise<string[]> {
  const allEmails: string[] = []
  
  for (const [pageType, urls] of Object.entries(specificPages)) {
    if (urls.length === 0) continue
    
    console.log(`Scraping ${pageType} pages:`, urls)
    
    for (const url of urls) {
      try {
        const browser = await browserPool.getBrowser()
        const page = await browser.newPage()
        
        // Optimized settings
        await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        await page.setViewport({ width: 1366, height: 768 })
        
        // Block resources for faster loading
        await page.setRequestInterception(true)
        page.on('request', (req: any) => {
          const resourceType = req.resourceType()
          if (resourceType === 'image' || resourceType === 'stylesheet' || resourceType === 'font') {
            req.abort()
          } else {
            req.continue()
          }
        })
        
        await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 15000 })
        await page.waitForTimeout(1000)
        
        // Extract emails using all methods
        const [
          basicEmails,
          jsEmails,
          sourceEmails,
          mailtoEmails,
          cloudflareEmails
        ] = await Promise.all([
          extractEmails(await page.content()),
          extractJavaScriptEmails(page),
          extractPageSourceEmails(page),
          findMailtoLinks(await page.content()),
          findCloudflareEmails(await page.content())
        ])
        
        allEmails.push(...basicEmails, ...jsEmails, ...sourceEmails, ...mailtoEmails, ...cloudflareEmails)
        
        await page.close()
        
      } catch (error) {
        console.error(`Error scraping ${pageType} page ${url}:`, error)
      }
    }
  }
  
  return Array.from(new Set(allEmails.filter(email => isValidEmail(email))))
}

// Legacy scraping function (kept for compatibility)
async function scrapeUrl(url: string): Promise<ScrapedData> {
  let browser
  let page
  
  try {
    // Normalize URL
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      url = 'https://' + url
    }
    
    const domain = new URL(url).hostname
    console.log(`Starting to scrape: ${url}`)
    
    browser = await getBrowser()
    page = await browser.newPage()
    
    // Set enhanced user agent and viewport (matches Python version)
    await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    await page.setViewport({ width: 1366, height: 768 })
    
    // Set extra headers to avoid detection
    await page.setExtraHTTPHeaders({
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
      'Accept-Language': 'en-US,en;q=0.5',
      'Accept-Encoding': 'gzip, deflate',
      'Connection': 'keep-alive',
      'Upgrade-Insecure-Requests': '1',
    })
    
    // Navigate to page with enhanced timeout and error handling
    await page.goto(url, { 
      waitUntil: 'domcontentloaded', 
      timeout: 45000 
    })
    
    // Wait for page to fully load
    await page.waitForTimeout(2000)
    
    // Get page content with retry logic for navigation errors
    let html: string
    try {
      html = await page.content()
    } catch (error) {
      console.log('First attempt to get content failed, retrying...')
      await page.waitForTimeout(1000)
      try {
        html = await page.content()
      } catch (retryError) {
        console.log('Retry failed, attempting page reload...')
        await page.reload({ waitUntil: 'domcontentloaded', timeout: 30000 })
        await page.waitForTimeout(1000)
        html = await page.content()
      }
    }
    
    const dom = new JSDOM(html)
    const document = dom.window.document
    const text = document.body?.textContent || ''
    
    console.log(`Extracting data from: ${url}`)
    
    // Extract emails with enhanced methods (Python-based logic)
    let emails = extractEmails(html)
    
    // Add image emails
    const imageEmails = findImageEmails(html)
    emails.push(...imageEmails)
    
    // Add mailto link emails
    const mailtoEmails = findMailtoLinks(html)
    emails.push(...mailtoEmails)
    
    // Check for Cloudflare protected emails
    const cfEmails = findCloudflareEmails(html)
    emails.push(...cfEmails)
    
    console.log(`Found ${emails.length} emails on main page`)
    
    // Enhanced mailto discovery: Check all common pages for mailto links
    const commonPageEmails = await scrapeCommonPagesForMailto(page, url)
    emails.push(...commonPageEmails)
    
    console.log(`Found ${commonPageEmails.length} additional emails from common pages`)
    
    // Find and scrape contact pages
    const contactLinks = findContactLinks(document, url)
    console.log(`Found ${contactLinks.length} contact pages to scrape`)
    
    for (const contactUrl of contactLinks) {
      try {
        console.log(`Scraping contact page: ${contactUrl}`)
        
        await page.goto(contactUrl, { 
          waitUntil: 'domcontentloaded', 
          timeout: 30000 
        })
        
        await page.waitForTimeout(1500)
        
        const contactHtml = await page.content()
        const contactDom = new JSDOM(contactHtml)
        const contactDocument = contactDom.window.document
        const contactText = contactDocument.body?.textContent || ''
        
        const contactEmails = extractEmails(contactHtml)
        
        emails.push(...contactEmails)
        
        // Check for Cloudflare emails on contact page
        const contactCfEmails = findCloudflareEmails(contactHtml)
        emails.push(...contactCfEmails)
        
        console.log(`Contact page ${contactUrl}: +${contactEmails.length} emails`)
        
        // Small delay between requests
        await page.waitForTimeout(1000)
      } catch (error) {
        console.log(`Failed to scrape contact page ${contactUrl}:`, error instanceof Error ? error.message : 'Unknown error')
      }
    }
    
    // Remove duplicates and clean data
    emails = [...new Set(emails.filter(email => email && email.length > 0))]
    
    console.log(`Final results for ${url}: ${emails.length} emails`)
    
    return {
      url,
      domain,
      emails,
      status: 'success'
    }
    
  } catch (error) {
    console.error(`Error scraping ${url}:`, error)
    
    // Return partial results if we have any emails before the error
    const partialEmails = []
    try {
      if (page) {
        // Try to get whatever content we can
        const html = await page.content()
        const extractedEmails = extractEmails(html)
        const mailtoEmails = findMailtoLinks(html)
        partialEmails.push(...extractedEmails, ...mailtoEmails)
      }
    } catch (recoveryError) {
      console.log('Could not recover any emails from failed page')
    }
    
    return {
      url,
      domain: url.startsWith('http') ? new URL(url).hostname : url,
      emails: [...new Set(partialEmails.filter(email => email && email.length > 0))],
      status: 'error',
      error: error instanceof Error ? error.message : 'Unknown error'
    }
  } finally {
    if (page) {
      try {
        await page.close()
      } catch (e) {
        console.log('Error closing page:', e)
      }
    }
    if (browser) {
      try {
        await browser.close()
      } catch (e) {
        console.log('Error closing browser:', e)
      }
    }
  }
}

// Function to generate common page URLs for comprehensive mailto discovery
function generateCommonPageUrls(baseUrl: string): string[] {
  const commonPages = [
    '', // Homepage
    '/',
    '/contact',
    '/contact-us',
    '/contactus',
    '/contact_us',
    '/contact.html',
    '/contact.php',
    '/about',
    '/about-us',
    '/aboutus',
    '/about_us',
    '/about.html',
    '/about.php',
    '/privacy',
    '/privacy-policy',
    '/privacy_policy',
    '/privacypolicy',
    '/privacy.html',
    '/privacy.php',
    '/cookie',
    '/cookie-policy',
    '/cookie_policy',
    '/cookiepolicy',
    '/cookies',
    '/cookies.html',
    '/terms',
    '/terms-of-service',
    '/terms_of_service',
    '/termsofservice',
    '/terms.html',
    '/legal',
    '/legal.html',
    '/support',
    '/help',
    '/faq',
    '/team',
    '/staff',
    '/leadership',
    '/management',
    '/footer',
    '/sitemap',
    '/sitemap.html'
  ];

  const urls: string[] = [];
  const baseUrlObj = new URL(baseUrl);
  const baseUrlClean = `${baseUrlObj.protocol}//${baseUrlObj.hostname}`;

  for (const page of commonPages) {
    try {
      const fullUrl = page === '' || page === '/' 
        ? baseUrlClean 
        : `${baseUrlClean}${page.startsWith('/') ? page : '/' + page}`;
      urls.push(fullUrl);
    } catch (error) {
      console.log(`Error generating URL for page ${page}:`, error);
    }
  }

  // Remove duplicates
  return [...new Set(urls)];
}

// Enhanced function to scrape mailto links from common pages
async function scrapeCommonPagesForMailto(page: any, baseUrl: string): Promise<string[]> {
  const allEmails: string[] = [];
  const commonUrls = generateCommonPageUrls(baseUrl);
  
  console.log(`Checking ${commonUrls.length} common pages for mailto links...`);
  
  for (const url of commonUrls) {
    try {
      console.log(`Checking mailto links on: ${url}`);
      
      // Navigate to the page
      await page.goto(url, { 
        waitUntil: 'domcontentloaded', 
        timeout: 20000 
      });
      
      // Wait for page to load
      await page.waitForTimeout(1000);
      
      // Get page content with retry logic for navigation errors
      let html: string;
      try {
        html = await page.content();
      } catch (error) {
        console.log(`First attempt to get content failed for ${url}, retrying...`);
        await page.waitForTimeout(500);
        try {
          html = await page.content();
        } catch (retryError) {
          console.log(`Retry failed for ${url}, skipping this page`);
          continue;
        }
      }
      
      // Extract mailto links from this page
      const mailtoEmails = findMailtoLinks(html);
      
      if (mailtoEmails.length > 0) {
        console.log(`Found ${mailtoEmails.length} mailto links on ${url}`);
        allEmails.push(...mailtoEmails);
      }
      
      // Also extract any other emails from the page content
      const pageEmails = extractEmails(html);
      allEmails.push(...pageEmails);
      
      // Small delay between requests to be respectful
      await page.waitForTimeout(500);
      
    } catch (error) {
      console.log(`Failed to check mailto links on ${url}:`, error instanceof Error ? error.message : 'Unknown error');
      // Continue with next page even if this one fails
      continue;
    }
  }
  
  // Remove duplicates and return
  const uniqueEmails = [...new Set(allEmails.filter(email => email && email.length > 0))];
  console.log(`Total unique emails found from common pages: ${uniqueEmails.length}`);
  
  return uniqueEmails;
}

// Enhanced optimized scraping function with JavaScript and page source extraction
async function scrapeUrlOptimized(url: string): Promise<ScrapedData> {
  let page

  try {
    // Normalize URL
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      url = 'https://' + url
    }

    const domain = new URL(url).hostname
    console.log(`Starting enhanced optimized scrape: ${url}`)

    const browser = await browserPool.getBrowser()
    page = await browser.newPage()

    // Optimized page settings for faster loading
    await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    await page.setViewport({ width: 1366, height: 768 })

    // Block unnecessary resources for faster loading
    await page.setRequestInterception(true)
    page.on('request', (req: any) => {
      const resourceType = req.resourceType()
      if (resourceType === 'image' || resourceType === 'stylesheet' || resourceType === 'font' || resourceType === 'media') {
        req.abort()
      } else {
        req.continue()
      }
    })

    // Set extra headers
    await page.setExtraHTTPHeaders({
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
      'Accept-Language': 'en-US,en;q=0.5',
      'Connection': 'keep-alive',
    })

    // Navigate with reduced timeout for faster processing
    await page.goto(url, { 
      waitUntil: 'domcontentloaded', 
      timeout: 20000 
    })

    // Reduced wait time
    await page.waitForTimeout(1000)

    // Get page content with retry logic
    let html: string
    try {
      html = await page.content()
    } catch (error) {
      console.log('Content retrieval failed, retrying...')
      await page.waitForTimeout(500)
      try {
        html = await page.content()
      } catch (retryError) {
        await page.reload({ waitUntil: 'domcontentloaded', timeout: 15000 })
        await page.waitForTimeout(500)
        html = await page.content()
      }
    }

    const dom = new JSDOM(html)
    const document = dom.window.document

    console.log(`Extracting data from: ${url}`)

    // Find specific pages for enhanced extraction
    const specificPages = findSpecificPages(document, url)
    console.log(`Found specific pages:`, specificPages)

    // Parallel email extraction with enhanced methods
    const [
      basicEmails,
      imageEmails,
      mailtoEmails,
      cfEmails,
      jsEmails,
      sourceEmails,
      specificPageEmails,
      commonPageEmails,
      contactPageEmails
    ] = await Promise.all([
      Promise.resolve(extractEmails(html)),
      Promise.resolve(findImageEmails(html)),
      Promise.resolve(findMailtoLinks(html)),
      Promise.resolve(findCloudflareEmails(html)),
      extractJavaScriptEmails(page),
      extractPageSourceEmails(page),
      scrapeSpecificPages(specificPages),
      scrapeCommonPagesForMailtoOptimized(page, url),
      scrapeContactPagesOptimized(page, document, url)
    ])

    // Combine all emails
    let emails = [
      ...basicEmails,
      ...imageEmails,
      ...mailtoEmails,
      ...cfEmails,
      ...jsEmails,
      ...sourceEmails,
      ...specificPageEmails,
      ...commonPageEmails,
      ...contactPageEmails
    ]

    // Remove duplicates and clean data
    emails = [...new Set(emails.filter(email => email && email.length > 0))]

    console.log(`Enhanced optimized results for ${url}: ${emails.length} emails`)
    console.log(`Email breakdown: Basic(${basicEmails.length}), Images(${imageEmails.length}), Mailto(${mailtoEmails.length}), Cloudflare(${cfEmails.length}), JavaScript(${jsEmails.length}), PageSource(${sourceEmails.length}), SpecificPages(${specificPageEmails.length}), CommonPages(${commonPageEmails.length}), ContactPages(${contactPageEmails.length})`)

    return {
      url,
      domain,
      emails,
      status: 'success'
    }

  } catch (error) {
    console.error(`Error in enhanced optimized scraping ${url}:`, error)

    // Return partial results if possible
    const partialEmails = []
    try {
      if (page) {
        const html = await page.content()
        const extractedEmails = extractEmails(html)
        const mailtoEmails = findMailtoLinks(html)
        partialEmails.push(...extractedEmails, ...mailtoEmails)
      }
    } catch (recoveryError) {
      console.log('Could not recover any emails from failed page')
    }

    return {
      url,
      domain: url.startsWith('http') ? new URL(url).hostname : url,
      emails: [...new Set(partialEmails.filter(email => email && email.length > 0))],
      status: 'error',
      error: error instanceof Error ? error.message : 'Unknown error'
    }
  } finally {
    if (page) {
      try {
        await page.close()
      } catch (e) {
        console.log('Error closing page:', e)
      }
    }
  }
}

// Optimized common pages scraping with parallel processing
async function scrapeCommonPagesForMailtoOptimized(page: any, baseUrl: string): Promise<string[]> {
  const commonUrls = generateCommonPageUrls(baseUrl).slice(0, 15) // Limit to 15 most important pages
  console.log(`Checking ${commonUrls.length} common pages concurrently...`)

  // Process pages in batches of 5 for optimal performance
  const batchSize = 5
  const allEmails: string[] = []

  for (let i = 0; i < commonUrls.length; i += batchSize) {
    const batch = commonUrls.slice(i, i + batchSize)

    const batchPromises = batch.map(async (url) => {
      try {
        await page.goto(url, { 
          waitUntil: 'domcontentloaded', 
          timeout: 10000 
        })

        await page.waitForTimeout(500)

        const html = await page.content()
        const mailtoEmails = findMailtoLinks(html)
        const pageEmails = extractEmails(html)

        return [...mailtoEmails, ...pageEmails]
      } catch (error) {
        console.log(`Failed to scrape common page ${url}:`, error instanceof Error ? error.message : 'Unknown error')
        return []
      }
    })

    const batchResults = await Promise.allSettled(batchPromises)
    batchResults.forEach(result => {
      if (result.status === 'fulfilled') {
        allEmails.push(...result.value)
      }
    })

    // Small delay between batches
    await page.waitForTimeout(200)
  }

  const uniqueEmails = [...new Set(allEmails.filter(email => email && email.length > 0))]
  console.log(`Found ${uniqueEmails.length} emails from common pages`)

  return uniqueEmails
}

// Optimized contact pages scraping
async function scrapeContactPagesOptimized(page: any, document: Document, baseUrl: string): Promise<string[]> {
  const contactLinks = findContactLinks(document, baseUrl)
  console.log(`Found ${contactLinks.length} contact pages to scrape`)

  const contactEmails: string[] = []

  // Process contact pages sequentially but with optimized settings
  for (const contactUrl of contactLinks) {
    try {
      console.log(`Scraping contact page: ${contactUrl}`)

      await page.goto(contactUrl, { 
        waitUntil: 'domcontentloaded', 
        timeout: 15000 
      })

      await page.waitForTimeout(800)

      const contactHtml = await page.content()
      
      // Enhanced extraction for contact pages
      const [
        pageEmails,
        cfEmails,
        mailtoEmails,
        jsEmails,
        sourceEmails
      ] = await Promise.all([
        Promise.resolve(extractEmails(contactHtml)),
        Promise.resolve(findCloudflareEmails(contactHtml)),
        Promise.resolve(findMailtoLinks(contactHtml)),
        extractJavaScriptEmails(page),
        extractPageSourceEmails(page)
      ])

      contactEmails.push(...pageEmails, ...cfEmails, ...mailtoEmails, ...jsEmails, ...sourceEmails)

      console.log(`Contact page ${contactUrl}: +${pageEmails.length + cfEmails.length + mailtoEmails.length + jsEmails.length + sourceEmails.length} emails`)

      // Minimal delay
      await page.waitForTimeout(300)
    } catch (error) {
      console.log(`Failed to scrape contact page ${contactUrl}:`, error instanceof Error ? error.message : 'Unknown error')
    }
  }

  return [...new Set(contactEmails.filter(email => email && email.length > 0))]
}

export async function POST(request: NextRequest) {
  try {
    const { urls } = await request.json()

    if (!urls || !Array.isArray(urls) || urls.length === 0) {
      return NextResponse.json(
        { success: false, error: 'Please provide an array of URLs' },
        { status: 400 }
      )
    }

    if (urls.length > 10) {
      return NextResponse.json(
        { success: false, error: 'Maximum 10 URLs allowed per request' },
        { status: 400 }
      )
    }

    console.log(`Starting enhanced concurrent processing of ${urls.length} URLs...`)

    // Process URLs concurrently with enhanced optimized function
    const validUrls = urls.filter(url => typeof url === 'string' && url.trim())

    // Process in batches of 3 for optimal performance
    const batchSize = 3
    const results: ScrapedData[] = []

    for (let i = 0; i < validUrls.length; i += batchSize) {
      const batch = validUrls.slice(i, i + batchSize)
      console.log(`Processing batch ${Math.floor(i / batchSize) + 1}/${Math.ceil(validUrls.length / batchSize)}`)

      const batchPromises = batch.map(url => scrapeUrlOptimized(url.trim()))
      const batchResults = await Promise.allSettled(batchPromises)

      batchResults.forEach(result => {
        if (result.status === 'fulfilled') {
          results.push(result.value)
        } else {
          console.error('Batch processing error:', result.reason)
          // Add error result
          results.push({
            url: 'unknown',
            domain: 'unknown',
            emails: [],
            status: 'error',
            error: result.reason instanceof Error ? result.reason.message : 'Unknown error'
          })
        }
      })

      // Small delay between batches to prevent overwhelming
      if (i + batchSize < validUrls.length) {
        await new Promise(resolve => setTimeout(resolve, 1000))
      }
    }

    console.log(`Enhanced concurrent processing completed. Total results: ${results.length}`)

    // Cleanup browser pool
    await browserPool.cleanup()

    return NextResponse.json({
      success: true,
      results,
      summary: {
        total_urls: results.length,
        successful: results.filter(r => r.status === 'success').length,
        total_emails: results.reduce((sum, r) => sum + r.emails.length, 0),
        processing_mode: 'enhanced_concurrent_optimized',
        features: [
          'JavaScript email extraction',
          'Page source analysis',
          'Privacy/Terms/About/Contact page scraping',
          'Enhanced obfuscation detection',
          'Concurrent processing',
          'Browser pooling'
        ]
      }
    })

  } catch (error) {
    console.error('API Error:', error)

    // Cleanup on error
    await browserPool.cleanup()

    return NextResponse.json(
      { 
        success: false, 
        error: error instanceof Error ? error.message : 'Internal server error' 
      },
      { status: 500 }
    )
  }
}