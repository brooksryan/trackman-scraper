#!/usr/bin/env python3
"""
Trackman API Scraper

This script extracts golf shot data directly from Trackman API endpoints.
"""

import json
import os
import re
import time
from urllib.parse import parse_qs, urlparse

import pandas as pd
import requests


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

    # Try different parameter names
    for param in ["ReportId", "r"]:
        if param in query_params:
            return query_params[param][0]

    return None


def fetch_report_data(report_id):
    """Fetch report data directly from the API using POST method."""
    api_url = "https://golf-player-activities.trackmangolf.com/api/reports/getreport"

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Content-Type": "application/json",
        "Origin": "https://web-dynamic-reports.trackmangolf.com",
        "Referer": "https://web-dynamic-reports.trackmangolf.com/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "Sec-Ch-Ua": '"Not:A-Brand";v="24", "Chromium";v="134"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"macOS"',
    }

    # POST payload with the report ID
    payload = {"reportId": report_id}

    try:
        response = requests.post(api_url, headers=headers, json=payload)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error fetching report data: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"Exception fetching report data: {e}")
        return None


def fetch_dispersion_data(report_id, shot_group_id=None):
    """Fetch dispersion data for a specific shot group using POST method."""
    api_url = "https://golf-player-activities.trackmangolf.com/api/reports/GetDispersionEllipse"

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Content-Type": "application/json",
        "Origin": "https://web-dynamic-reports.trackmangolf.com",
        "Referer": "https://web-dynamic-reports.trackmangolf.com/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
    }

    # POST payload with the report ID and shot group ID
    payload = {"reportId": report_id}

    if shot_group_id:
        payload["shotGroupId"] = shot_group_id

    try:
        response = requests.post(api_url, headers=headers, json=payload)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error fetching dispersion data: {response.status_code}")
            return None
    except Exception as e:
        print(f"Exception fetching dispersion data: {e}")
        return None


def extract_shot_data(report_data):
    """Extract shot data from the report data."""
    if not report_data:
        return None

    shots = []

    # Based on the observed structure, extract shots from StrokeGroups
    if "StrokeGroups" in report_data:
        for group in report_data["StrokeGroups"]:
            if "Strokes" in group:
                for stroke in group["Strokes"]:
                    # Add group metadata to each stroke
                    stroke_data = {
                        "GroupDate": group.get("Date"),
                        "GroupClub": group.get("Club"),
                        "GroupBall": group.get("Ball"),
                        "GroupTarget": group.get("Target"),
                        "PlayerName": group.get("Player", {}).get("Name"),
                        "PlayerHcp": group.get("Player", {}).get("Hcp"),
                        "PlayerGender": group.get("Player", {}).get("Gender"),
                        "StrokeId": stroke.get("Id"),
                        "StrokeTime": stroke.get("Time"),
                        "StrokeClub": stroke.get("Club"),
                        "StrokeBall": stroke.get("Ball"),
                    }

                    # Add impact location data
                    if "ImpactLocation" in stroke:
                        impact = stroke["ImpactLocation"]
                        stroke_data.update(
                            {
                                "ImpactOffset": impact.get("ImpactOffset"),
                                "ImpactHeight": impact.get("ImpactHeight"),
                                "DynamicLie": impact.get("DynamicLie"),
                            }
                        )

                    # Add measurement data
                    if "Measurement" in stroke:
                        measurement = stroke["Measurement"]
                        for key, value in measurement.items():
                            # Skip complex nested objects and arrays
                            if not isinstance(value, (dict, list)):
                                stroke_data[f"Measurement_{key}"] = value

                    # Add normalized measurement data if available
                    if "NormalizedMeasurement" in stroke:
                        normalized = stroke["NormalizedMeasurement"]
                        for key, value in normalized.items():
                            # Skip complex nested objects and arrays
                            if not isinstance(value, (dict, list)):
                                stroke_data[f"Normalized_{key}"] = value

                    shots.append(stroke_data)

    # If we found shots, convert to DataFrame
    if shots:
        df = pd.DataFrame(shots)
        return df

    return None


def extract_shot_groups(report_data):
    """Extract shot groups from the report data."""
    if not report_data:
        return None

    shot_groups = []

    # Based on the observed structure, extract StrokeGroups
    if "StrokeGroups" in report_data:
        for group in report_data["StrokeGroups"]:
            group_data = {
                "Date": group.get("Date"),
                "Club": group.get("Club"),
                "Ball": group.get("Ball"),
                "Target": group.get("Target"),
                "NumStrokes": len(group.get("Strokes", [])),
                "PlayerName": group.get("Player", {}).get("Name"),
                "PlayerHcp": group.get("Player", {}).get("Hcp"),
                "PlayerGender": group.get("Player", {}).get("Gender"),
                "PlayerID": group.get("Player", {}).get("Id"),
            }

            # Calculate some basic stats for the group
            if "Strokes" in group and group["Strokes"]:
                measurements = [
                    stroke.get("Measurement", {}) for stroke in group["Strokes"]
                ]

                # Calculate averages for common metrics
                metrics = [
                    "BallSpeed",
                    "ClubSpeed",
                    "LaunchAngle",
                    "SpinRate",
                    "AttackAngle",
                    "ClubPath",
                    "FaceAngle",
                ]
                for metric in metrics:
                    values = [
                        m.get(metric) for m in measurements if m.get(metric) is not None
                    ]
                    if values:
                        group_data[f"Avg{metric}"] = sum(values) / len(values)
                        group_data[f"Min{metric}"] = min(values)
                        group_data[f"Max{metric}"] = max(values)

            shot_groups.append(group_data)

    # If we found shot groups, convert to DataFrame
    if shot_groups:
        df = pd.DataFrame(shot_groups)
        return df

    return None


def is_combine_report(report_data):
    """Determine if the report is a Trackman Combine report."""
    if not report_data:
        return False

    # Check for combine-specific attributes
    if "CombineScore" in report_data:
        return True

    # Check if the Kind attribute indicates a combine report
    if report_data.get("Kind") == "combineTestReport":
        return True

    # Check if any stroke group has a distance target (typical for combine reports)
    if "StrokeGroups" in report_data:
        for group in report_data["StrokeGroups"]:
            # Combine groups often have distance targets or specific naming patterns
            if "Target" in group and group.get("Target", "").isdigit():
                return True
            if "Name" in group and "yards" in group.get("Name", "").lower():
                return True

    return False


def extract_combine_data(report_data):
    """Extract combine-specific data from the report."""
    if not report_data or not is_combine_report(report_data):
        return None

    # Extract combine score from TestResult.Statistics.AvgScore if available
    combine_score = None
    if "TestResult" in report_data and "Statistics" in report_data["TestResult"]:
        combine_score = report_data["TestResult"]["Statistics"].get("AvgScore")

    combine_data = {
        "CombineScore": combine_score or report_data.get("CombineScore"),
        "CombineHcp": report_data.get("CombineHcp"),
        "CombineName": report_data.get("Name")
        or (report_data.get("TestResult", {}).get("Definition", {}).get("Name")),
        "CombineDate": (
            report_data.get("Date") or report_data.get("Time", "").split("T")[0]
            if "Time" in report_data
            else None
        ),
        "PlayerName": report_data.get("Player", {}).get("Name"),
        "PlayerHcp": report_data.get("Player", {}).get("Hcp"),
        "PlayerGender": report_data.get("Player", {}).get("Gender"),
        "PlayerID": report_data.get("Player", {}).get("Id"),
    }

    return combine_data


def extract_combine_shot_data(report_data):
    """Extract shot data from a combine report with distance-based targets."""
    if not report_data or not is_combine_report(report_data):
        return None

    shots = []
    combine_data = extract_combine_data(report_data) or {}

    # Based on the observed structure, extract shots from StrokeGroups
    if "StrokeGroups" in report_data:
        for group in report_data["StrokeGroups"]:
            if "Strokes" in group:
                for stroke in group["Strokes"]:
                    # Add group metadata and combine metadata to each stroke
                    stroke_data = {
                        "GroupDate": group.get("Date"),
                        "GroupTarget": group.get(
                            "Target"
                        ),  # This is often the distance in combine reports
                        "GroupName": group.get(
                            "Name"
                        ),  # This might contain the distance description
                        "PlayerName": (group.get("Player") or {}).get("Name")
                        or combine_data.get("PlayerName"),
                        "PlayerHcp": (group.get("Player") or {}).get("Hcp")
                        or combine_data.get("PlayerHcp"),
                        "PlayerGender": (group.get("Player") or {}).get("Gender")
                        or combine_data.get("PlayerGender"),
                        "StrokeId": stroke.get("Id"),
                        "StrokeTime": stroke.get("Time"),
                        "StrokeClub": stroke.get("Club"),
                        "StrokeBall": stroke.get("Ball"),
                        "CombineScore": combine_data.get("CombineScore"),
                        "CombineHcp": combine_data.get("CombineHcp"),
                        "CombineName": combine_data.get("CombineName"),
                        "TargetDistance": group.get(
                            "Target"
                        ),  # Store the target distance
                        "DistanceToPin": (stroke.get("Result") or {}).get(
                            "DistanceToPin"
                        ),  # How close to target
                        "Score": (stroke.get("Result") or {}).get(
                            "Score"
                        ),  # Points scored for this shot
                    }

                    # Add impact location data
                    if "ImpactLocation" in stroke:
                        impact = stroke["ImpactLocation"]
                        stroke_data.update(
                            {
                                "ImpactLocationX": impact.get("X"),
                                "ImpactLocationY": impact.get("Y"),
                            }
                        )

                    # Add measurement data
                    if "Measurement" in stroke:
                        measurement = stroke["Measurement"]
                        for key, value in measurement.items():
                            stroke_data[f"Measurement_{key}"] = value

                    # Add normalized data
                    if "Normalized" in stroke:
                        normalized = stroke["Normalized"]
                        for key, value in normalized.items():
                            stroke_data[f"Normalized_{key}"] = value

                    # Add result data
                    if "Result" in stroke:
                        result = stroke["Result"]
                        for key, value in result.items():
                            if key not in [
                                "Score",
                                "DistanceToPin",
                            ]:  # Already added these
                                stroke_data[f"Result_{key}"] = value

                    shots.append(stroke_data)

    return pd.DataFrame(shots) if shots else None


def extract_combine_shot_groups(report_data):
    """Extract shot groups from a combine report with distance-based targets."""
    if not report_data or not is_combine_report(report_data):
        return None

    shot_groups = []
    combine_data = extract_combine_data(report_data) or {}

    # Get the overall combine score
    combine_score = combine_data.get("CombineScore")

    # Get the combine date
    combine_date = combine_data.get("CombineDate")
    if not combine_date and "Time" in report_data:
        combine_date = report_data["Time"].split("T")[0]

    # Based on the observed structure, extract StrokeGroups
    if "StrokeGroups" in report_data:
        for group in report_data["StrokeGroups"]:
            group_data = {
                "Date": group.get("Date") or combine_date,
                "Target": group.get(
                    "Target"
                ),  # This is often the distance in combine reports
                "TargetName": group.get(
                    "Name"
                ),  # This might contain the distance description
                "NumStrokes": len(group.get("Strokes", [])),
                "PlayerName": (group.get("Player") or {}).get("Name")
                or combine_data.get("PlayerName"),
                "PlayerHcp": (group.get("Player") or {}).get("Hcp")
                or combine_data.get("PlayerHcp"),
                "PlayerGender": (group.get("Player") or {}).get("Gender")
                or combine_data.get("PlayerGender"),
                "PlayerID": (group.get("Player") or {}).get("Id")
                or combine_data.get("PlayerID"),
                "CombineScore": combine_score,
                "CombineHcp": combine_data.get("CombineHcp"),
                "CombineName": combine_data.get("CombineName"),
                "ReportId": report_data.get("Id"),
            }

            # Calculate some basic stats for the group
            if "Strokes" in group and group["Strokes"]:
                # Get all measurements
                measurements = [
                    stroke.get("Measurement", {}) for stroke in group["Strokes"]
                ]

                # Calculate averages for common metrics
                metrics = [
                    "BallSpeed",
                    "ClubSpeed",
                    "LaunchAngle",
                    "SpinRate",
                    "AttackAngle",
                    "ClubPath",
                    "FaceAngle",
                    "Carry",
                    "Side",
                ]

                for metric in metrics:
                    values = [
                        m.get(metric) for m in measurements if m.get(metric) is not None
                    ]
                    if values:
                        group_data[f"Avg{metric}"] = sum(values) / len(values)
                        group_data[f"Min{metric}"] = min(values)
                        group_data[f"Max{metric}"] = max(values)

                # Calculate average score and distance to pin for combine reports
                results = [stroke.get("Result", {}) for stroke in group["Strokes"]]

                scores = [r.get("Score") for r in results if r.get("Score") is not None]
                if scores:
                    group_data["AvgScore"] = sum(scores) / len(scores)
                    group_data["TotalScore"] = sum(scores)
                    group_data["MaxScore"] = max(scores)

                distances = [
                    r.get("DistanceToPin")
                    for r in results
                    if r.get("DistanceToPin") is not None
                ]
                if distances:
                    group_data["AvgDistanceToPin"] = sum(distances) / len(distances)
                    group_data["MinDistanceToPin"] = min(distances)
                    group_data["MaxDistanceToPin"] = max(distances)

            shot_groups.append(group_data)

    return pd.DataFrame(shot_groups) if shot_groups else None


def main():
    # Extract URLs from the file
    urls = extract_urls_from_file("urls to scrape for trackman data.txt")

    all_shots = []
    all_shot_groups = []
    results = []

    for url in urls:
        print(f"\nProcessing URL: {url}")

        # Follow redirects to get the final URL
        final_url, _ = follow_redirect(url)
        if not final_url:
            continue

        # Extract the report ID
        report_id = extract_report_id(final_url)
        if not report_id:
            print(f"Could not extract report ID from {final_url}")
            continue

        print(f"Report ID: {report_id}")

        # Fetch report data
        report_data = fetch_report_data(report_id)
        if not report_data:
            print(f"Could not fetch report data for {report_id}")
            continue

        # Save the raw report data for analysis
        with open(f"report_data_{report_id}.json", "w") as f:
            json.dump(report_data, f, indent=2)

        print(f"Saved raw report data to report_data_{report_id}.json")

        # Extract shot data
        shot_data = extract_shot_data(report_data)
        if isinstance(shot_data, pd.DataFrame):
            print(f"Extracted {len(shot_data)} shots")
            all_shots.append(shot_data)

            # Save the shot data
            shot_data.to_csv(f"shot_data_{report_id}.csv", index=False)
            print(f"Saved shot data to shot_data_{report_id}.csv")

        # Extract shot groups
        shot_groups = extract_shot_groups(report_data)
        if isinstance(shot_groups, pd.DataFrame):
            print(f"Extracted {len(shot_groups)} shot groups")
            all_shot_groups.append(shot_groups)

            # Save the shot groups
            shot_groups.to_csv(f"shot_groups_{report_id}.csv", index=False)
            print(f"Saved shot groups to shot_groups_{report_id}.csv")

        results.append(
            {
                "original_url": url,
                "final_url": final_url,
                "report_id": report_id,
                "has_report_data": report_data is not None,
                "has_shot_data": shot_data is not None,
                "has_shot_groups": shot_groups is not None,
                "num_shots": (
                    len(shot_data) if isinstance(shot_data, pd.DataFrame) else 0
                ),
                "num_shot_groups": (
                    len(shot_groups) if isinstance(shot_groups, pd.DataFrame) else 0
                ),
            }
        )

    # Save the results
    with open("trackman_api_results.json", "w") as f:
        json.dump(results, f, indent=2)

    # Combine all shot data if available
    if all_shots:
        combined_shots = pd.concat(all_shots, ignore_index=True)
        combined_shots.to_csv("combined_shot_data.csv", index=False)
        print(f"\nCombined {len(combined_shots)} shots from all reports")
        print("Saved combined shot data to combined_shot_data.csv")

    # Combine all shot groups if available
    if all_shot_groups:
        combined_groups = pd.concat(all_shot_groups, ignore_index=True)
        combined_groups.to_csv("combined_shot_groups.csv", index=False)
        print(f"Combined {len(combined_groups)} shot groups from all reports")
        print("Saved combined shot groups to combined_shot_groups.csv")

    print("\nAnalysis complete. Results saved to trackman_api_results.json")


if __name__ == "__main__":
    main()
