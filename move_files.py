#!/usr/bin/env python3
"""
Move Files to New Directory Structure

This script moves existing data files to the new directory structure.
"""

import glob
import os
import shutil

# Create the directory structure
os.makedirs("data/raw", exist_ok=True)
os.makedirs("data/processed", exist_ok=True)
os.makedirs("data/visualizations", exist_ok=True)

# Move raw JSON files
for file in glob.glob("report_data_*.json"):
    shutil.move(file, os.path.join("data", "raw", file))
    print(f"Moved {file} to data/raw/")

# Move processed CSV files
for file in glob.glob("shot_data_*.csv"):
    shutil.move(file, os.path.join("data", "processed", file))
    print(f"Moved {file} to data/processed/")

for file in glob.glob("shot_groups_*.csv"):
    shutil.move(file, os.path.join("data", "processed", file))
    print(f"Moved {file} to data/processed/")

for file in glob.glob("combined_*.csv"):
    shutil.move(file, os.path.join("data", "processed", file))
    print(f"Moved {file} to data/processed/")

# Move visualization files
for file in glob.glob("*.png"):
    shutil.move(file, os.path.join("data", "visualizations", file))
    print(f"Moved {file} to data/visualizations/")

for file in glob.glob("trackman_analysis_report.txt"):
    shutil.move(file, os.path.join("data", "visualizations", file))
    print(f"Moved {file} to data/visualizations/")

# Move URL file
if os.path.exists("urls to scrape for trackman data.txt"):
    shutil.copy(
        "urls to scrape for trackman data.txt",
        os.path.join("data", "trackman_urls.txt"),
    )
    print(f"Copied 'urls to scrape for trackman data.txt' to data/trackman_urls.txt")

print("File migration complete!")
