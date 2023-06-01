from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import json
import openai
from dotenv import dotenv_values
import sys

def configure_driver():
    print("configuring driver...")
    # Configure Selenium options
    options = Options()
    options.add_argument("--headless")  # Run Chrome in headless mode
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    # Create a new instance of the Chrome driver
    return webdriver.Chrome(options=options)

def scrape_web_page(url):
    driver = configure_driver()
    print("scraping web page...", url)
    # Load the page with Selenium
    driver.get(url)
    # Wait for the page to fully load
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "breadCrumb")))
    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    # Close the Selenium browser
    driver.quit()
    print("scraping complete...")
    return soup

def extract_product_details(soup):
    print("extracting product details...")
    product_details = {} # initialize a dictionary to store product details

    # Extract All Specifications
    global specifications
    specifications = {}
    specifications_list = soup.find_all('div', class_='pdp-feature-spec-heading')
    for specification in specifications_list:
        key = specification.text.strip().split(":")[0]
        value = specification.find_next_sibling('div').text.strip()
        specifications[key] = value

    # Extract details and store them in the dictionary
    product_details["Vendor Part Number"] = specifications["Vendor Part Number"]
    
    # Brand
    product_details["Brand"] = specifications["Brand"]

    # Part Name
    product_details["Part Name"] = soup.find('div', class_='product-name').text.strip()

    # Categories
    category_element = soup.find('div', class_='breadCrumb')

    if category_element:
        category_span = category_element.find_all('span', class_='links')
        if len(category_span) > 1:
            product_details["Top Level Category"] = category_span[1].text.strip()
        else:
            print("Category not found")
    else:
        print("Category element not found")

    categories = specifications["Parts Classification"].split(">>")
    product_details["Major Category"] = categories[1]
    product_details["Minor Category"] = categories[2]
    product_details["Sub-minor Category"] = categories[3]

    # URL
    product_details["URL"] = url

    # Description
    product_details["Description"] = soup.find('div', class_='pdp-long-description').text.strip()

    print("extracting product details complete...")
    return product_details

def generate(data, temperature=1, max_tokens=1000):
    print("generating with openai...")
    # Your OpenAI API key
    openai.api_key = dotenv_values()["OPENAI_API_KEY"]

    # Generate the product description using the OpenAI API
    response = openai.Completion.create(
        engine='text-davinci-003',
        prompt=data,
        max_tokens=max_tokens,
        temperature=temperature,
        n=1,
        stop=None,
    )

    generated_description = response.choices[0].text.strip()

    print("generation with openai complete...")
    return generated_description

def main(url):
    # Scrape the web page
    soup = scrape_web_page(url)

    # Extract product details
    product_details = extract_product_details(soup)

    # Prepare Openai Payload
    opanai_payload = product_details
    del opanai_payload["URL"]
    print("OpenAI Payload: ", json.dumps(opanai_payload, indent=4))

    # Generate description and name
    generated_description = generate(str(opanai_payload))
    print("Generated Description: ", generated_description)
    generated_name = generate(str(opanai_payload), 0.7, 5)
    print("Generated Name: ", generated_name)

    product_details["Part Name"] = {
        "current": product_details["Part Name"],
        "generated": generated_name
    }

    product_details["Description"] = {
        "current": product_details["Description"],
        "generated": generated_description
    }

    product_details["Specifications"] = specifications
    # Convert the product details to JSON
    json_data = json.dumps(product_details, indent=4)
    # Print the JSON data
    print("\n\n\nOUTPUT:", json_data)

# Run the script
if __name__ == "__main__":
    # Hardcoded URL to use if no argument is provided
    default_url = "https://shop.cccparts.com/p/eaton-yoke-20624/hf20624/"
    # Use the command-line argument if provided, otherwise use the hardcoded URL
    url = sys.argv[1] if len(sys.argv) > 1 else default_url
    main(url)
