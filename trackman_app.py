#!/usr/bin/env python3
"""
Trackman Data Analysis Application

This is the main entry point for the Trackman data analysis application.
"""

import os
import subprocess
import sys


def show_menu():
    """Show the main menu."""
    print("\nTRACKMAN DATA ANALYSIS APPLICATION")
    print("=================================")
    print("1. Import Trackman Data")
    print("2. Analyze Trackman Data")
    print("3. Analyze Trackman Combine Data")
    print("4. Exit")

    choice = input("\nEnter your choice (1-4): ").strip()
    return choice


def run_importer():
    """Run the data importer."""
    script_path = os.path.join("src", "trackman_importer.py")
    subprocess.run([sys.executable, script_path])


def run_analyzer():
    """Run the data analyzer."""
    script_path = os.path.join("src", "trackman_analysis.py")
    subprocess.run([sys.executable, script_path])


def run_combine_analyzer():
    """Run the Trackman Combine data analyzer."""
    script_path = os.path.join("src", "trackman_analysis.py")
    subprocess.run(
        [
            sys.executable,
            "-c",
            "from src.trackman_analysis import analyze_combine_data, visualize_combine_data; analyze_combine_data(); visualize_combine_data()",
        ]
    )


def main():
    """Main function."""
    while True:
        choice = show_menu()

        if choice == "1":
            run_importer()
        elif choice == "2":
            run_analyzer()
        elif choice == "3":
            run_combine_analyzer()
        elif choice == "4":
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()
