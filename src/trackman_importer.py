#!/usr/bin/env python3
"""
Trackman Data Importer

This script provides a simple interface for adding new Trackman report URLs
and importing the data.
"""

import json
import os
import re
import sys
from datetime import datetime
from urllib.parse import parse_qs, urlparse

import pandas as pd

# Add the src directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.trackman_api_scraper import (
    extract_combine_shot_data,
    extract_combine_shot_groups,
    extract_report_id,
    extract_shot_data,
    extract_shot_groups,
    fetch_report_data,
    follow_redirect,
    is_combine_report,
)

# Constants
DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"
)
RAW_DIR = os.path.join(DATA_DIR, "raw")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
URL_FILE = os.path.join(DATA_DIR, "trackman_urls.txt")
MULTI_URL_FILE = os.path.join(DATA_DIR, "multi_shot_group_urls.txt")
COMBINE_URL_FILE = os.path.join(DATA_DIR, "combine_urls.txt")

# Regular shot data files
COMBINED_SHOTS = os.path.join(PROCESSED_DIR, "combined_shot_data.csv")
COMBINED_GROUPS = os.path.join(PROCESSED_DIR, "combined_shot_groups.csv")

# Combine-specific data files
COMBINE_SHOTS = os.path.join(PROCESSED_DIR, "combine_combined_shot_data.csv")
COMBINE_GROUPS = os.path.join(PROCESSED_DIR, "combine_combined_shot_groups.csv")


def ensure_directories():
    """Ensure all necessary directories exist."""
    os.makedirs(RAW_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    # Create URL file if it doesn't exist
    if not os.path.exists(URL_FILE):
        with open(URL_FILE, "w") as f:
            f.write("# Trackman Report URLs\n")
            f.write("# Format: URL,ImportDate,Status\n")


def extract_urls_from_text(text):
    """Extract URLs from text."""
    url_pattern = r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
    return re.findall(url_pattern, text)


def get_existing_urls():
    """Get list of URLs that have already been processed."""
    if not os.path.exists(URL_FILE):
        return []

    with open(URL_FILE, "r") as f:
        lines = f.readlines()

    urls = []
    for line in lines:
        if line.startswith("#") or not line.strip():
            continue
        parts = line.strip().split(",")
        if len(parts) >= 1:
            urls.append(parts[0])

    return urls


def add_url_to_file(url, status="Pending"):
    """Add a URL to the URL file."""
    with open(URL_FILE, "a") as f:
        f.write(f"{url},{datetime.now().isoformat()},{status}\n")


def update_url_status(url, status):
    """Update the status of a URL in the URL file."""
    if not os.path.exists(URL_FILE):
        return

    with open(URL_FILE, "r") as f:
        lines = f.readlines()

    with open(URL_FILE, "w") as f:
        for line in lines:
            if line.startswith("#") or not line.strip():
                f.write(line)
                continue

            parts = line.strip().split(",")
            if len(parts) >= 1 and parts[0] == url:
                f.write(f"{url},{datetime.now().isoformat()},{status}\n")
            else:
                f.write(line)


def extract_shot_groups_from_url(url):
    """Extract shot group IDs from a URL."""
    shot_groups = []

    # Look for sgos[] parameters in the URL
    if "sgos%5B%5D=" in url:
        parts = url.split("sgos%5B%5D=")
        # Skip the first part (before the first sgos parameter)
        for i in range(1, len(parts)):
            # Extract the shot group ID up to the next & or end of string
            sg_id = parts[i].split("&")[0]
            if sg_id:
                shot_groups.append(sg_id)

    return shot_groups


def add_multi_shot_group_url():
    """Add a URL with multiple shot groups and process it efficiently."""
    print("For long URLs, you can paste the URL in multiple parts.")
    print(
        "Enter each part of the URL and press Enter. Type 'DONE' on a new line when finished."
    )

    url_parts = []
    while True:
        part = input("URL part (or 'DONE' to finish): ").strip()
        if part.upper() == "DONE":
            break
        url_parts.append(part)

    url = "".join(url_parts).strip()

    if not url:
        print("No URL entered. Aborting.")
        return

    # Check if URL is valid
    if not url.startswith("http"):
        print("Invalid URL. Must start with http:// or https://")
        return

    # Extract the report ID and shot groups
    final_url, _ = follow_redirect(url)
    if not final_url:
        print(f"Error: Could not follow redirect for {url}")
        return

    report_id = extract_report_id(final_url)
    if not report_id:
        print(f"Error: Could not extract report ID from {final_url}")
        return

    print(f"Report ID: {report_id}")

    # Extract shot groups from the URL
    shot_groups = extract_shot_groups_from_url(url)
    print(f"Found {len(shot_groups)} shot groups in the URL")

    # Check if URL already exists
    existing_urls = get_existing_urls()
    if url in existing_urls:
        print(f"URL already exists in the database.")
        process_anyway = input("Process anyway? (y/n): ").strip().lower()
        if process_anyway != "y":
            return

    # Add URL to file
    add_url_to_file(url)

    # Process in batches if there are many shot groups
    if len(shot_groups) > 10:
        print(f"Processing {len(shot_groups)} shot groups in batches...")

        # First, get the base report data
        base_url = f"https://web-dynamic-reports.trackmangolf.com/?r={report_id}"
        process_url(base_url, track_url=False)

        # Then process each shot group separately or in small batches
        batch_size = 5
        for i in range(0, len(shot_groups), batch_size):
            batch = shot_groups[i : i + batch_size]
            batch_url = f"https://web-dynamic-reports.trackmangolf.com/?r={report_id}"
            for sg in batch:
                batch_url += f"&sgos%5B%5D={sg}"

            print(
                f"Processing batch {i//batch_size + 1} of {(len(shot_groups) + batch_size - 1)//batch_size}..."
            )
            process_url(batch_url, track_url=False)

        # Update the status of the original URL
        update_url_status(url, "Success")
        print("All shot groups processed successfully")
    else:
        # Process normally if not too many shot groups
        process_url(url)

    # Update combined data
    update_combined_data()


def process_url(url, track_url=True):
    """Process a single URL and extract the data."""
    print(f"Processing URL: {url}")

    # Follow redirects to get the final URL
    final_url, _ = follow_redirect(url)
    if not final_url:
        print(f"Error: Could not follow redirect for {url}")
        if track_url:
            update_url_status(url, "Error: Redirect failed")
        return False

    # Extract the report ID
    report_id = extract_report_id(final_url)
    if not report_id:
        print(f"Error: Could not extract report ID from {final_url}")
        if track_url:
            update_url_status(url, "Error: No report ID")
        return False

    print(f"Report ID: {report_id}")

    # Check if we've already processed this report
    raw_file = os.path.join(RAW_DIR, f"report_data_{report_id}.json")
    if os.path.exists(raw_file):
        print(f"Report {report_id} already exists. Appending new data if available.")

    # Fetch report data
    report_data = fetch_report_data(report_id)
    if not report_data:
        print(f"Error: Could not fetch report data for {report_id}")
        if track_url:
            update_url_status(url, "Error: API fetch failed")
        return False

    # Save the raw report data
    with open(raw_file, "w") as f:
        json.dump(report_data, f, indent=2)

    print(f"Saved raw report data to {raw_file}")

    # Extract shot data
    shot_data = extract_shot_data(report_data)
    if isinstance(shot_data, pd.DataFrame):
        # Add report_id to the shot data for tracking
        shot_data["report_id"] = report_id

        # Save the shot data
        shot_file = os.path.join(PROCESSED_DIR, f"shot_data_{report_id}.csv")
        shot_data.to_csv(shot_file, index=False)
        print(f"Extracted {len(shot_data)} shots and saved to {shot_file}")

    # Extract shot groups
    shot_groups = extract_shot_groups(report_data)
    if isinstance(shot_groups, pd.DataFrame):
        # Add report_id to the shot groups for tracking
        shot_groups["report_id"] = report_id

        # Save the shot groups
        groups_file = os.path.join(PROCESSED_DIR, f"shot_groups_{report_id}.csv")
        shot_groups.to_csv(groups_file, index=False)
        print(f"Extracted {len(shot_groups)} shot groups and saved to {groups_file}")

    # Update combined data files
    update_combined_data()

    if track_url:
        update_url_status(url, "Success")
    return True


def update_combined_data():
    """Update the combined data files with all processed data."""
    # Get all shot data files
    shot_files = [
        f
        for f in os.listdir(PROCESSED_DIR)
        if f.startswith("shot_data_") and f.endswith(".csv")
    ]
    group_files = [
        f
        for f in os.listdir(PROCESSED_DIR)
        if f.startswith("shot_groups_") and f.endswith(".csv")
    ]

    print(
        f"Found {len(shot_files)} shot data files and {len(group_files)} shot group files"
    )

    # Combine shot data
    all_shots = []
    for file in shot_files:
        file_path = os.path.join(PROCESSED_DIR, file)
        try:
            df = pd.read_csv(file_path)
            print(f"Reading {file}: {len(df)} rows")
            all_shots.append(df)
        except Exception as e:
            print(f"Error reading {file}: {e}")

    if all_shots:
        # Combine all dataframes, handling new columns
        print("Combining shot data...")
        combined_shots = pd.concat(all_shots, ignore_index=True, sort=False)

        # Remove duplicate shots based on StrokeId
        if "StrokeId" in combined_shots.columns:
            before_dedup = len(combined_shots)

            # Identify duplicates before removing them
            duplicates = combined_shots[
                combined_shots.duplicated(subset=["StrokeId"], keep=False)
            ]

            if not duplicates.empty:
                # Sort by key metrics if available (e.g., more recent date or better data quality)
                # This determines which duplicate we keep
                if "Date" in combined_shots.columns:
                    # Sort by date descending to keep the most recent shots
                    combined_shots = combined_shots.sort_values("Date", ascending=False)

                # Group duplicates by StrokeId for better reporting
                # We need to re-identify duplicates after sorting to get the correct keep/remove status
                duplicates = combined_shots[
                    combined_shots.duplicated(subset=["StrokeId"], keep="last")
                ]
                duplicate_ids = set(duplicates["StrokeId"])

                # Get all rows with duplicate IDs for display
                all_dupes = combined_shots[
                    combined_shots["StrokeId"].isin(duplicate_ids)
                ]
                duplicate_groups = all_dupes.groupby("StrokeId")

                print(f"\nFound {len(duplicate_groups)} duplicate shot IDs:")

                # Show summary of duplicates
                for stroke_id, group in duplicate_groups:
                    # Sort the group by Date descending if available
                    if "Date" in group.columns:
                        group = group.sort_values("Date", ascending=False)

                    print(f"  - StrokeId {stroke_id}: {len(group)} duplicates")

                    for i, (_, row) in enumerate(group.iterrows()):
                        # Get key information about the duplicate shots
                        info = {}
                        # Include key fields if they exist
                        for field in [
                            "Date",
                            "Club",
                            "PlayerName",
                            "BallSpeed",
                            "ClubSpeed",
                            "SpinRate",
                            "ReportId",
                        ]:
                            if field in row and not pd.isna(row[field]):
                                info[field] = row[field]

                        # Mark which one will be kept
                        status = " (KEEPING)" if i == 0 else " (REMOVING)"
                        print(
                            f"    Duplicate {i+1}{status}: {', '.join([f'{k}={v}' for k, v in info.items()])}"
                        )

            # Remove duplicates (keeping first occurrence after sorting)
            combined_shots = combined_shots.drop_duplicates(subset=["StrokeId"])
            after_dedup = len(combined_shots)

            if before_dedup > after_dedup:
                print(
                    f"\nRemoved {before_dedup - after_dedup} duplicate shots (keeping most recent occurrence)"
                )
                print(
                    "To change which duplicate is kept, modify the sorting criteria in the code."
                )

        # Save combined shot data
        combined_file = os.path.join(PROCESSED_DIR, "combined_shot_data.csv")
        combined_shots.to_csv(combined_file, index=False)
        print(f"Combined {len(combined_shots)} shots from {len(shot_files)} files")

    # Combine shot group data
    all_groups = []
    for file in group_files:
        file_path = os.path.join(PROCESSED_DIR, file)
        try:
            df = pd.read_csv(file_path)
            print(f"Reading {file}: {len(df)} rows")
            all_groups.append(df)
        except Exception as e:
            print(f"Error reading {file}: {e}")

    if all_groups:
        # Combine all dataframes, handling new columns
        print("Combining shot group data...")
        combined_groups = pd.concat(all_groups, ignore_index=True, sort=False)

        # Identify potential duplicates based on Date, Club, and PlayerName
        if all(
            col in combined_groups.columns for col in ["Date", "Club", "PlayerName"]
        ):
            before_dedup = len(combined_groups)

            # Create a composite key for identifying similar groups
            combined_groups["group_key"] = (
                combined_groups["Date"]
                + "_"
                + combined_groups["Club"]
                + "_"
                + combined_groups["PlayerName"].astype(str)
            )

            # Identify duplicates before removing them
            duplicates = combined_groups[
                combined_groups.duplicated(subset=["group_key"], keep=False)
            ]

            if not duplicates.empty:
                # Sort by NumStrokes (descending) to keep the groups with more shots
                combined_groups = combined_groups.sort_values(
                    "NumStrokes", ascending=False
                )

                # Group duplicates by group_key for better reporting
                # We need to re-identify duplicates after sorting to get the correct keep/remove status
                duplicates = combined_groups[
                    combined_groups.duplicated(subset=["group_key"], keep="last")
                ]
                duplicate_keys = set(duplicates["group_key"])

                # Get all rows with duplicate keys for display
                all_dupes = combined_groups[
                    combined_groups["group_key"].isin(duplicate_keys)
                ]
                duplicate_groups = all_dupes.groupby("group_key")

                print(f"\nFound {len(duplicate_groups)} duplicate shot groups:")

                # Show summary of duplicates
                for group_key, group in duplicate_groups:
                    print(f"  - Group {group_key}:")
                    # Sort the group by NumStrokes descending to show which one will be kept first
                    group = group.sort_values("NumStrokes", ascending=False)

                    for i, (_, row) in enumerate(group.iterrows()):
                        # Include key fields for comparison
                        info = {
                            "NumStrokes": (
                                row["NumStrokes"] if "NumStrokes" in row else "N/A"
                            ),
                            "Date": row["Date"] if "Date" in row else "N/A",
                            "Club": row["Club"] if "Club" in row else "N/A",
                            "PlayerName": (
                                row["PlayerName"] if "PlayerName" in row else "N/A"
                            ),
                        }
                        # Add report ID if available
                        if "ReportId" in row:
                            info["ReportId"] = row["ReportId"]

                        # Mark which one will be kept (the one with highest NumStrokes)
                        status = " (KEEPING)" if i == 0 else " (REMOVING)"
                        print(
                            f"    Group {i+1}{status}: {', '.join([f'{k}={v}' for k, v in info.items()])}"
                        )

            # Drop duplicates based on the composite key, keeping the first occurrence (with more shots)
            # Note: We've already sorted by NumStrokes descending, so the first occurrence has the most shots
            combined_groups = combined_groups.drop_duplicates(subset=["group_key"])

            # Remove the temporary key
            combined_groups = combined_groups.drop(columns=["group_key"])

            after_dedup = len(combined_groups)
            if before_dedup > after_dedup:
                print(
                    f"\nRemoved {before_dedup - after_dedup} duplicate shot groups (keeping groups with more shots)"
                )

        # Save combined shot groups
        combined_file = os.path.join(PROCESSED_DIR, "combined_shot_groups.csv")
        combined_groups.to_csv(combined_file, index=False)
        print(
            f"Combined {len(combined_groups)} shot groups from {len(group_files)} files"
        )


def add_single_url():
    """Add a single URL interactively."""
    url = input("Enter Trackman report URL: ").strip()
    if not url:
        print("No URL entered. Aborting.")
        return

    # Check if URL is valid
    if not url.startswith("http"):
        print("Invalid URL. Must start with http:// or https://")
        return

    # Check if URL already exists
    existing_urls = get_existing_urls()
    if url in existing_urls:
        print(f"URL already exists in the database.")
        process_anyway = input("Process anyway? (y/n): ").strip().lower()
        if process_anyway != "y":
            return

    # Add URL to file
    add_url_to_file(url)

    # Process the URL
    process_url(url)


def add_bulk_urls():
    """Add multiple URLs from a text input."""
    print("Enter or paste URLs (one per line). Enter a blank line when done:")
    urls = []
    while True:
        line = input().strip()
        if not line:
            break
        urls.extend(extract_urls_from_text(line))

    if not urls:
        print("No valid URLs found. Aborting.")
        return

    print(f"Found {len(urls)} URLs.")

    # Check for existing URLs
    existing_urls = get_existing_urls()
    new_urls = [url for url in urls if url not in existing_urls]

    if len(new_urls) < len(urls):
        print(f"{len(urls) - len(new_urls)} URLs already exist in the database.")
        process_all = input("Process all URLs anyway? (y/n): ").strip().lower()
        if process_all == "y":
            new_urls = urls

    if not new_urls:
        print("No new URLs to process.")
        return

    # Add and process new URLs
    for url in new_urls:
        add_url_to_file(url)
        process_url(url)


def process_pending_urls():
    """Process all pending URLs in the URL file."""
    if not os.path.exists(URL_FILE):
        print("No URL file found.")
        return

    with open(URL_FILE, "r") as f:
        lines = f.readlines()

    pending_urls = []
    for line in lines:
        if line.startswith("#") or not line.strip():
            continue

        parts = line.strip().split(",")
        if len(parts) >= 3 and parts[2] == "Pending":
            pending_urls.append(parts[0])

    if not pending_urls:
        print("No pending URLs found.")
        return

    print(f"Found {len(pending_urls)} pending URLs.")
    for url in pending_urls:
        process_url(url)


def show_menu():
    """Show the main menu."""
    print("\nTRACKMAN DATA IMPORTER")
    print("=====================")
    print("1. Add single URL")
    print("2. Add multiple URLs")
    print("3. Process pending URLs")
    print("4. Update combined data")
    print("5. Add multi-shot-group URL (supports chunked input for long URLs)")
    print("6. Process multi-shot-group URLs from file")
    print("7. Add combine URL")
    print("8. Process combine URLs from file")
    print("9. Add multiple combine URLs")
    print("10. Exit")

    choice = input("\nEnter your choice (1-10): ").strip()
    return choice


def main():
    """Main function."""
    ensure_directories()

    while True:
        choice = show_menu()

        if choice == "1":
            add_single_url()
        elif choice == "2":
            add_bulk_urls()
        elif choice == "3":
            process_pending_urls()
        elif choice == "4":
            update_combined_data()
        elif choice == "5":
            add_multi_shot_group_url()
        elif choice == "6":
            process_multi_shot_group_urls_from_file()
        elif choice == "7":
            add_combine_url()
        elif choice == "8":
            process_combine_urls_from_file()
        elif choice == "9":
            add_bulk_combine_urls()
        elif choice == "10":
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please try again.")


def process_multi_shot_group_urls_from_file():
    """Process multi-shot-group URLs from a dedicated file."""
    if not os.path.exists(MULTI_URL_FILE):
        # Create the file if it doesn't exist
        with open(MULTI_URL_FILE, "w") as f:
            f.write("# Paste your multi-shot-group URLs below (one URL per line)\n")
            f.write("# Lines starting with # are ignored\n\n")
        print(f"Created file for multi-shot-group URLs at: {MULTI_URL_FILE}")
        print(
            "Please paste your URLs into this file (one URL per line) and run this option again."
        )
        return

    # Read URLs from the file
    with open(MULTI_URL_FILE, "r") as f:
        lines = f.readlines()

    # Filter out comments and empty lines
    urls = [
        line.strip()
        for line in lines
        if line.strip() and not line.strip().startswith("#")
    ]

    if not urls:
        print(f"No URLs found in {MULTI_URL_FILE}")
        print(
            "Please paste your URLs into this file (one URL per line) and run this option again."
        )
        return

    print(f"Found {len(urls)} URLs in the file.")

    # Process each URL
    for i, url in enumerate(urls, 1):
        print(f"\nProcessing URL {i} of {len(urls)}:")

        # Check if URL is valid
        if not url.startswith("http"):
            print(f"Invalid URL (skipping): {url}")
            continue

        # Extract the report ID and shot groups
        final_url, _ = follow_redirect(url)
        if not final_url:
            print(f"Error: Could not follow redirect for {url}")
            continue

        report_id = extract_report_id(final_url)
        if not report_id:
            print(f"Error: Could not extract report ID from {final_url}")
            continue

        print(f"Report ID: {report_id}")

        # Extract shot groups from the URL
        shot_groups = extract_shot_groups_from_url(url)
        print(f"Found {len(shot_groups)} shot groups in the URL")

        # Check if URL already exists
        existing_urls = get_existing_urls()
        if url in existing_urls:
            print(f"URL already exists in the database.")
            continue

        # Add URL to file
        add_url_to_file(url)

        # Process in batches if there are many shot groups
        if len(shot_groups) > 10:
            print(f"Processing {len(shot_groups)} shot groups in batches...")

            # First, get the base report data
            base_url = f"https://web-dynamic-reports.trackmangolf.com/?r={report_id}"
            process_url(base_url, track_url=False)

            # Then process each shot group separately or in small batches
            batch_size = 5
            for j in range(0, len(shot_groups), batch_size):
                batch = shot_groups[j : j + batch_size]
                batch_url = (
                    f"https://web-dynamic-reports.trackmangolf.com/?r={report_id}"
                )
                for sg in batch:
                    batch_url += f"&sgos%5B%5D={sg}"

                print(
                    f"Processing batch {j//batch_size + 1} of {(len(shot_groups) + batch_size - 1)//batch_size}..."
                )
                process_url(batch_url, track_url=False)

            # Update the status of the original URL
            update_url_status(url, "Success")
            print("All shot groups processed successfully")
        else:
            # Process normally if not too many shot groups
            process_url(url)

    # Update combined data after processing all URLs
    update_combined_data()

    # Ask if user wants to clear the file
    clear_file = input("\nDo you want to clear the URLs file? (y/n): ").strip().lower()
    if clear_file == "y":
        with open(MULTI_URL_FILE, "w") as f:
            f.write("# Paste your multi-shot-group URLs below (one URL per line)\n")
            f.write("# Lines starting with # are ignored\n\n")
        print("File cleared successfully.")


def process_combine_url(url, track_url=True):
    """Process a Trackman Combine report URL and extract the data."""
    print(f"Processing Combine URL: {url}")

    # Follow redirects to get the final URL
    final_url, _ = follow_redirect(url)
    if not final_url:
        print(f"Error: Could not follow redirect for {url}")
        if track_url:
            update_url_status(url, "Error: Redirect failed")
        return False

    # Extract the report ID
    report_id = extract_report_id(final_url)
    if not report_id:
        print(f"Error: Could not extract report ID from {final_url}")
        if track_url:
            update_url_status(url, "Error: No report ID")
        return False

    print(f"Report ID: {report_id}")

    # Check if we've already processed this report
    raw_file = os.path.join(RAW_DIR, f"combine_report_data_{report_id}.json")
    if os.path.exists(raw_file):
        print(
            f"Combine Report {report_id} already exists. Appending new data if available."
        )

    # Fetch the report data
    report_data = fetch_report_data(report_id)
    if not report_data:
        print(f"Error: Could not fetch report data for {report_id}")
        if track_url:
            update_url_status(url, "Error: Failed to fetch data")
        return False

    # Check if this is a combine report
    if not is_combine_report(report_data):
        print(f"This is not a Trackman Combine report. Processing as regular report.")
        return process_url(url, track_url)

    # Save the raw data to a Combine-specific file
    with open(raw_file, "w") as f:
        json.dump(report_data, f, indent=2)

    # Extract shot data
    shot_data = extract_combine_shot_data(report_data)
    if shot_data is not None and not shot_data.empty:
        # Save to CSV with a Combine-specific prefix
        shot_file = os.path.join(PROCESSED_DIR, f"combine_shot_data_{report_id}.csv")
        shot_data.to_csv(shot_file, index=False)
        print(f"Saved {len(shot_data)} combine shots to {shot_file}")
    else:
        print("No combine shot data found in the report.")

    # Extract shot groups
    shot_groups = extract_combine_shot_groups(report_data)
    if shot_groups is not None and not shot_groups.empty:
        # Save to CSV with a Combine-specific prefix
        group_file = os.path.join(PROCESSED_DIR, f"combine_shot_groups_{report_id}.csv")
        shot_groups.to_csv(group_file, index=False)
        print(f"Saved {len(shot_groups)} combine shot groups to {group_file}")
    else:
        print("No combine shot group data found in the report.")

    # Update URL status
    if track_url:
        update_url_status(url, "Success (Combine)")

    # Update the combined combine data
    update_combine_data()

    return True


def update_combine_data():
    """Update the combined data files for Trackman Combine reports."""
    # Get all combine shot data files (using the combine_ prefix)
    shot_files = [
        f
        for f in os.listdir(PROCESSED_DIR)
        if f.startswith("combine_shot_data_") and f.endswith(".csv")
    ]
    group_files = [
        f
        for f in os.listdir(PROCESSED_DIR)
        if f.startswith("combine_shot_groups_") and f.endswith(".csv")
    ]

    print(
        f"Found {len(shot_files)} combine shot data files and {len(group_files)} combine shot group files"
    )

    # Combine shot data
    all_shots = []
    for file in shot_files:
        file_path = os.path.join(PROCESSED_DIR, file)
        try:
            df = pd.read_csv(file_path)
            print(f"Reading {file}: {len(df)} rows")
            all_shots.append(df)
        except Exception as e:
            print(f"Error reading {file}: {e}")

    if all_shots:
        # Combine all dataframes, handling new columns
        print("Combining combine shot data...")
        combined_shots = pd.concat(all_shots, ignore_index=True, sort=False)

        # Remove duplicate shots based on StrokeId
        if "StrokeId" in combined_shots.columns:
            before_dedup = len(combined_shots)

            # Identify duplicates before removing them
            duplicates = combined_shots[
                combined_shots.duplicated(subset=["StrokeId"], keep=False)
            ]

            if not duplicates.empty:
                # Sort by key metrics if available (e.g., more recent date or better data quality)
                # This determines which duplicate we keep
                if "GroupDate" in combined_shots.columns:
                    # Sort by date descending to keep the most recent shots
                    combined_shots = combined_shots.sort_values(
                        "GroupDate", ascending=False
                    )

                # Group duplicates by StrokeId for better reporting
                # We need to re-identify duplicates after sorting to get the correct keep/remove status
                duplicates = combined_shots[
                    combined_shots.duplicated(subset=["StrokeId"], keep="last")
                ]
                duplicate_ids = set(duplicates["StrokeId"])

                # Get all rows with duplicate IDs for display
                all_dupes = combined_shots[
                    combined_shots["StrokeId"].isin(duplicate_ids)
                ]
                duplicate_groups = all_dupes.groupby("StrokeId")

                print(f"\nFound {len(duplicate_groups)} duplicate combine shot IDs:")

                # Show summary of duplicates
                for stroke_id, group in duplicate_groups:
                    # Sort the group by Date descending if available
                    if "GroupDate" in group.columns:
                        group = group.sort_values("GroupDate", ascending=False)

                    print(f"  - StrokeId {stroke_id}: {len(group)} duplicates")

                    for i, (_, row) in enumerate(group.iterrows()):
                        # Get key information about the duplicate shots
                        info = {}
                        # Include key fields if they exist
                        for field in [
                            "GroupDate",
                            "GroupTarget",
                            "StrokeClub",
                            "Score",
                            "DistanceToPin",
                        ]:
                            if field in row and not pd.isna(row[field]):
                                info[field] = row[field]

                        # Mark which one will be kept
                        status = " (KEEPING)" if i == 0 else " (REMOVING)"
                        print(
                            f"    Duplicate {i+1}{status}: {', '.join([f'{k}={v}' for k, v in info.items()])}"
                        )

            # Remove duplicates (keeping first occurrence after sorting)
            combined_shots = combined_shots.drop_duplicates(subset=["StrokeId"])
            after_dedup = len(combined_shots)

            if before_dedup > after_dedup:
                print(
                    f"\nRemoved {before_dedup - after_dedup} duplicate combine shots (keeping most recent occurrence)"
                )

        # Save combined shot data to the combine-specific file
        combined_file = os.path.join(PROCESSED_DIR, "combine_combined_shot_data.csv")
        combined_shots.to_csv(combined_file, index=False)
        print(
            f"Combined {len(combined_shots)} combine shots from {len(shot_files)} files"
        )

    # Combine shot group data
    all_groups = []
    for file in group_files:
        file_path = os.path.join(PROCESSED_DIR, file)
        try:
            df = pd.read_csv(file_path)
            print(f"Reading {file}: {len(df)} rows")
            all_groups.append(df)
        except Exception as e:
            print(f"Error reading {file}: {e}")

    if all_groups:
        # Combine all dataframes, handling new columns
        print("Combining combine shot group data...")
        combined_groups = pd.concat(all_groups, ignore_index=True, sort=False)

        # Identify potential duplicates based on Date, Target, and PlayerName
        if all(
            col in combined_groups.columns for col in ["Date", "Target", "PlayerName"]
        ):
            before_dedup = len(combined_groups)

            # Create a composite key for identifying similar groups
            combined_groups["group_key"] = (
                combined_groups["Date"].astype(str)
                + "_"
                + combined_groups["Target"].astype(str)
                + "_"
                + combined_groups["PlayerName"].astype(str)
            )

            # Sort by NumStrokes (descending) to keep the groups with more shots
            combined_groups = combined_groups.sort_values("NumStrokes", ascending=False)

            # Identify duplicates before removing them
            # We need to re-identify duplicates after sorting to get the correct keep/remove status
            duplicates = combined_groups[
                combined_groups.duplicated(subset=["group_key"], keep="last")
            ]
            duplicate_keys = set(duplicates["group_key"])

            # Get all rows with duplicate keys for display
            all_dupes = combined_groups[
                combined_groups["group_key"].isin(duplicate_keys)
            ]
            duplicate_groups = all_dupes.groupby("group_key")

            if not duplicate_keys:
                print("\nNo duplicate combine shot groups found.")
            else:
                print(f"\nFound {len(duplicate_groups)} duplicate combine shot groups:")

                # Show summary of duplicates
                for group_key, group in duplicate_groups:
                    print(f"  - Group {group_key}:")
                    # Sort the group by NumStrokes descending to show which one will be kept first
                    group = group.sort_values("NumStrokes", ascending=False)

                    for i, (_, row) in enumerate(group.iterrows()):
                        # Include key fields for comparison
                        info = {
                            "NumStrokes": (
                                row["NumStrokes"] if "NumStrokes" in row else "N/A"
                            ),
                            "Date": row["Date"] if "Date" in row else "N/A",
                            "Target": row["Target"] if "Target" in row else "N/A",
                            "PlayerName": (
                                row["PlayerName"] if "PlayerName" in row else "N/A"
                            ),
                        }
                        # Add report ID if available
                        if "ReportId" in row:
                            info["ReportId"] = row["ReportId"]

                        # Mark which one will be kept (the one with highest NumStrokes)
                        status = " (KEEPING)" if i == 0 else " (REMOVING)"
                        print(
                            f"    Group {i+1}{status}: {', '.join([f'{k}={v}' for k, v in info.items()])}"
                        )

            # Drop duplicates based on the composite key, keeping the first occurrence (with more shots)
            # Note: We've already sorted by NumStrokes descending, so the first occurrence has the most shots
            combined_groups = combined_groups.drop_duplicates(subset=["group_key"])

            # Remove the temporary key
            combined_groups = combined_groups.drop(columns=["group_key"])

            after_dedup = len(combined_groups)
            if before_dedup > after_dedup:
                print(
                    f"\nRemoved {before_dedup - after_dedup} duplicate combine shot groups (keeping groups with more shots)"
                )

        # Save combined shot groups to the combine-specific file
        combined_file = os.path.join(PROCESSED_DIR, "combine_combined_shot_groups.csv")
        combined_groups.to_csv(combined_file, index=False)
        print(
            f"Combined {len(combined_groups)} combine shot groups from {len(group_files)} files"
        )


def add_combine_url():
    """Add a Trackman Combine report URL interactively."""
    url = input("Enter Trackman Combine report URL: ").strip()
    if not url:
        print("No URL entered. Aborting.")
        return

    # Check if URL is valid
    if not url.startswith("http"):
        print("Invalid URL. Must start with http:// or https://")
        return

    # Check if URL already exists
    existing_urls = get_existing_urls()
    if url in existing_urls:
        print(f"URL already exists in the database.")
        process_anyway = input("Process anyway? (y/n): ").strip().lower()
        if process_anyway != "y":
            return

    # Add URL to file
    add_url_to_file(url)

    # Process the URL as a combine report
    process_combine_url(url)

    # Note: update_combine_data() is now called from within process_combine_url


def process_combine_urls_from_file():
    """Process Trackman Combine report URLs from a dedicated file."""
    if not os.path.exists(COMBINE_URL_FILE):
        # Create the file if it doesn't exist
        with open(COMBINE_URL_FILE, "w") as f:
            f.write(
                "# Paste your Trackman Combine report URLs below (one URL per line)\n"
            )
            f.write("# Lines starting with # are ignored\n\n")
        print(f"Created file for Combine report URLs at: {COMBINE_URL_FILE}")
        print(
            "Please paste your URLs into this file (one URL per line) and run this option again."
        )
        return

    # Read URLs from the file
    with open(COMBINE_URL_FILE, "r") as f:
        lines = f.readlines()

    # Filter out comments and empty lines
    urls = [
        line.strip()
        for line in lines
        if line.strip() and not line.strip().startswith("#")
    ]

    if not urls:
        print(f"No URLs found in {COMBINE_URL_FILE}")
        print(
            "Please paste your URLs into this file (one URL per line) and run this option again."
        )
        return

    print(f"Found {len(urls)} URLs in the file.")

    # Process each URL
    for i, url in enumerate(urls, 1):
        print(f"\nProcessing URL {i} of {len(urls)}:")

        # Check if URL is valid
        if not url.startswith("http"):
            print(f"Invalid URL (skipping): {url}")
            continue

        # Add URL to tracking file if not already there
        existing_urls = get_existing_urls()
        if url not in existing_urls:
            add_url_to_file(url)

        # Process the URL as a combine report
        process_combine_url(url)

    # Note: update_combine_data() is now called from within process_combine_url for each URL

    # Ask if user wants to clear the file
    clear_file = input("\nDo you want to clear the URLs file? (y/n): ").strip().lower()
    if clear_file == "y":
        with open(COMBINE_URL_FILE, "w") as f:
            f.write(
                "# Paste your Trackman Combine report URLs below (one URL per line)\n"
            )
            f.write("# Lines starting with # are ignored\n\n")
        print("File cleared successfully.")


def add_bulk_combine_urls():
    """Add multiple Trackman Combine report URLs at once."""
    print("\nEnter Trackman Combine report URLs (one per line).")
    print("Enter a blank line when done.")

    urls = []
    while True:
        url = input("> ").strip()
        if not url:
            break
        urls.append(url)

    if not urls:
        print("No URLs entered. Aborting.")
        return

    print(f"\nProcessing {len(urls)} Combine URLs...")

    # Process each URL
    for i, url in enumerate(urls, 1):
        print(f"\nProcessing URL {i} of {len(urls)}:")

        # Check if URL is valid
        if not url.startswith("http"):
            print(f"Invalid URL (skipping): {url}")
            continue

        # Check if URL already exists
        existing_urls = get_existing_urls()
        if url in existing_urls:
            print(f"URL already exists in the database.")
            continue

        # Add URL to file
        add_url_to_file(url)

        # Process the URL as a combine report
        process_combine_url(url)

    print("\nAll Combine URLs processed.")

    # Also add the URLs to the combine_urls.txt file for future reference
    with open(COMBINE_URL_FILE, "a") as f:
        for url in urls:
            f.write(f"{url}\n")

    print(f"Added {len(urls)} URLs to {COMBINE_URL_FILE}")


if __name__ == "__main__":
    main()
