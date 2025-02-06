import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
import time
import random
import os
import csv

def get_total_pages(base_url):
    response = requests.get(base_url)
    if response.status_code != 200:
        raise Exception(f"Failed to retrieve data from {base_url}. Status code: {response.status_code}")
    soup = BeautifulSoup(response.content, 'html.parser')
    pagination = soup.find('div', class_='pagination')
    if pagination:
        total_pages = [int(a.text) for a in pagination.find_all('a') if a.text.isdigit()]
        return max(total_pages) if total_pages else 1
    return 1

def get_company_urls_from_page(url):
    response = requests.get(url)
    if response.status_code != 200:
        if response.status_code == 429:
            print(f"Too many requests to {url}. Retrying after a short delay...")
            time.sleep(random.uniform(3, 5))  # Wait for 3 to 5 seconds before retrying
            response = requests.get(url)
            if response.status_code != 200:
                raise Exception(f"Failed to retrieve data from {url}. Status code: {response.status_code}")
        else:
            raise Exception(f"Failed to retrieve data from {url}. Status code: {response.status_code}")
    soup = BeautifulSoup(response.content, 'html.parser')
    urls = [f"https://www.screener.in{a['href']}" for a in soup.find_all('a', href=True) if a['href'].startswith("/company/")]
    return urls

def save_urls_to_file(urls, file_path, file_format):
    if file_format == 'txt':
        with open(file_path, 'w') as file:
            for url in urls:
                file.write(f"{url}\n")
    elif file_format == 'csv':
        with open(file_path, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['URL'])
            for url in urls:
                writer.writerow([url])

def main():
    screener_url = input("Enter the screener URL: ").strip()

    # Form the base URL
    if screener_url.startswith("http://") or screener_url.startswith("https://"):
        base_url = screener_url
    elif screener_url.startswith("screener.in"):
        base_url = "https://" + screener_url
    else:
        base_url = "https://screener.in/screens/" + screener_url

    # Adjust base URL if needed
    if "?page=" in base_url:
        base_url = base_url.split("?page=")[0]
    if not base_url.endswith("/"):
        base_url = base_url + "/"

    base_url_with_page = base_url + "?page="

    print(f"Base URL: {base_url_with_page}1")

    total_pages = get_total_pages(base_url_with_page + "1")
    print(f"Total pages found: {total_pages}")

    if total_pages == 0:
        print("No pages found.")
        return
    elif total_pages == 1:
        print("Only one page found.")
        max_pages = 1
    else:
        max_pages = int(input(f"Enter the number of pages to go through (1-{total_pages}): "))

    file_format = input("Enter the file format to store URLs (txt/csv): ").strip().lower()
    if file_format not in ['txt', 'csv']:
        print("Invalid file format. Please enter 'txt' or 'csv'.")
        return

    folder_path = input("Enter the folder name for storage: ").strip()
    os.makedirs(folder_path, exist_ok=True)

    # Generate the file name based on the base URL's title
    file_name = base_url.strip('/').split('/')[-1] + ('.txt' if file_format == 'txt' else '.csv')
    output_file_path = os.path.join(folder_path, file_name)

    all_urls = []
    for page in tqdm(range(1, max_pages + 1), desc='Processing pages', unit='page'):
        page_url = base_url_with_page + str(page)
        urls = get_company_urls_from_page(page_url)
        all_urls.extend(urls)
        tqdm.write(f"Collected {len(urls)} URLs from page {page}")
        time.sleep(random.uniform(3, 5))  # Random delay between 3 to 5 seconds

    if all_urls:
        save_urls_to_file(all_urls, output_file_path, file_format)
        print(f"All URLs have been saved to '{output_file_path}'")
    else:
        print("No URLs collected.")

if __name__ == "__main__":
    main()
