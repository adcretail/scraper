import pymysql
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup, Tag
from webdriver_manager.chrome import ChromeDriverManager

# Function to initialize the Selenium WebDriver
def init_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # Run headless Chrome
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

# Function to connect to the MySQL database
def connect_db(host, user, password, db):
    connection = pymysql.connect(
        host=host,
        user=user,
        password=password,
        db=db,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    return connection

# Function to create the table to store Wikipedia page data
def create_table(connection):
    create_table_query = """
    CREATE TABLE IF NOT EXISTS pages (
        id INT AUTO_INCREMENT PRIMARY KEY,
        page_title VARCHAR(255),
        section_title VARCHAR(255),
        text TEXT
    );
    """
    with connection.cursor() as cursor:
        cursor.execute(create_table_query)
    connection.commit()

# Function to scrape the Wikipedia page and store the content in the database
def scrape_wikipedia_page(url, driver, connection):
    driver.get(url)
    html = driver.page_source
    soup = BeautifulSoup(html, 'lxml')

    # Find the title of the page
    title = soup.find("h1", {"id": "firstHeading"}).text.strip()

    # Find all headers that denote sections on the page (assuming they are h2, h3, and h4 tags)
    headers = soup.find_all(['h2', 'h3', 'h4'])
    
    for header in headers:
        # Initialize an empty string to store section text
        section_title = header.get_text(separator=' ', strip=True).replace("[edit]", "").strip()
        text = ''

        # Get all elements between current header and the next one
        next_node = header
        while True:
            next_node = next_node.find_next_sibling()
            if next_node is None or (isinstance(next_node, Tag) and next_node.name in ['h2', 'h3', 'h4']):
                break
            if isinstance(next_node, Tag) and next_node.name in ['p', 'ul', 'ol', 'dl', 'blockquote']:
                text += next_node.get_text(separator=' ', strip=True) + '\n'
        
        if text.strip():
            # Insert the data into the table (page title, section title, and its text)
            insert_data_query = "INSERT INTO pages (page_title, section_title, text) VALUES (%s, %s, %s)"
            with connection.cursor() as cursor:
                cursor.execute(insert_data_query, (title, section_title, text.strip()))
            connection.commit()

# Main function
def main():
    url = input("Enter the URL of the Wikipedia page you want to scrape: ")

    # Database credentials
    db_host = 'localhost'
    db_user = 'root'
    db_password = 'arka@1256'
    db_name = 'wikipedia'

    driver = init_driver()
    connection = connect_db(db_host, db_user, db_password, db_name)

    try:
        create_table(connection)
        scrape_wikipedia_page(url, driver, connection)
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        driver.quit()
        connection.close()

if __name__ == "__main__":
    main()
