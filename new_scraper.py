import os
import time
import logging
import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import psycopg2
from urllib.parse import urljoin, urlparse
import re
import faiss
import numpy as np
from langchain_openai import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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

# Streamlit interface
st.title("Web Scraper")

# Connect to PostgreSQL database
conn = psycopg2.connect(
    dbname='economics_crawler',
    user='root',
    password='arka1256',
    host='localhost'
)
cursor = conn.cursor()

# Create table if it does not exist
cursor.execute("""
    CREATE TABLE IF NOT EXISTS pages (
        id SERIAL PRIMARY KEY,
        url VARCHAR(2083) NOT NULL,
        name TEXT,
        price TEXT,
        content TEXT
    );
""")
conn.commit()

# Initialize WebDriver
driver = init_driver()

# Get URL input from user
start_url = st.text_input("Enter the starting URL:")

if st.button("Start Scraping"):
    if start_url:
        # Set of visited URLs to avoid duplicates
        visited_urls = set()
        urls_to_visit = {start_url}

        while urls_to_visit:
            current_url = urls_to_visit.pop()
            if current_url in visited_urls:
                continue

            logger.info(f"Visiting: {current_url}")
            driver.get(current_url)
            time.sleep(3)  # Allow time for the page to load

            soup = BeautifulSoup(driver.page_source, 'html.parser')

            # Extract important information
            page_content = ' '.join([p.get_text() for p in soup.find_all('p')])  # All text
            name = soup.find('h1').get_text() if soup.find('h1') else ''
            price = soup.find('span', class_='price').get_text() if soup.find('span', class_='price') else ''

            # Combine extracted info for storage
            combined_content = f"Name: {name}\nPrice: {price}\nContent: {page_content}"

            # Store the combined content in the database
            sql_insert = """
                INSERT INTO pages (url, name, price, content)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(sql_insert, (current_url, name, price, combined_content))
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
        st.success("Finished crawling and storing pages.")
    else:
        st.error("Please enter a valid URL.")

# Display all rows from the table
if st.button("Show Stored Data"):
    conn = psycopg2.connect(
        dbname='economics_crawler',
        user='root',
        password='arka1256',
        host='localhost'
    )
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pages;")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    if rows:
        for row in rows:
            st.write(f"ID: {row[0]}")
            st.write(f"URL: {row[1]}")
            st.write(f"Name: {row[2]}")
            st.write(f"Price: {row[3]}")
            st.write(f"Content: {row[4]}")
            st.write("---")
    else:
        st.info("No data found in the database.")

# Function to get text data from the database
def get_text_data():
    conn = psycopg2.connect(
        dbname='economics_crawler',
        user='root',
        password='arka1256',
        host='localhost'
    )
    cursor = conn.cursor()
    cursor.execute("SELECT content FROM pages;")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [Document(page_content=row[0], metadata={}) for row in rows]

# Function to create FAISS index and store embeddings
def create_faiss_index(texts):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    split_texts = text_splitter.split_documents(texts)

    openai_api_key = os.getenv('OPENAI_API_KEY')
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set.")

    embedding_model = OpenAIEmbeddings(api_key=openai_api_key)
    embeddings = [embedding_model.embed_query(doc.page_content) for doc in split_texts]

    # Convert embeddings list to a NumPy array
    embeddings_np = np.array(embeddings)

    dimension = embeddings_np.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings_np)

    return index, embedding_model, split_texts

# Load data and create FAISS index
texts = get_text_data()
if texts:
    index, embedding_model, split_texts = create_faiss_index(texts)

# Function to perform similarity search and generate answer
def get_answer(question, index, embedding_model, split_texts):
    question_embedding = embedding_model.embed_query(question)
    question_embedding_np = np.array([question_embedding])  # Convert to NumPy array
    D, I = index.search(question_embedding_np, k=1)
    return split_texts[I[0][0]].page_content

# Get user question and display answer
question = st.text_input("Ask a question:")

if st.button("Get Answer"):
    if question:
        answer = get_answer(question, index, embedding_model, split_texts)
        st.write(f"Answer: {answer}")
    else:
        st.error("Please enter a question.")
