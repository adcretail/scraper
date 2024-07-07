import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pymysql
from urllib.parse import urljoin, urlparse
import re

# Function to initialize the Selenium WebDriver
def init_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # Run headless Chrome
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

# Function to get all links on a page
def get_all_links(soup, base_url):
    links = set()
    for link in soup.find_all('a', href=True):
        url = urljoin(base_url, link['href'])
        if is_valid_url(url, base_url):
            links.add(url)
    return links

# Function to check if a URL is valid and belongs to the same website
def is_valid_url(url, base_url):
    parsed_url = urlparse(url)
    parsed_base = urlparse(base_url)
    return (parsed_url.scheme in ('http', 'https') and
            parsed_url.netloc == parsed_base.netloc and
            re.match(r'^https?://', url))

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Connect to MySQL database
conn = pymysql.connect(
    host='localhost',
    user='root',
    password='arka@1256',
    db='web_crawler'
)
cursor = conn.cursor()

# Create database and table if they do not exist
cursor.execute("CREATE DATABASE IF NOT EXISTS web_crawler;")
cursor.execute("USE web_crawler;")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS pages (
        id INT AUTO_INCREMENT PRIMARY KEY,
        url VARCHAR(2083) NOT NULL,
        content TEXT NOT NULL,
        chunk_order INT NOT NULL
    );
""")
conn.commit()

# Initialize WebDriver
driver = init_driver()

# Ask user for the starting URL
start_url = input("Enter the starting URL: ")

# Set of visited URLs to avoid duplicates
visited_urls = set()
urls_to_visit = {start_url}

# Function to split content into chunks
def split_content(content, chunk_size=10000):
    return [content[i:i + chunk_size] for i in range(0, len(content), chunk_size)]

while urls_to_visit:
    current_url = urls_to_visit.pop()
    if current_url in visited_urls:
        continue

    logger.info(f"Visiting: {current_url}")
    driver.get(current_url)
    time.sleep(3)  # Allow time for the page to load

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    page_content = str(soup)

    # Split the content into chunks
    content_chunks = split_content(page_content)
    
    # Store page content chunks in the database
    for order, chunk in enumerate(content_chunks):
        sql = "INSERT INTO pages (url, content, chunk_order) VALUES (%s, %s, %s)"
        values = (current_url, chunk, order)
        cursor.execute(sql, values)
    conn.commit()

    # Get all links on the current page
    links = get_all_links(soup, current_url)
    urls_to_visit.update(links)

    visited_urls.add(current_url)

# Close connections
cursor.close()
conn.close()
driver.quit()
logger.info("Finished crawling and storing pages.")
