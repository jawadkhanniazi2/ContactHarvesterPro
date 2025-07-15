import re
import concurrent.futures
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from bs4 import BeautifulSoup
import time
import logging
import urllib.parse
import requests
from tqdm import tqdm
import os
import sys
import platform

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ContactScraper:
    def __init__(self, max_workers=5, timeout=20, headless=True):
        """
        Initialize the Contact Scraper.
        
        Args:
            max_workers (int): Maximum number of concurrent workers
            timeout (int): Page load timeout in seconds
            headless (bool): Whether to run browser in headless mode
        """
        self.max_workers = max_workers
        self.timeout = timeout
        self.headless = headless
        self.results = []
        
    def setup_driver(self):
        """Set up and configure the Chrome WebDriver."""
        try:
            # Set up Chrome options
            chrome_options = Options()
            if self.headless:
                chrome_options.add_argument('--headless=new')
            
            # Security and performance options
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--ignore-certificate-errors')
            
            # Prevent detection
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Set user agent to mimic real browser
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
            
            # Create driver with configured options - modern approach without Service
            # This should work better on Windows 10
            try:
                logger.info("Attempting to create Chrome WebDriver directly")
                driver = webdriver.Chrome(options=chrome_options)
            except Exception as e:
                logger.warning(f"Direct WebDriver initialization failed: {str(e)}")
                logger.info("Falling back to ChromeDriverManager path")
                
                # Fallback to ChromeDriverManager
                driver_path = ChromeDriverManager().install()
                service = Service(driver_path)
                driver = webdriver.Chrome(service=service, options=chrome_options)
            
            driver.set_page_load_timeout(self.timeout)
            
            # Add undetectable properties to the navigator object
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            return driver
            
        except Exception as e:
            logger.error(f"Failed to set up Chrome driver: {str(e)}")
            raise

    def extract_emails(self, text):
        """
        Extract email addresses from text using advanced pattern matching.
        
        Args:
            text (str): Text to extract emails from
            
        Returns:
            list: List of unique email addresses
        """
        # Advanced email regex - handles various email formats
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        
        # Find all emails using standard pattern
        emails = re.findall(email_pattern, text)
        
        # Set for faster duplicate checking
        filtered_emails = set()
        
        for email in emails:
            # Skip emails with invalid TLDs or likely false positives
            if any(invalid in email.lower() for invalid in ['@example.', '@domain.', '@email.']):
                continue
                
            # Skip emails with suspicious patterns
            if '..' in email or '@.' in email or '.@' in email:
                continue
                
            # Normalized email
            filtered_emails.add(email.lower())
        
        # Additional patterns for protected emails
        
        # Pattern for emails with "at" and "dot" text encoding
        encoded_pattern = r'([a-zA-Z0-9._%+-]+)[\s]*(?:\[at\]|@|[\(\[\{]at[\)\]\}]|&#64;|%40)[\s]*([a-zA-Z0-9.-]+)[\s]*(?:\[dot\]|\.|\(dot\)|\[dot\]|&#46;|%2E)[\s]*([a-zA-Z]{2,})'
        encoded_matches = re.finditer(encoded_pattern, text, re.IGNORECASE)
        for match in encoded_matches:
            if match.group(1) and match.group(2) and match.group(3):
                email = f"{match.group(1).strip()}@{match.group(2).strip()}.{match.group(3).strip()}"
                filtered_emails.add(email.lower())
        
        # Pattern for JavaScript obfuscated emails (common pattern using concatenation)
        js_pattern = r'document\.write\([\'"]([a-zA-Z0-9._%+-]+)[\'"][\s]*\+[\s]*[\'"]@[\'"][\s]*\+[\s]*[\'"]([a-zA-Z0-9.-]+)[\s]*[\'"][\s]*\+[\s]*[\'"]\.[\'"][\s]*\+[\s]*[\'"]([a-zA-Z]{2,})[\'"]'
        js_matches = re.finditer(js_pattern, text)
        for match in js_matches:
            if match.group(1) and match.group(2) and match.group(3):
                email = f"{match.group(1)}@{match.group(2)}.{match.group(3)}"
                filtered_emails.add(email.lower())
        
        # Pattern for HTML entity encoded emails (like &#64; for @ and &#46; for .)
        html_entity_pattern = r'([a-zA-Z0-9._%+-]+)(?:&#64;|&#0*64;|%40)([a-zA-Z0-9.-]+)(?:&#46;|&#0*46;|%2E)([a-zA-Z]{2,})'
        entity_matches = re.finditer(html_entity_pattern, text)
        for match in entity_matches:
            if match.group(1) and match.group(2) and match.group(3):
                email = f"{match.group(1)}@{match.group(2)}.{match.group(3)}"
                filtered_emails.add(email.lower())
        
        # Pattern for separated email parts with CSS display tricks
        # This is a simplified version, as real CSS tricks can be very complex
        css_pattern = r'<span[^>]*data-user=["\']([^"\']+)["\'][^>]*>.*?</span>.*?<span[^>]*data-domain=["\']([^"\']+)["\'][^>]*>.*?</span>'
        css_matches = re.finditer(css_pattern, text)
        for match in css_matches:
            if match.group(1) and match.group(2):
                email = f"{match.group(1)}@{match.group(2)}"
                filtered_emails.add(email.lower())
                
        # Pattern for unicode obfuscation (where @ is replaced by \u0040 and . by \u002E)
        unicode_pattern = r'([a-zA-Z0-9._%+-]+)(?:\\u0*40|\\x40)([a-zA-Z0-9.-]+)(?:\\u0*2e|\\x2e)([a-zA-Z]{2,})'
        unicode_matches = re.finditer(unicode_pattern, text)
        for match in unicode_matches:
            if match.group(1) and match.group(2) and match.group(3):
                email = f"{match.group(1)}@{match.group(2)}.{match.group(3)}"
                filtered_emails.add(email.lower())
                
        return list(filtered_emails)

    def extract_phones(self, text):
        """
        Extract phone numbers from text using advanced pattern matching.
        
        Args:
            text (str): Text to extract phone numbers from
            
        Returns:
            list: List of unique phone numbers
        """
        # International format: +1-123-456-7890, +1 (123) 456-7890, etc.
        international_pattern = r'(?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        
        # US format without country code: (123) 456-7890, 123-456-7890, 123.456.7890, etc.
        us_pattern = r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        
        # Extract phone numbers
        phones = re.findall(international_pattern, text)
        phones.extend(re.findall(us_pattern, text))
        
        # Clean and normalize phone numbers
        normalized_phones = []
        for phone in phones:
            # Remove non-digits
            digits_only = re.sub(r'\D', '', phone)
            
            # Skip if too short or too long
            if len(digits_only) < 10 or len(digits_only) > 15:
                continue
                
            # Add to results
            normalized_phones.append(phone)
            
        return list(set(normalized_phones))

    def extract_social_media(self, text):
        """
        Extract social media links from text.
        
        Args:
            text (str): Text to extract social media links from
            
        Returns:
            dict: Dictionary of social media platforms and their URLs
        """
        social_patterns = {
            'linkedin': r'(?:https?:\/\/)?(?:www\.)?linkedin\.com\/(?:in|company)\/[a-zA-Z0-9_-]+\/?',
            'twitter': r'(?:https?:\/\/)?(?:www\.)?(?:twitter\.com|x\.com)\/[a-zA-Z0-9_-]+\/?',
            'facebook': r'(?:https?:\/\/)?(?:www\.)?facebook\.com\/(?:profile\.php\?id=\d+|[a-zA-Z0-9._-]+)\/?',
            'instagram': r'(?:https?:\/\/)?(?:www\.)?instagram\.com\/[a-zA-Z0-9._-]+\/?',
            'youtube': r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/(?:channel|user)\/[a-zA-Z0-9_-]+\/?',
            'github': r'(?:https?:\/\/)?(?:www\.)?github\.com\/[a-zA-Z0-9_-]+\/?',
        }
        
        social_profiles = {}
        for platform, pattern in social_patterns.items():
            matches = re.findall(pattern, text)
            if matches:
                # Add https:// if not present
                url = matches[0]
                if not url.startswith('http'):
                    url = 'https://' + url.lstrip('/')
                social_profiles[platform] = url
                
        return social_profiles

    def safe_get(self, driver, url, timeout=20):
        """
        Safely navigate to a URL with error handling.
        
        Args:
            driver: Selenium WebDriver
            url (str): URL to navigate to
            timeout (int): Timeout in seconds
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            driver.get(url)
            # Use a shorter timeout for better performance
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            return True
        except TimeoutException:
            logger.warning(f"Timeout loading URL: {url}")
            # Try to continue even if timeout - sometimes we can still get content
            try:
                # If we get some content, consider it a partial success
                if driver.page_source and len(driver.page_source) > 500:
                    logger.info(f"Got partial content for {url} despite timeout")
                    return True
            except:
                pass
            return False
        except WebDriverException as e:
            logger.error(f"Error loading URL {url}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error loading URL {url}: {str(e)}")
            return False
    
    def decode_cloudflare_email(self, encoded_email):
        """
        Decode Cloudflare protected emails.
        
        Cloudflare email protection uses a JavaScript function to decode emails like:
        <a href="/cdn-cgi/l/email-protection#1234567890" data-cfemail="1234567890">Protected Email</a>
        
        Args:
            encoded_email (str): The hex encoded email string
            
        Returns:
            str: Decoded email address or None if decoding fails
        """
        try:
            # Cloudflare encoding uses a simple XOR cipher with the first character as the key
            decoded = ""
            
            # Convert hex to bytes
            hex_encoded = bytes.fromhex(encoded_email)
            
            # First byte is the key
            key = hex_encoded[0]
            
            # Decode each byte with XOR
            for i in range(1, len(hex_encoded)):
                decoded += chr(hex_encoded[i] ^ key)
            
            return decoded
        except Exception as e:
            logger.warning(f"Failed to decode Cloudflare email: {str(e)}")
            return None

    def find_cloudflare_emails(self, html):
        """
        Find Cloudflare protected emails in HTML content.
        
        Args:
            html (str): HTML content
            
        Returns:
            list: List of decoded email addresses
        """
        # Look for Cloudflare protected email patterns
        cf_pattern = r'<a[^>]*href="/cdn-cgi/l/email-protection#([a-zA-Z0-9]+)"[^>]*>.*?</a>'
        cf_data_pattern = r'<a[^>]*data-cfemail="([a-zA-Z0-9]+)"[^>]*>.*?</a>'
        
        emails = []
        
        # Find emails with href pattern
        for match in re.finditer(cf_pattern, html, re.IGNORECASE):
            encoded = match.group(1)
            decoded = self.decode_cloudflare_email(encoded)
            if decoded and '@' in decoded:
                emails.append(decoded.lower())
        
        # Find emails with data-cfemail pattern
        for match in re.finditer(cf_data_pattern, html, re.IGNORECASE):
            encoded = match.group(1)
            decoded = self.decode_cloudflare_email(encoded)
            if decoded and '@' in decoded:
                emails.append(decoded.lower())
        
        return list(set(emails))

    def find_contact_links(self, soup, base_url):
        """
        Find contact page links in the website.
        
        Args:
            soup: BeautifulSoup object
            base_url (str): Base URL of the website
            
        Returns:
            list: List of contact page URLs
        """
        contact_keywords = ['contact', 'kontakt', 'contacto', 'about', 'about us', 'get in touch', 'support']
        contact_links = []
        
        # Find all links
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            link_text = link.get_text().lower()
            
            # Skip if empty href or javascript
            if not href or href.startswith('javascript:') or href == '#':
                continue
                
            # Check if link text contains contact keywords
            if any(keyword in link_text for keyword in contact_keywords):
                # Handle relative URLs
                if not href.startswith(('http://', 'https://')):
                    href = urllib.parse.urljoin(base_url, href)
                contact_links.append(href)
                
            # Also check href itself for contact keywords
            elif any(keyword in href.lower() for keyword in contact_keywords):
                if not href.startswith(('http://', 'https://')):
                    href = urllib.parse.urljoin(base_url, href)
                contact_links.append(href)
                
        return list(set(contact_links))

    def find_image_emails(self, soup):
        """
        Find email addresses in image alt tags.
        
        Some sites put email addresses in image alt attributes to prevent scraping.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            list: List of email addresses
        """
        emails = []
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        
        # Find all images
        for img in soup.find_all('img', alt=True):
            alt_text = img.get('alt', '')
            # Check for email patterns in alt text
            matches = re.findall(email_pattern, alt_text)
            for email in matches:
                if '@' in email and '.' in email:
                    emails.append(email.lower())
        
        # Also check title attributes which sometimes contain emails
        for elem in soup.find_all(title=True):
            title_text = elem.get('title', '')
            matches = re.findall(email_pattern, title_text)
            for email in matches:
                if '@' in email and '.' in email:
                    emails.append(email.lower())
        
        return list(set(emails))
    
    def find_mailto_links(self, soup):
        """
        Extract email addresses from mailto links.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            list: List of email addresses
        """
        emails = []
        
        # Find all mailto links
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            if href.startswith('mailto:'):
                # Extract email from mailto: link
                email = href.replace('mailto:', '').strip()
                # Remove any query parameters
                email = email.split('?')[0].strip()
                if '@' in email and '.' in email:
                    emails.append(email.lower())
        
        return list(set(emails))

    def scrape_url(self, url):
        """
        Scrape contact information from a single URL.
        
        Args:
            url (str): URL to scrape
            
        Returns:
            dict: Dictionary with scraped contact information
        """
        driver = None
        try:
            logger.info(f"Starting to scrape URL: {url}")
            
            # Try to set up the WebDriver with additional error info
            try:
                driver = self.setup_driver()
            except Exception as setup_error:
                error_details = f"WebDriver setup failed: {str(setup_error)}"
                logger.error(error_details)
                return {
                    'url': url,
                    'domain': urllib.parse.urlparse(url).netloc if url.startswith(('http://', 'https://')) else '',
                    'emails': [],
                    'phones': [],
                    'social_media': {},
                    'status': f"Error: {error_details}"
                }
            
            # Normalize URL
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            # Extract domain for later use
            domain = urllib.parse.urlparse(url).netloc
            
            # Load main page
            logger.info(f"Navigating to page: {url}")
            if not self.safe_get(driver, url):
                logger.warning(f"Failed to load page: {url}")
                raise Exception(f"Failed to load page: {url}")
            
            # Get page content
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            text_content = soup.get_text()
            
            # Initial search for contact information
            emails = self.extract_emails(text_content)
            phones = self.extract_phones(text_content)
            social = self.extract_social_media(page_source)
            
            # Check for Cloudflare protected emails
            cloudflare_emails = self.find_cloudflare_emails(page_source)
            if cloudflare_emails:
                logger.info(f"Found {len(cloudflare_emails)} Cloudflare protected emails")
                emails.extend(cloudflare_emails)
            
            # Check for emails in image alt tags
            img_emails = self.find_image_emails(soup)
            if img_emails:
                logger.info(f"Found {len(img_emails)} emails in image alt tags")
                emails.extend(img_emails)
                
            # Check for mailto links
            mailto_emails = self.find_mailto_links(soup)
            if mailto_emails:
                logger.info(f"Found {len(mailto_emails)} emails in mailto links")
                emails.extend(mailto_emails)
            
            # Find contact pages
            contact_links = self.find_contact_links(soup, url)
            
            # Visit contact pages if found
            for contact_url in contact_links[:3]:  # Limit to first 3 contact URLs
                logger.info(f"Found contact page: {contact_url}")
                if self.safe_get(driver, contact_url):
                    contact_source = driver.page_source
                    contact_soup = BeautifulSoup(contact_source, 'html.parser')
                    contact_text = contact_soup.get_text()
                    
                    # Extract additional contact information
                    emails.extend(self.extract_emails(contact_text))
                    phones.extend(self.extract_phones(contact_text))
                    social.update(self.extract_social_media(contact_source))
                    
                    # Short delay to avoid overloading the server
                    time.sleep(1)
            
            # Remove duplicates
            emails = list(set(emails))
            phones = list(set(phones))
            
            logger.info(f"Successfully scraped {url}")
            logger.info(f"Found {len(emails)} emails, {len(phones)} phones, {len(social)} social profiles")
            
            return {
                'url': url,
                'domain': domain,
                'emails': emails,
                'phones': phones,
                'social_media': social,
                'status': 'success'
            }
            
        except Exception as e:
            error_msg = f"Error scraping {url}: {str(e)}"
            logger.error(error_msg)
            return {
                'url': url,
                'domain': urllib.parse.urlparse(url).netloc if url.startswith(('http://', 'https://')) else '',
                'emails': [],
                'phones': [],
                'social_media': {},
                'status': f"Error: {error_msg}"
            }
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception as quit_error:
                    logger.warning(f"Error closing driver: {str(quit_error)}")

    def scrape_urls(self, urls, progress_callback=None):
        """
        Scrape contact information from multiple URLs concurrently.
        
        Args:
            urls (list): List of URLs to scrape
            progress_callback (function): Callback function for progress updates
            
        Returns:
            list: List of dictionaries with scraped contact information
        """
        self.results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_url = {executor.submit(self.scrape_url, url): url for url in urls}
            
            completed = 0
            total = len(urls)
            
            for future in tqdm(concurrent.futures.as_completed(future_to_url), 
                              total=len(urls), 
                              desc="Scraping URLs"):
                result = future.result()
                self.results.append(result)
                completed += 1
                if progress_callback:
                    progress_callback(completed, total)
        
        return self.results

    def export_to_excel(self, filename='scraping_results.xlsx'):
        """
        Export scraping results to Excel file.
        
        Args:
            filename (str): Output filename
            
        Returns:
            str: Path to the saved file
        """
        try:
            # Check if we have any results
            if not self.results:
                logger.warning("No results to export")
                return None
                
            # Create DataFrame with all columns even if not all entries have them
            # Flatten nested lists to make them Excel-friendly
            processed_results = []
            
            for result in self.results:
                # Create a copy to avoid modifying the original
                processed_result = result.copy()
                
                # Convert lists to comma-separated strings
                for key in ['emails', 'phones', 'social_media']:
                    if key in processed_result and isinstance(processed_result[key], list):
                        processed_result[key] = ', '.join(processed_result[key])
                
                processed_results.append(processed_result)
            
            # Create DataFrame
            df = pd.DataFrame(processed_results)
            
            # Ensure all expected columns exist
            expected_columns = ['url', 'domain', 'emails', 'phones', 'social_media', 'status']
            for col in expected_columns:
                if col not in df.columns:
                    df[col] = ""
            
            # Reorder columns for better readability
            column_order = [col for col in expected_columns if col in df.columns]
            additional_columns = [col for col in df.columns if col not in expected_columns]
            final_column_order = column_order + additional_columns
            
            df = df[final_column_order]
            
            # Pandas 2.2.3 compatibility: Use default engine parameter
            df.to_excel(filename, index=False, sheet_name='Scraping Results')
            
            logger.info(f"Results exported to {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Failed to export results to Excel: {str(e)}")
            return None 