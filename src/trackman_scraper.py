#!/usr/bin/env python3
"""
Trackman Data Scraper

This script extracts golf shot data from Trackman reports.
"""

import json
import os
import re
import time
from urllib.parse import parse_qs, urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup


def extract_urls_from_file(file_path):
    """Extract URLs from a text file."""
    with open(file_path, "r") as f:
        content = f.read()

    # Extract URLs using regex
    url_pattern = r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
    urls = re.findall(url_pattern, content)
    return urls


def follow_redirect(url):
    """Follow URL redirects to get the final destination URL."""
    try:
        response = requests.get(url, allow_redirects=True)
        return response.url, response
    except Exception as e:
        print(f"Error following redirect for {url}: {e}")
        return None, None


def extract_report_id(url):
    """Extract the ReportId from a Trackman URL."""
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    return query_params.get("ReportId", [None])[0]


def analyze_page_content(response):
    """Analyze the page content to identify data sources."""
    if not response or response.status_code != 200:
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    # Look for JavaScript data objects
    scripts = soup.find_all("script")
    data_objects = []

    for script in scripts:
        script_content = script.string
        if script_content and "var data" in script_content:
            print("Found potential data script!")
            data_objects.append(script_content)

    # Look for API calls in the JavaScript
    api_endpoints = []
    for script in scripts:
        script_content = script.string
        if script_content:
            # Look for URLs that might be API endpoints
            api_pattern = r'https?://[^"\']+api[^"\']+'
            apis = re.findall(api_pattern, script_content)
            api_endpoints.extend(apis)

    # Look for network requests to API endpoints
    api_url = f"https://web-dynamic-reports-api.trackmangolf.com/api/report"

    try:
        # Try to directly access the API with the report ID
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "application/json",
            "Referer": response.url,
        }

        report_id = extract_report_id(response.url)
        if report_id:
            api_response = requests.get(f"{api_url}/{report_id}", headers=headers)
            if api_response.status_code == 200:
                print(f"Successfully accessed API endpoint: {api_url}/{report_id}")
                return {
                    "data_objects": data_objects,
                    "api_endpoints": api_endpoints,
                    "api_data": api_response.json(),
                }
    except Exception as e:
        print(f"Error accessing API: {e}")

    return {"data_objects": data_objects, "api_endpoints": api_endpoints}


def extract_shot_data(api_data):
    """Extract shot data from the API response."""
    if not api_data:
        return None

    shots = []
    try:
        # Extract shot data based on the API response structure
        # This will need to be adjusted based on the actual structure
        if "shots" in api_data:
            shots = api_data["shots"]
        elif "data" in api_data and "shots" in api_data["data"]:
            shots = api_data["data"]["shots"]

        # Convert to DataFrame for easier analysis
        if shots:
            df = pd.DataFrame(shots)
            return df
    except Exception as e:
        print(f"Error extracting shot data: {e}")

    return None


def main():
    # Extract URLs from the file
    urls = extract_urls_from_file("urls to scrape for trackman data.txt")

    results = []
    shot_data_frames = []

    for url in urls:
        print(f"Processing URL: {url}")
        final_url, response = follow_redirect(url)

        if not final_url:
            continue

        report_id = extract_report_id(final_url)
        print(f"Report ID: {report_id}")
        print(f"Final URL: {final_url}")

        # Analyze the page content
        analysis = analyze_page_content(response)

        # Extract shot data if available
        shot_data = None
        if analysis and "api_data" in analysis:
            shot_data = extract_shot_data(analysis["api_data"])
            if isinstance(shot_data, pd.DataFrame):
                shot_data_frames.append(shot_data)

        results.append(
            {
                "original_url": url,
                "final_url": final_url,
                "report_id": report_id,
                "analysis": analysis,
                "has_shot_data": shot_data is not None,
            }
        )

    # Save the results for further analysis
    with open("trackman_analysis_results.json", "w") as f:
        json.dump(results, f, indent=2)

    # Combine all shot data if available
    if shot_data_frames:
        combined_data = pd.concat(shot_data_frames, ignore_index=True)
        combined_data.to_csv("combined_shot_data.csv", index=False)
        print(f"Combined shot data saved to combined_shot_data.csv")

    print("\nAnalysis complete. Results saved to trackman_analysis_results.json")


if __name__ == "__main__":
    main()
