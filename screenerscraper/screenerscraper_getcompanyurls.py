import requests
from bs4 import BeautifulSoup
import time
import random
import os
import csv

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

def get_total_pages(base_url):
    response = requests.get(base_url, headers=HEADERS)
    if response.status_code != 200: return 1
    soup = BeautifulSoup(response.content, 'html.parser')
    pagination = soup.find('div', class_='pagination')
    if pagination:
        total_pages = [int(a.text) for a in pagination.find_all('a') if a.text.isdigit()]
        return max(total_pages) if total_pages else 1
    return 1

def get_company_urls_from_page(url):
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 429:
        time.sleep(random.uniform(3, 5))
        response = requests.get(url, headers=HEADERS)
    if response.status_code != 200: return []
    soup = BeautifulSoup(response.content, 'html.parser')
    return [f"https://www.screener.in{a['href']}" for a in soup.find_all('a', href=True) if a['href'].startswith("/company/")]

def run_url_scraper(screener_url, max_pages_input, file_format, folder_path):
    print("\n--- Starting URL Scraper ---")
    if screener_url.startswith("http"): base_url = screener_url
    elif screener_url.startswith("screener.in"): base_url = "https://" + screener_url
    else: base_url = "https://screener.in/screens/" + screener_url

    if "?page=" in base_url: base_url = base_url.split("?page=")[0]
    if not base_url.endswith("/"): base_url += "/"
    base_url_with_page = base_url + "?page="

    total_pages = get_total_pages(base_url_with_page + "1")
    try:
        max_pages = int(max_pages_input) if max_pages_input else total_pages
        max_pages = min(max_pages, total_pages)
    except ValueError: max_pages = total_pages

    os.makedirs(folder_path, exist_ok=True)
    file_name = base_url.strip('/').split('/')[-1] + ('.txt' if file_format == 'txt' else '.csv')
    output_file_path = os.path.join(folder_path, file_name)

    all_urls = []
    for page in range(1, max_pages + 1):
        print(f"Processing page {page}/{max_pages}...")
        urls = get_company_urls_from_page(base_url_with_page + str(page))
        all_urls.extend(urls)
        time.sleep(random.uniform(3, 5))

    if file_format == 'txt':
        with open(output_file_path, 'w') as file:
            for url in all_urls: file.write(f"{url}\n")
    else:
        with open(output_file_path, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['URL'])
            for url in all_urls: writer.writerow([url])
            
    print(f"Collected {len(all_urls)} URLs. Saved to '{output_file_path}'")