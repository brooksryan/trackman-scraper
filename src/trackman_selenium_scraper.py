#!/usr/bin/env python3
"""
Trackman Data Scraper using Selenium

This script extracts golf shot data from Trackman reports using Selenium to capture
network requests and dynamic content.
"""

import json
import os
import re
import time
from urllib.parse import parse_qs, urlparse

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


def extract_urls_from_file(file_path):
    """Extract URLs from a text file."""
    with open(file_path, "r") as f:
        content = f.read()

    # Extract URLs using regex
    url_pattern = r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
    urls = re.findall(url_pattern, content)
    return urls


def follow_redirect(url, driver):
    """Follow URL redirects using Selenium."""
    try:
        driver.get(url)
        # Wait for the page to load
        time.sleep(5)
        return driver.current_url
    except Exception as e:
        print(f"Error following redirect for {url}: {e}")
        return None


def extract_report_id(url):
    """Extract the ReportId from a Trackman URL."""
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    return query_params.get("ReportId", [None])[0]


def capture_network_requests(driver, url):
    """Capture network requests and look for API calls."""
    # Navigate to the URL
    driver.get(url)

    # Wait for the page to load completely
    time.sleep(10)

    # Execute JavaScript to get the network requests
    logs = driver.execute_script(
        """
    var performance = window.performance || window.mozPerformance || window.msPerformance || window.webkitPerformance || {};
    var network = performance.getEntries() || [];
    return network;
    """
    )

    # Filter for API requests
    api_requests = [log for log in logs if "api" in log.get("name", "").lower()]

    return api_requests


def extract_data_from_page(driver):
    """Extract data directly from the page using JavaScript."""
    try:
        # Wait for the data to be loaded into the page
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".report-container"))
        )

        # Try to extract data from various potential sources
        data_sources = [
            # Try to get data from window objects
            "return window.reportData || null;",
            "return window.data || null;",
            "return window.shotData || null;",
            # Try to find data in localStorage
            "return JSON.parse(localStorage.getItem('reportData')) || null;",
            # Look for data in specific DOM elements
            "return JSON.parse(document.querySelector('[data-report]')?.getAttribute('data-report')) || null;",
        ]

        for script in data_sources:
            try:
                data = driver.execute_script(script)
                if data:
                    print(f"Found data using script: {script}")
                    return data
            except Exception as e:
                print(f"Error executing script {script}: {e}")

        # If we couldn't find data in predefined locations, try to extract it from the DOM
        print("Trying to extract data from DOM elements...")

        # Look for tables with shot data
        tables = driver.find_elements(By.CSS_SELECTOR, "table")
        if tables:
            print(f"Found {len(tables)} tables on the page")
            table_data = []
            for i, table in enumerate(tables):
                try:
                    headers = [
                        th.text for th in table.find_elements(By.CSS_SELECTOR, "th")
                    ]
                    rows = []
                    for tr in table.find_elements(By.CSS_SELECTOR, "tbody tr"):
                        row = [
                            td.text for td in tr.find_elements(By.CSS_SELECTOR, "td")
                        ]
                        if row:
                            rows.append(dict(zip(headers, row)))
                    if rows:
                        table_data.append({"table_index": i, "data": rows})
                except Exception as e:
                    print(f"Error extracting data from table {i}: {e}")

            if table_data:
                return {"tables": table_data}

        # Look for shot data in divs or spans
        shot_elements = driver.find_elements(
            By.CSS_SELECTOR, ".shot-data, [data-shot], .shot"
        )
        if shot_elements:
            print(f"Found {len(shot_elements)} shot elements")
            shot_data = []
            for elem in shot_elements:
                try:
                    shot_data.append(
                        {
                            "text": elem.text,
                            "html": elem.get_attribute("innerHTML"),
                            "attributes": {
                                attr: elem.get_attribute(attr)
                                for attr in ["data-shot", "data-id", "data-index"]
                            },
                        }
                    )
                except Exception as e:
                    print(f"Error extracting shot element data: {e}")

            if shot_data:
                return {"shot_elements": shot_data}

        # If all else fails, get the page source for manual analysis
        return {"page_source": driver.page_source}

    except Exception as e:
        print(f"Error extracting data from page: {e}")
        return None


def process_extracted_data(data):
    """Process the extracted data into a structured format."""
    if not data:
        return None

    # If we have table data, convert it to a DataFrame
    if "tables" in data:
        all_rows = []
        for table in data["tables"]:
            all_rows.extend(table["data"])

        if all_rows:
            return pd.DataFrame(all_rows)

    # If we have shot elements, try to extract structured data
    if "shot_elements" in data:
        # This would need to be customized based on the actual structure
        # For now, just return the raw data
        return data["shot_elements"]

    # If we have raw JSON data
    if isinstance(data, dict) and ("shots" in data or "data" in data):
        shots = data.get("shots", [])
        if not shots and "data" in data:
            shots = data["data"].get("shots", [])

        if shots:
            return pd.DataFrame(shots)

    return data


def main():
    # Set up Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")

    # Initialize the Chrome driver
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=chrome_options
    )

    try:
        # Extract URLs from the file
        urls = extract_urls_from_file("urls to scrape for trackman data.txt")

        results = []
        all_data = []

        for url in urls:
            print(f"\nProcessing URL: {url}")

            # Follow redirects
            final_url = follow_redirect(url, driver)
            if not final_url:
                continue

            report_id = extract_report_id(final_url)
            print(f"Report ID: {report_id}")
            print(f"Final URL: {final_url}")

            # Capture network requests
            api_requests = capture_network_requests(driver, final_url)
            print(f"Found {len(api_requests)} network requests")

            # Extract data from the page
            extracted_data = extract_data_from_page(driver)

            # Process the extracted data
            processed_data = process_extracted_data(extracted_data)

            if isinstance(processed_data, pd.DataFrame):
                all_data.append(processed_data)
                print(f"Successfully extracted data with {len(processed_data)} rows")

            # Save the results
            results.append(
                {
                    "original_url": url,
                    "final_url": final_url,
                    "report_id": report_id,
                    "api_requests": api_requests,
                    "has_extracted_data": extracted_data is not None,
                    "has_processed_data": processed_data is not None,
                }
            )

        # Save the results for further analysis
        with open("trackman_selenium_results.json", "w") as f:
            # Convert non-serializable objects to strings
            serializable_results = []
            for result in results:
                serializable_result = result.copy()
                if "api_requests" in serializable_result:
                    serializable_result["api_requests"] = str(
                        serializable_result["api_requests"]
                    )
                serializable_results.append(serializable_result)

            json.dump(serializable_results, f, indent=2)

        # Combine all data if available
        if all_data:
            combined_data = pd.concat(all_data, ignore_index=True)
            combined_data.to_csv("combined_shot_data.csv", index=False)
            print(f"\nCombined shot data saved to combined_shot_data.csv")

        print("\nAnalysis complete. Results saved to trackman_selenium_results.json")

    finally:
        # Close the browser
        driver.quit()


if __name__ == "__main__":
    main()
