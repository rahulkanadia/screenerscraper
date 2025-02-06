import os
import requests
from tqdm import tqdm
import time
import random
import csv
import shutil

def save_html_content(url, html_folder_path, counter=None):
    response = requests.get(url)
    if response.status_code == 200:
        company_name = url.split("/company/")[1].split('/')[0]
        if counter:
            company_name += f"_{counter}"
        html_file_path = os.path.join(html_folder_path, f"{company_name}.html")
        with open(html_file_path, 'w', encoding='utf-8') as html_file:
            html_file.write(response.text)

def get_urls_from_file(file_path):
    if file_path.endswith('.txt'):
        with open(file_path, 'r') as file:
            urls = [line.strip() for line in file]
    elif file_path.endswith('.csv'):
        with open(file_path, 'r') as file:
            reader = csv.reader(file)
            next(reader)  # Skip header
            urls = [row[0] for row in reader]
    return urls

def handle_existing_folder(folder_path):
    choice = input(f"Folder '{folder_path}' already exists. Choose an option:\n"
                   "1. Empty the folder before proceeding\n"
                   "2. Replace existing files if any\n"
                   "3. Make a file with name change so both old and new files can exist\n"
                   "Enter your choice (1/2/3): ").strip()
    return choice

def empty_folder(folder_path):
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path) or os.path.islink(file_path):
            os.unlink(file_path)
        elif os.path.isdir(file_path):
            shutil.rmtree(file_path)

def main():
    file_path = input("Enter the path and file (txt/csv) containing URLs of HTML files to be pulled: ").strip()

    if not os.path.exists(file_path):
        print(f"File '{file_path}' does not exist.")
        return

    urls = get_urls_from_file(file_path)
    if not urls:
        print(f"No URLs found in '{file_path}'.")
        return

    folder_path = input("Enter the folder name for storage: ").strip()
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    else:
        choice = handle_existing_folder(folder_path)
        if choice == '1':
            empty_folder(folder_path)
        elif choice == '2':
            pass  # Do nothing, just proceed
        elif choice == '3':
            pass  # Do nothing, just proceed
        else:
            print("Invalid choice. Exiting.")
            return

    existing_files = set(os.listdir(folder_path)) if choice == '3' else set()

    # Saving HTML pages
    for idx, url in enumerate(tqdm(urls, desc='Saving HTML pages', unit='file')):
        counter = 1
        company_name = url.split("/company/")[1].split('/')[0]
        while f"{company_name}.html" in existing_files:
            counter += 1
            company_name = f"{url.split('/company/')[1].split('/')[0]}_{counter}"
        save_html_content(url, folder_path, counter if counter > 1 else None)
        if (idx + 1) % 4 == 0:
            time.sleep(random.uniform(2, 5))  # Random delay between 2 to 5 seconds after every 4 files

    print(f"All HTML pages have been saved to '{folder_path}'")

if __name__ == "__main__":
    main()
