import os

# Define the paths
html_dir = r'\company_html'
reference_file = r'\company_links.txt'
output_file = r'\company_links_status.txt'

# Read the company links and create a set of expected company names
expected_companies = {}
with open(reference_file, 'r') as file:
    for line in file:
        company_url = line.strip()
        # Remove 'https://www.screener.in/company/' and everything after and including the '/' after the company name
        company_name = company_url.replace('https://www.screener.in/company/', '').split('/')[0].replace('/', '_')
        expected_companies[company_name] = company_url

# Get the list of HTML files in the directory
available_files = set(f.replace('.html', '') for f in os.listdir(html_dir) if f.endswith('.html'))

# Initialize counters
downloaded_count = 0
pending_count = 0

# Compare and mark as downloaded or pending
with open(output_file, 'w') as status_file:
    for company_name, company_url in expected_companies.items():
        if company_name in available_files:
            status_file.write(f"{company_url} - Downloaded\n")
            downloaded_count += 1
        else:
            status_file.write(f"{company_url} - Pending\n")
            pending_count += 1

# Print the tally of totals
print('Comparison completed and statuses have been recorded.')
print(f'Total Downloaded: {downloaded_count}')
print(f'Total Pending: {pending_count}')
