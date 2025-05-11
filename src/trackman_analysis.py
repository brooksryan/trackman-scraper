#!/usr/bin/env python3
"""
Trackman Data Analysis

This script provides simple analysis and visualization of Trackman shot data.
"""

import os
import sys
from datetime import datetime

import matplotlib.cm as cm
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

# Constants
DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"
)
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
VISUALIZATIONS_DIR = os.path.join(DATA_DIR, "visualizations")
ANALYSIS_DIR = os.path.join(DATA_DIR, "analysis")
COMBINED_SHOTS = os.path.join(PROCESSED_DIR, "combined_shot_data.csv")
COMBINED_GROUPS = os.path.join(PROCESSED_DIR, "combined_shot_groups.csv")
COMBINE_SHOTS = os.path.join(PROCESSED_DIR, "combine_combined_shot_data.csv")
COMBINE_GROUPS = os.path.join(PROCESSED_DIR, "combine_combined_shot_groups.csv")

# Unit conversion constants
MS_TO_MPH = 2.23694  # Convert meters/second to miles/hour


def ensure_directories():
    """Ensure all necessary directories exist."""
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    os.makedirs(VISUALIZATIONS_DIR, exist_ok=True)
    os.makedirs(ANALYSIS_DIR, exist_ok=True)


def load_data():
    """Load the combined shot data."""
    shots_file = os.path.join(PROCESSED_DIR, "combined_shot_data.csv")
    groups_file = os.path.join(PROCESSED_DIR, "combined_shot_groups.csv")

    if not os.path.exists(shots_file):
        print(f"Error: Combined shot data file not found at {shots_file}")
        return None, None

    shots_df = pd.read_csv(shots_file)

    if os.path.exists(groups_file):
        groups_df = pd.read_csv(groups_file)
    else:
        groups_df = None
        print(f"Warning: Combined shot groups file not found at {groups_file}")

    return shots_df, groups_df


def clean_data(df):
    """Clean and prepare the data for analysis."""
    if df is None:
        return None

    # Convert date columns to datetime
    if "GroupDate" in df.columns:
        df["GroupDate"] = pd.to_datetime(df["GroupDate"])

    # Convert time columns to datetime
    if "StrokeTime" in df.columns:
        df["StrokeTime"] = pd.to_datetime(df["StrokeTime"])

    # Create a club category column
    if "StrokeClub" in df.columns:
        df["ClubCategory"] = df["StrokeClub"].apply(categorize_club)

    return df


def categorize_club(club):
    """Categorize clubs into groups."""
    if pd.isna(club):
        return "Unknown"

    club = str(club).lower()

    if "driver" in club or "1w" in club:
        return "Driver"
    elif "wood" in club or "w" in club:
        return "Fairway Woods"
    elif "hybrid" in club or "h" in club or "rescue" in club:
        return "Hybrids"
    elif "iron" in club or "i" in club:
        return "Irons"
    elif "wedge" in club or "w" in club:
        return "Wedges"
    elif "putter" in club or "p" in club:
        return "Putter"
    else:
        return "Other"


def convert_speed_to_mph(speed_ms):
    """Convert speed from meters/second to miles/hour."""
    if pd.isna(speed_ms):
        return None
    return speed_ms * MS_TO_MPH


def analyze_club_data(club_name=None):
    """Analyze data for a specific club or all clubs."""
    # Ensure the analysis directory exists
    os.makedirs(ANALYSIS_DIR, exist_ok=True)

    # Load the combined shot data
    if not os.path.exists(COMBINED_SHOTS):
        print("No combined shot data found. Please run the data importer first.")
        return

    df = pd.read_csv(COMBINED_SHOTS)

    # Apply unit conversions to speed measurements
    if "Measurement_ClubSpeed" in df.columns:
        df["Measurement_ClubSpeed_mph"] = df["Measurement_ClubSpeed"].apply(
            convert_speed_to_mph
        )

    if "Measurement_BallSpeed" in df.columns:
        df["Measurement_BallSpeed_mph"] = df["Measurement_BallSpeed"].apply(
            convert_speed_to_mph
        )

    # Determine which club column to use
    club_column = None
    if "StrokeClub" in df.columns:
        club_column = "StrokeClub"
    elif "GroupClub" in df.columns:
        club_column = "GroupClub"

    if club_column is None:
        print("Club information not found in the data.")
        return

    # Filter by club if specified
    if club_name:
        df = df[df[club_column] == club_name]
        if len(df) == 0:
            print(f"No data found for club: {club_name}")
            return
        print(f"Analyzing data for {club_name} ({len(df)} shots)")
    else:
        print(f"Analyzing all club data ({len(df)} shots)")

    # Generate summary statistics
    summary = {}

    # Group by club
    clubs = df[club_column].unique()
    for club in clubs:
        club_data = df[df[club_column] == club]
        summary[club] = {
            "shots": len(club_data),
            "avg_metrics": {},
        }

        # Calculate average metrics
        for metric in [
            "Measurement_AttackAngle",
            "Measurement_ClubPath",
            "Measurement_ClubSpeed",
            "Measurement_ClubSpeed_mph",  # Added mph version
            "Measurement_FaceAngle",
            "Measurement_LaunchAngle",
            "Measurement_SpinRate",
        ]:
            if metric in club_data.columns:
                summary[club]["avg_metrics"][metric] = club_data[metric].mean()

    # Print summary
    print("\nSummary Statistics:")
    for club, stats in summary.items():
        print(f"\n{club} ({stats['shots']} shots):")
        for metric, value in stats["avg_metrics"].items():
            # Format the output based on the metric
            if "Angle" in metric:
                print(f"  Average {metric.replace('Measurement_', '')}: {value:.1f}°")
            elif "ClubSpeed" in metric and "mph" in metric:
                print(f"  Average Club Speed: {value:.1f} mph")
            elif "ClubSpeed" in metric:
                print(f"  Average Club Speed (raw): {value:.1f} m/s")
            elif "SpinRate" in metric:
                print(
                    f"  Average {metric.replace('Measurement_', '')}: {value:.0f} rpm"
                )
            else:
                print(f"  Average {metric.replace('Measurement_', '')}: {value:.2f}")


def analyze_shot_metrics(df):
    """Analyze key shot metrics."""
    if df is None:
        return None

    # Calculate basic statistics for key metrics by club
    metrics = [
        "Measurement_BallSpeed",
        "Measurement_ClubSpeed",
        "Measurement_LaunchAngle",
        "Measurement_SpinRate",
        "Measurement_Carry",
        "Measurement_Total",
    ]

    # Filter out metrics that don't exist in the dataframe
    metrics = [m for m in metrics if m in df.columns]

    if not metrics:
        print("Error: No valid metrics found in the dataframe")
        return None

    if "StrokeClub" not in df.columns:
        print("Error: StrokeClub column not found in the dataframe")
        return None

    club_stats = (
        df.groupby("StrokeClub")[metrics]
        .agg(["mean", "std", "min", "max"])
        .reset_index()
    )

    return club_stats


def plot_club_performance(df):
    """Plot performance metrics by club."""
    if df is None:
        return

    # Check if required columns exist
    required_cols = [
        "StrokeClub",
        "Measurement_BallSpeed",
        "Measurement_Carry",
        "Measurement_LaunchAngle",
        "Measurement_SpinRate",
    ]
    missing_cols = [col for col in required_cols if col not in df.columns]

    if missing_cols:
        print(f"Warning: Missing columns for club performance plot: {missing_cols}")
        return

    # Apply unit conversions to speed measurements
    if "Measurement_ClubSpeed" in df.columns:
        df["Measurement_ClubSpeed_mph"] = df["Measurement_ClubSpeed"].apply(
            convert_speed_to_mph
        )

    if "Measurement_BallSpeed" in df.columns:
        df["Measurement_BallSpeed_mph"] = df["Measurement_BallSpeed"].apply(
            convert_speed_to_mph
        )

    # Create a figure with multiple subplots
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle("Club Performance Metrics", fontsize=16)

    # Plot 1: Ball Speed by Club
    sns.boxplot(x="StrokeClub", y="Measurement_BallSpeed_mph", data=df, ax=axes[0, 0])
    axes[0, 0].set_title("Ball Speed by Club")
    axes[0, 0].set_xlabel("Club")
    axes[0, 0].set_ylabel("Ball Speed (mph)")
    axes[0, 0].tick_params(axis="x", rotation=45)

    # Plot 2: Carry Distance by Club
    sns.boxplot(x="StrokeClub", y="Measurement_Carry", data=df, ax=axes[0, 1])
    axes[0, 1].set_title("Carry Distance by Club")
    axes[0, 1].set_xlabel("Club")
    axes[0, 1].set_ylabel("Carry Distance (yards)")
    axes[0, 1].tick_params(axis="x", rotation=45)

    # Plot 3: Launch Angle by Club
    sns.boxplot(x="StrokeClub", y="Measurement_LaunchAngle", data=df, ax=axes[1, 0])
    axes[1, 0].set_title("Launch Angle by Club")
    axes[1, 0].set_xlabel("Club")
    axes[1, 0].set_ylabel("Launch Angle (degrees)")
    axes[1, 0].tick_params(axis="x", rotation=45)

    # Plot 4: Spin Rate by Club
    sns.boxplot(x="StrokeClub", y="Measurement_SpinRate", data=df, ax=axes[1, 1])
    axes[1, 1].set_title("Spin Rate by Club")
    axes[1, 1].set_xlabel("Club")
    axes[1, 1].set_ylabel("Spin Rate (rpm)")
    axes[1, 1].tick_params(axis="x", rotation=45)

    plt.tight_layout()
    plt.subplots_adjust(top=0.9)

    # Save the figure
    output_file = os.path.join(VISUALIZATIONS_DIR, "club_performance.png")
    plt.savefig(output_file)
    plt.close()

    print(f"Club performance chart saved to {output_file}")


def plot_shot_dispersion(df):
    """Plot shot dispersion patterns."""
    if df is None:
        return

    # Check if required columns exist
    required_cols = ["StrokeClub", "Measurement_CarrySide", "Measurement_Carry"]
    missing_cols = [col for col in required_cols if col not in df.columns]

    if missing_cols:
        print(f"Warning: Missing columns for shot dispersion plot: {missing_cols}")
        return

    # Create a figure for shot dispersion
    plt.figure(figsize=(12, 10))

    # Create a scatter plot of shot dispersion
    clubs = df["StrokeClub"].unique()

    # Use default colors from matplotlib
    for i, club in enumerate(clubs):
        club_data = df[df["StrokeClub"] == club]
        plt.scatter(
            club_data["Measurement_CarrySide"],
            club_data["Measurement_Carry"],
            label=club,
            alpha=0.7,
        )

    plt.axvline(x=0, color="black", linestyle="--", alpha=0.3)
    plt.grid(True, alpha=0.3)
    plt.title("Shot Dispersion by Club", fontsize=16)
    plt.xlabel("Side Carry (yards)", fontsize=12)
    plt.ylabel("Carry Distance (yards)", fontsize=12)
    plt.legend(title="Club")

    # Save the figure
    output_file = os.path.join(VISUALIZATIONS_DIR, "shot_dispersion.png")
    plt.savefig(output_file)
    plt.close()

    print(f"Shot dispersion chart saved to {output_file}")


def plot_club_path_face_angle(df):
    """Plot club path vs face angle."""
    if df is None:
        return

    # Check if required columns exist
    required_cols = ["StrokeClub", "Measurement_ClubPath", "Measurement_FaceAngle"]
    missing_cols = [col for col in required_cols if col not in df.columns]

    if missing_cols:
        print(
            f"Warning: Missing columns for club path vs face angle plot: {missing_cols}"
        )
        return

    # Create a figure for club path vs face angle
    plt.figure(figsize=(12, 10))

    # Create a scatter plot of club path vs face angle
    clubs = df["StrokeClub"].unique()

    # Use default colors from matplotlib
    for i, club in enumerate(clubs):
        club_data = df[df["StrokeClub"] == club]
        plt.scatter(
            club_data["Measurement_ClubPath"],
            club_data["Measurement_FaceAngle"],
            label=club,
            alpha=0.7,
        )

    plt.axvline(x=0, color="black", linestyle="--", alpha=0.3)
    plt.axhline(y=0, color="black", linestyle="--", alpha=0.3)
    plt.grid(True, alpha=0.3)
    plt.title("Club Path vs Face Angle", fontsize=16)
    plt.xlabel("Club Path (degrees)", fontsize=12)
    plt.ylabel("Face Angle (degrees)", fontsize=12)
    plt.legend(title="Club")

    # Save the figure
    output_file = os.path.join(VISUALIZATIONS_DIR, "club_path_face_angle.png")
    plt.savefig(output_file)
    plt.close()

    print(f"Club path vs face angle chart saved to {output_file}")


def plot_trends_over_time(df):
    """Plot trends in key metrics over time."""
    if df is None:
        return

    # Check if required columns exist
    required_cols = [
        "StrokeClub",
        "StrokeTime",
        "Measurement_BallSpeed",
        "Measurement_Carry",
        "Measurement_ClubSpeed",
        "Measurement_SmashFactor",
    ]
    missing_cols = [col for col in required_cols if col not in df.columns]

    if missing_cols:
        print(f"Warning: Missing columns for trends over time plot: {missing_cols}")
        return

    # Apply unit conversions to speed measurements
    if "Measurement_ClubSpeed" in df.columns:
        df["Measurement_ClubSpeed_mph"] = df["Measurement_ClubSpeed"].apply(
            convert_speed_to_mph
        )

    if "Measurement_BallSpeed" in df.columns:
        df["Measurement_BallSpeed_mph"] = df["Measurement_BallSpeed"].apply(
            convert_speed_to_mph
        )

    # Convert StrokeTime to datetime and create a numeric index for plotting
    try:
        # First try to parse the timestamps
        df["DateTime"] = pd.to_datetime(df["StrokeTime"])

        # Sort by time
        df = df.sort_values("DateTime")

        # Create a simpler date representation for the x-axis
        df["DateFormatted"] = df["DateTime"].dt.strftime("%Y-%m-%d")

        # Create a numeric index for each unique date
        unique_dates = df["DateFormatted"].unique()
        date_to_index = {date: i for i, date in enumerate(unique_dates)}
        df["DateIndex"] = df["DateFormatted"].map(date_to_index)

        # Use the numeric index for plotting
        x_axis = "DateIndex"

        # Create custom x-tick labels
        x_ticks = [date_to_index[date] for date in unique_dates]
        x_labels = unique_dates
    except:
        # If datetime conversion fails, use a simple numeric index
        print("Warning: Could not parse timestamps. Using shot sequence instead.")
        df = df.sort_values("StrokeTime")  # Still sort by the original time string
        df["DateIndex"] = range(len(df))
        x_axis = "DateIndex"
        x_ticks = None
        x_labels = None

    # Create a figure with multiple subplots
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle("Performance Trends Over Time", fontsize=16)

    # Plot 1: Ball Speed Over Time
    for club in df["StrokeClub"].unique():
        club_data = df[df["StrokeClub"] == club]
        axes[0, 0].plot(
            club_data[x_axis],
            club_data["Measurement_BallSpeed_mph"],  # Use mph version
            label=club,
            marker="o",
            linestyle="-",
            alpha=0.7,
        )

    axes[0, 0].set_title("Ball Speed Over Time")
    axes[0, 0].set_xlabel("Date")
    axes[0, 0].set_ylabel("Ball Speed (mph)")
    if x_ticks is not None:
        axes[0, 0].set_xticks(x_ticks)
        axes[0, 0].set_xticklabels(x_labels, rotation=45)

    # Plot 2: Carry Distance Over Time
    for club in df["StrokeClub"].unique():
        club_data = df[df["StrokeClub"] == club]
        axes[0, 1].plot(
            club_data[x_axis],
            club_data["Measurement_Carry"],
            label=club,
            marker="o",
            linestyle="-",
            alpha=0.7,
        )

    axes[0, 1].set_title("Carry Distance Over Time")
    axes[0, 1].set_xlabel("Date")
    axes[0, 1].set_ylabel("Carry Distance (yards)")
    if x_ticks is not None:
        axes[0, 1].set_xticks(x_ticks)
        axes[0, 1].set_xticklabels(x_labels, rotation=45)

    # Plot 3: Club Speed Over Time
    for club in df["StrokeClub"].unique():
        club_data = df[df["StrokeClub"] == club]
        axes[1, 0].plot(
            club_data[x_axis],
            club_data["Measurement_ClubSpeed_mph"],  # Use mph version
            label=club,
            marker="o",
            linestyle="-",
            alpha=0.7,
        )

    axes[1, 0].set_title("Club Speed Over Time")
    axes[1, 0].set_xlabel("Date")
    axes[1, 0].set_ylabel("Club Speed (mph)")
    if x_ticks is not None:
        axes[1, 0].set_xticks(x_ticks)
        axes[1, 0].set_xticklabels(x_labels, rotation=45)

    # Plot 4: Smash Factor Over Time
    for club in df["StrokeClub"].unique():
        club_data = df[df["StrokeClub"] == club]
        axes[1, 1].plot(
            club_data[x_axis],
            club_data["Measurement_SmashFactor"],
            label=club,
            marker="o",
            linestyle="-",
            alpha=0.7,
        )

    axes[1, 1].set_title("Smash Factor Over Time")
    axes[1, 1].set_xlabel("Date")
    axes[1, 1].set_ylabel("Smash Factor")
    if x_ticks is not None:
        axes[1, 1].set_xticks(x_ticks)
        axes[1, 1].set_xticklabels(x_labels, rotation=45)

    # Add a single legend for all subplots
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", title="Club")

    plt.tight_layout()
    plt.subplots_adjust(top=0.9, right=0.85)

    # Save the figure
    output_file = os.path.join(VISUALIZATIONS_DIR, "performance_trends.png")
    plt.savefig(output_file)
    plt.close()

    print(f"Performance trends chart saved to {output_file}")


def generate_report(df, club_stats):
    """Generate a simple text report with key insights."""
    if df is None:
        return

    # Create the report file
    report_file = os.path.join(VISUALIZATIONS_DIR, "trackman_analysis_report.txt")

    with open(report_file, "w") as f:
        f.write("TRACKMAN DATA ANALYSIS REPORT\n")
        f.write("=============================\n\n")

        f.write(f"Total shots analyzed: {len(df)}\n")

        if "GroupDate" in df.columns:
            f.write(
                f"Date range: {df['GroupDate'].min()} to {df['GroupDate'].max()}\n\n"
            )

        f.write("CLUB PERFORMANCE SUMMARY\n")
        f.write("------------------------\n\n")

        for club in df["StrokeClub"].unique():
            club_data = df[df["StrokeClub"] == club]
            f.write(f"{club} ({len(club_data)} shots):\n")

            if "Measurement_BallSpeed" in df.columns:
            f.write(
                f"  Average Ball Speed: {club_data['Measurement_BallSpeed'].mean():.1f} mph\n"
            )

            if "Measurement_ClubSpeed" in df.columns:
            f.write(
                f"  Average Club Speed: {club_data['Measurement_ClubSpeed'].mean():.1f} mph\n"
            )

            if "Measurement_SmashFactor" in df.columns:
            f.write(
                f"  Average Smash Factor: {club_data['Measurement_SmashFactor'].mean():.2f}\n"
            )

            if "Measurement_Carry" in df.columns:
            f.write(
                f"  Average Carry Distance: {club_data['Measurement_Carry'].mean():.1f} yards\n"
            )

            if "Measurement_Total" in df.columns:
            f.write(
                f"  Average Total Distance: {club_data['Measurement_Total'].mean():.1f} yards\n"
            )

            if "Measurement_LaunchAngle" in df.columns:
            f.write(
                f"  Average Launch Angle: {club_data['Measurement_LaunchAngle'].mean():.1f} degrees\n"
            )

            if "Measurement_SpinRate" in df.columns:
            f.write(
                    f"  Average Spin Rate: {club_data['Measurement_SpinRate'].mean():.0f} rpm\n"
            )

            f.write("\n")

        f.write("SHOT DISPERSION ANALYSIS\n")
        f.write("------------------------\n\n")

        for club in df["StrokeClub"].unique():
            club_data = df[df["StrokeClub"] == club]
            f.write(f"{club}:\n")

            if "Measurement_CarrySide" in df.columns:
            f.write(
                f"  Average Side Carry: {club_data['Measurement_CarrySide'].mean():.1f} yards\n"
            )
            f.write(
                f"  Side Carry Standard Deviation: {club_data['Measurement_CarrySide'].std():.1f} yards\n"
            )

            if "Measurement_ClubPath" in df.columns:
            f.write(
                f"  Average Club Path: {club_data['Measurement_ClubPath'].mean():.1f} degrees\n"
            )

            if "Measurement_FaceAngle" in df.columns:
            f.write(
                    f"  Average Face Angle: {club_data['Measurement_FaceAngle'].mean():.1f} degrees\n"
                )

            f.write("\n")

    print(f"Analysis report saved to {report_file}")


def show_menu():
    """Show the main menu."""
    print("\nTRACKMAN DATA ANALYSIS")
    print("=====================")
    print("1. Analyze all data")
    print("2. Analyze specific club")
    print("3. Visualize club data")
    print("4. Performance trends over time")
    print("5. Analyze Trackman Combine data")
    print("6. Visualize Trackman Combine data")
    print("7. Exit")

    choice = input("\nEnter your choice (1-7): ").strip()
    return choice


def main():
    """Main function."""
    # Ensure directories exist
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    os.makedirs(VISUALIZATIONS_DIR, exist_ok=True)
    os.makedirs(ANALYSIS_DIR, exist_ok=True)

    while True:
        choice = show_menu()

        if choice == "1":
            analyze_club_data()
        elif choice == "2":
            club = input("Enter club name: ").strip()
            analyze_club_data(club)
        elif choice == "3":
            club_choice = (
                input("Visualize data for a specific club? (y/n): ").strip().lower()
            )
            if club_choice == "y":
                club = input("Enter club name: ").strip()
                visualize_club_data(club)
            else:
                visualize_club_data()
        elif choice == "4":
            # Load the combined shot data
            if not os.path.exists(COMBINED_SHOTS):
                print(
                    "No combined shot data found. Please run the data importer first."
                )
                continue

            df = pd.read_csv(COMBINED_SHOTS)
            plot_trends_over_time(df)
        elif choice == "5":
            analyze_combine_data()
        elif choice == "6":
            visualize_combine_data()
        elif choice == "7":
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please try again.")


def create_club_speed_histogram(df, club_name=None):
    """Create a histogram of club speeds."""
    if "Measurement_ClubSpeed" not in df.columns:
        print("Club speed data not found.")
        return

    # Convert club speed from m/s to mph
    df["Measurement_ClubSpeed_mph"] = df["Measurement_ClubSpeed"].apply(
        convert_speed_to_mph
    )

    # Determine which club column to use
    club_column = None
    if "StrokeClub" in df.columns:
        club_column = "StrokeClub"
    elif "GroupClub" in df.columns:
        club_column = "GroupClub"

    # Filter by club if specified
    if club_name:
        if club_column is None:
            print("Club information not found.")
            return
        df = df[df[club_column] == club_name]
        if len(df) == 0:
            print(f"No data found for club: {club_name}")
            return
        title = f"Club Speed Distribution - {club_name}"
    else:
        title = "Club Speed Distribution - All Clubs"

    plt.figure(figsize=(10, 6))

    # Create histogram with mph values
    sns.histplot(df["Measurement_ClubSpeed_mph"].dropna(), kde=True)

    plt.title(title)
    plt.xlabel("Club Speed (mph)")
    plt.ylabel("Frequency")
    plt.grid(True, alpha=0.3)

    # Add mean line
    mean_speed = df["Measurement_ClubSpeed_mph"].mean()
    plt.axvline(
        mean_speed, color="r", linestyle="--", label=f"Mean: {mean_speed:.1f} mph"
    )

    plt.legend()

    # Save the figure
    filename = f"club_speed_{'all' if club_name is None else club_name}.png"
    filepath = os.path.join(VISUALIZATIONS_DIR, filename)
    plt.savefig(filepath)
    print(f"Saved club speed histogram to {filepath}")
    plt.close()


def visualize_club_data(club_name=None):
    """Create visualizations for club data."""
    # Ensure the visualizations directory exists
    os.makedirs(VISUALIZATIONS_DIR, exist_ok=True)

    # Load the combined shot data
    if not os.path.exists(COMBINED_SHOTS):
        print("No combined shot data found. Please run the data importer first.")
        return

    df = pd.read_csv(COMBINED_SHOTS)

    # Create visualizations
    create_club_speed_histogram(df, club_name)

    # If no specific club is selected, also create club performance plots
    if club_name is None:
        plot_club_performance(df)

    print(
        f"Visualizations created for {'all clubs' if club_name is None else club_name}"
    )


def analyze_combine_data():
    """Analyze Trackman Combine data."""
    if not os.path.exists(COMBINE_SHOTS):
        print(f"No combine data found at {COMBINE_SHOTS}")
        return

    df = pd.read_csv(COMBINE_SHOTS)

    # Apply unit conversions to speed measurements
    if "Measurement_ClubSpeed" in df.columns:
        df["Measurement_ClubSpeed_mph"] = df["Measurement_ClubSpeed"].apply(
            convert_speed_to_mph
        )

    if "Measurement_BallSpeed" in df.columns:
        df["Measurement_BallSpeed_mph"] = df["Measurement_BallSpeed"].apply(
            convert_speed_to_mph
        )

    print(f"Analyzing combine data ({len(df)} shots)")

    # Generate summary statistics by target distance
    summary = {}

    # Group by target distance
    if "TargetDistance" in df.columns:
        targets = df["TargetDistance"].unique()
        for target in targets:
            target_data = df[df["TargetDistance"] == target]
            summary[target] = {
                "shots": len(target_data),
                "avg_metrics": {},
            }

            # Calculate average metrics
            for metric in [
                "Measurement_AttackAngle",
                "Measurement_ClubPath",
                "Measurement_ClubSpeed",
                "Measurement_ClubSpeed_mph",  # Added mph version
                "Measurement_FaceAngle",
                "Measurement_LaunchAngle",
                "Measurement_SpinRate",
                "Score",  # Combine-specific
                "DistanceToPin",  # Combine-specific
            ]:
                if metric in target_data.columns:
                    summary[target]["avg_metrics"][metric] = target_data[metric].mean()

            # Calculate club usage
            if "StrokeClub" in target_data.columns:
                clubs = target_data["StrokeClub"].value_counts()
                summary[target]["club_usage"] = clubs.to_dict()

    # Print summary
    print("\nCombine Target Distance Summary:")
    for target in summary:
        print(f"\nTarget: {target} ({summary[target]['shots']} shots):")

        # Print club usage if available
        if "club_usage" in summary[target]:
            print("  Club Usage:")
            for club, count in summary[target]["club_usage"].items():
                if pd.notna(club):  # Check if club is not NaN
                    print(f"    {club}: {count} shots")

        # Print performance metrics
        print("  Performance Metrics:")
        metrics = summary[target]["avg_metrics"]
        if "Measurement_AttackAngle" in metrics:
            print(f"    Average AttackAngle: {metrics['Measurement_AttackAngle']:.1f}°")
        if "Measurement_ClubPath" in metrics:
            print(f"    Average ClubPath: {metrics['Measurement_ClubPath']:.1f}")
        if "Measurement_ClubSpeed" in metrics:
            print(
                f"    Average Club Speed (raw): {metrics['Measurement_ClubSpeed']:.1f} m/s"
            )
        if "Measurement_ClubSpeed_mph" in metrics:
            print(
                f"    Average Club Speed: {metrics['Measurement_ClubSpeed_mph']:.1f} mph"
            )
        if "Measurement_FaceAngle" in metrics:
            print(f"    Average FaceAngle: {metrics['Measurement_FaceAngle']:.1f}°")
        if "Measurement_LaunchAngle" in metrics:
            print(f"    Average LaunchAngle: {metrics['Measurement_LaunchAngle']:.1f}°")
        if "Measurement_SpinRate" in metrics:
            print(f"    Average SpinRate: {metrics['Measurement_SpinRate']:.0f} rpm")
        if "Score" in metrics:
            print(f"    Average Score: {metrics['Score']:.1f} points")
        if "DistanceToPin" in metrics:
            print(f"    Average Distance to Pin: {metrics['DistanceToPin']:.1f} yards")

    return df


def plot_combine_performance(df):
    """Plot performance metrics for Trackman Combine data."""
    # Ensure the analysis directory exists
    os.makedirs(ANALYSIS_DIR, exist_ok=True)

    # Apply unit conversions to speed measurements
    if "Measurement_ClubSpeed" in df.columns:
        df["Measurement_ClubSpeed_mph"] = df["Measurement_ClubSpeed"].apply(
            convert_speed_to_mph
        )

    if "Measurement_BallSpeed" in df.columns:
        df["Measurement_BallSpeed_mph"] = df["Measurement_BallSpeed"].apply(
            convert_speed_to_mph
        )

    # Create a copy of the dataframe for plotting
    plot_df = df.copy()

    # Extract numeric part from target distance for plotting
    if "TargetDistance" in plot_df.columns:
        # Create a new column for plotting that extracts the numeric part when possible
        def extract_target_value(target_str):
            if pd.isna(target_str):
                return target_str
            if target_str == "D":  # Driver
                return "Driver"
            if ";" in str(target_str):
                parts = str(target_str).split(";")
                if len(parts) == 2 and parts[1].isdigit():
                    return int(parts[1])  # Return the numeric part
            return target_str  # Return as is if we can't extract

        plot_df["TargetValue"] = plot_df["TargetDistance"].apply(extract_target_value)

        # Sort the dataframe by the numeric target value
        try:
            plot_df = plot_df.sort_values("TargetValue")
        except:
            # If sorting fails, continue without sorting
            pass

    # Create a figure with multiple subplots
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle("Combine Performance Metrics by Target Distance", fontsize=16)

    # Plot 1: Ball Speed by Target Distance
    sns.boxplot(
        x="TargetValue", y="Measurement_BallSpeed_mph", data=plot_df, ax=axes[0, 0]
    )
    axes[0, 0].set_title("Ball Speed by Target Distance")
    axes[0, 0].set_xlabel("Target Distance (yards)")
    axes[0, 0].set_ylabel("Ball Speed (mph)")
    axes[0, 0].tick_params(axis="x", rotation=45)

    # Plot 2: Club Speed by Target Distance
    sns.boxplot(
        x="TargetValue", y="Measurement_ClubSpeed_mph", data=plot_df, ax=axes[0, 1]
    )
    axes[0, 1].set_title("Club Speed by Target Distance")
    axes[0, 1].set_xlabel("Target Distance (yards)")
    axes[0, 1].set_ylabel("Club Speed (mph)")
    axes[0, 1].tick_params(axis="x", rotation=45)

    # Plot 3: Launch Angle by Target Distance
    sns.boxplot(
        x="TargetValue", y="Measurement_LaunchAngle", data=plot_df, ax=axes[1, 0]
    )
    axes[1, 0].set_title("Launch Angle by Target Distance")
    axes[1, 0].set_xlabel("Target Distance (yards)")
    axes[1, 0].set_ylabel("Launch Angle (degrees)")
    axes[1, 0].tick_params(axis="x", rotation=45)

    # Plot 4: Spin Rate by Target Distance
    sns.boxplot(x="TargetValue", y="Measurement_SpinRate", data=plot_df, ax=axes[1, 1])
    axes[1, 1].set_title("Spin Rate by Target Distance")
    axes[1, 1].set_xlabel("Target Distance (yards)")
    axes[1, 1].set_ylabel("Spin Rate (rpm)")
    axes[1, 1].tick_params(axis="x", rotation=45)

    plt.tight_layout(rect=(0.05, 0.05, 0.95, 0.95))

    # Save the figure
    plt.savefig(os.path.join(ANALYSIS_DIR, "combine_performance.png"))
    print(
        f"Saved combine performance visualization to {os.path.join(ANALYSIS_DIR, 'combine_performance.png')}"
    )

    plt.close()


def plot_combine_scores_over_time(df):
    """Plot combine scores over time."""
    # Ensure the analysis directory exists
    os.makedirs(ANALYSIS_DIR, exist_ok=True)

    # Check if we have the necessary columns
    if "Date" not in df.columns or "CombineScore" not in df.columns:
        print("Cannot plot combine scores: missing Date or CombineScore columns")
        return

    # Create a copy of the dataframe for plotting
    plot_df = df.copy()

    # Convert Date to datetime
    plot_df["Date"] = pd.to_datetime(plot_df["Date"])

    # Drop rows with missing scores
    plot_df = plot_df.dropna(subset=["CombineScore"])

    if len(plot_df) == 0:
        print("No combine scores found for plotting")
        return

    # Group by date and get the average score for each date
    # This handles cases where there might be multiple scores on the same day
    date_scores = plot_df.groupby("Date")["CombineScore"].mean().reset_index()

    # Sort by date
    date_scores = date_scores.sort_values("Date")

    # Create the plot
    plt.figure(figsize=(12, 6))
    plt.plot(
        date_scores["Date"],
        date_scores["CombineScore"],
        "o-",
        linewidth=2,
        markersize=8,
    )

    # Add labels and title
    plt.xlabel("Date")
    plt.ylabel("Combine Score")
    plt.title("Trackman Combine Scores Over Time")

    # Format the x-axis to show dates nicely
    plt.gcf().autofmt_xdate()

    # Add a grid
    plt.grid(True, linestyle="--", alpha=0.7)

    # Add data labels
    for i, (date, score) in enumerate(
        zip(date_scores["Date"], date_scores["CombineScore"])
    ):
        plt.annotate(
            f"{score:.1f}",
            (date, score),
            textcoords="offset points",
            xytext=(0, 10),
            ha="center",
        )

    # Save the figure
    plt.tight_layout()
    plt.savefig(os.path.join(ANALYSIS_DIR, "combine_scores_over_time.png"))
    print(
        f"Saved combine scores visualization to {os.path.join(ANALYSIS_DIR, 'combine_scores_over_time.png')}"
    )

    plt.close()


def plot_combine_distance_medians(df):
    """
    Create box and whisker plots showing the median scores for each target distance over time.
    Each point in the plot represents the median score for a specific distance across different dates.
    """
    # Ensure the analysis directory exists
    os.makedirs(ANALYSIS_DIR, exist_ok=True)

    # Check if we have the necessary columns
    if "Date" not in df.columns or "Target" not in df.columns:
        print("Cannot plot distance medians: missing Date or Target columns")
        return

    # Create a copy of the dataframe for plotting
    plot_df = df.copy()

    # Convert Date to datetime
    plot_df["Date"] = pd.to_datetime(plot_df["Date"])

    # Extract target values for better visualization
    def extract_target_value(target_str):
        if pd.isna(target_str):
            return target_str
        if target_str == "D":  # Driver
            return "Driver"
        if ";" in str(target_str):
            parts = str(target_str).split(";")
            if len(parts) == 2 and parts[1].isdigit():
                return int(parts[1])  # Return the numeric part
        return target_str  # Return as is if we can't extract

    plot_df["TargetValue"] = plot_df["Target"].apply(extract_target_value)

    # Check if we have any numeric target values
    numeric_targets = [
        t for t in plot_df["TargetValue"].unique() if isinstance(t, (int, float))
    ]
    if not numeric_targets:
        print("No numeric target distances found for plotting")
        return

    # Sort the dataframe by the numeric target value
    try:
        plot_df = plot_df.sort_values("TargetValue")
    except:
        # If sorting fails, continue without sorting
        pass

    # Group by target and date to get performance metrics for each target on each date
    target_metrics = []

    # Check which metrics are available
    available_metrics = []
    for metric in [
        "AvgCarry",
        "AvgBallSpeed",
        "AvgClubSpeed",
        "AvgSpinRate",
        "AvgLaunchAngle",
    ]:
        if metric in plot_df.columns and not plot_df[metric].isna().all():
            available_metrics.append(metric)

    if not available_metrics:
        print("No performance metrics available for plotting")
        return

    # Create a figure with subplots for each metric
    n_metrics = len(available_metrics)
    fig, axes = plt.subplots(n_metrics, 1, figsize=(12, 5 * n_metrics))

    # If only one metric, axes is not an array
    if n_metrics == 1:
        axes = [axes]

    # Plot each metric
    for i, metric in enumerate(available_metrics):
        # Create a boxplot for each target
        sns.boxplot(x="TargetValue", y=metric, data=plot_df, ax=axes[i])

        # Add labels and title
        axes[i].set_title(f"{metric.replace('Avg', '')} by Target Distance")
        axes[i].set_xlabel("Target Distance (yards)")
        axes[i].set_ylabel(metric.replace("Avg", "Median "))

        # Format x-axis
        axes[i].tick_params(axis="x", rotation=45)

        # Add a grid
        axes[i].grid(True, linestyle="--", alpha=0.7)

        # Add median values as text
        for j, target in enumerate(plot_df["TargetValue"].unique()):
            target_data = plot_df[plot_df["TargetValue"] == target]
            if not target_data[metric].isna().all():
                median_val = target_data[metric].median()
                axes[i].annotate(
                    f"{median_val:.1f}",
                    (j, median_val),
                    textcoords="offset points",
                    xytext=(0, 10),
                    ha="center",
                )

    # Adjust layout
    plt.tight_layout()

    # Save the figure
    plt.savefig(os.path.join(ANALYSIS_DIR, "combine_distance_medians.png"))
    print(
        f"Saved combine distance medians visualization to {os.path.join(ANALYSIS_DIR, 'combine_distance_medians.png')}"
    )

    plt.close()


def plot_combine_score_medians_over_time(df):
    """
    Create a time series visualization showing the median scores for each target distance over time.
    For each date and target distance, calculate the median score and display as a line plot.
    """
    # Ensure the analysis directory exists
    os.makedirs(ANALYSIS_DIR, exist_ok=True)

    # Check if we have the necessary columns
    required_columns = ["GroupDate", "Measurement_Score", "GroupTarget"]
    if not all(col in df.columns for col in required_columns):
        print(f"Cannot plot score medians over time: missing one of {required_columns}")
        return

    # Create a copy of the dataframe for plotting
    plot_df = df.copy()

    # Convert Date to datetime
    plot_df["Date"] = pd.to_datetime(plot_df["GroupDate"])

    # Drop rows with missing scores
    plot_df = plot_df.dropna(subset=["Measurement_Score"])

    if len(plot_df) == 0:
        print("No score data found for plotting")
        return

    # Create a target distance column that handles both numeric distances and special cases like Driver
    def get_target_distance(row):
        # First check if we have a numeric length to target
        if pd.notna(row.get("Measurement_LengthToTarget")):
            return round(row["Measurement_LengthToTarget"])

        # If not, check if it's a driver from the GroupTarget
        if pd.notna(row.get("GroupTarget")) and (
            row["GroupTarget"] == "D" or "Driver" in str(row["GroupTarget"])
        ):
            return "Driver"

        # If it's in the S;X format, extract the number
        if pd.notna(row.get("GroupTarget")) and ";" in str(row["GroupTarget"]):
            parts = str(row["GroupTarget"]).split(";")
            if len(parts) == 2 and parts[1].isdigit():
                return int(parts[1])

        # Default fallback
        return None

    # Apply the function to create the target distance column
    plot_df["TargetDistance"] = plot_df.apply(get_target_distance, axis=1)

    # Drop rows with missing target distances
    plot_df = plot_df.dropna(subset=["TargetDistance"])

    # Group by date and target, then calculate median score for each group
    median_scores = (
        plot_df.groupby(["Date", "TargetDistance"])["Measurement_Score"]
        .median()
        .reset_index()
    )

    # Get unique dates and targets
    dates = sorted(median_scores["Date"].unique())

    # If we have too many dates, select a subset to make the visualization clearer
    if len(dates) > 8:
        # Select evenly spaced dates
        indices = np.linspace(0, len(dates) - 1, 8).astype(int)
        selected_dates = [dates[i] for i in indices]
    else:
        selected_dates = dates

    # Get all targets, including both numeric and "Driver"
    all_targets = median_scores["TargetDistance"].unique()

    # Separate numeric and non-numeric targets
    numeric_targets = [t for t in all_targets if isinstance(t, (int, float))]
    non_numeric_targets = [t for t in all_targets if not isinstance(t, (int, float))]

    # Sort numeric targets and combine with non-numeric targets
    sorted_targets = sorted(numeric_targets) + non_numeric_targets

    # Filter to common targets that appear in most dates
    target_counts = median_scores.groupby("TargetDistance").size()
    common_targets = target_counts[target_counts >= len(dates) * 0.4].index.tolist()

    # If we still have too many targets, select the most common ones
    if len(common_targets) > 9:  # Increased from 8 to 9 to potentially include Driver
        # Make sure to include "Driver" if it exists
        if "Driver" in common_targets:
            # Get the 8 most common numeric targets
            numeric_common = [t for t in common_targets if isinstance(t, (int, float))]
            numeric_common = sorted(numeric_common)
            if len(numeric_common) > 8:
                numeric_common = numeric_common[:8]
            common_targets = numeric_common + ["Driver"]
        else:
            common_targets = target_counts.nlargest(9).index.tolist()

    # Sort the common targets (numeric first, then "Driver")
    common_targets = sorted(
        [t for t in common_targets if isinstance(t, (int, float))]
    ) + [t for t in common_targets if not isinstance(t, (int, float))]

    # Filter data to selected dates and common targets
    filtered_data = median_scores[
        (median_scores["Date"].isin(selected_dates))
        & (median_scores["TargetDistance"].isin(common_targets))
    ]

    if len(filtered_data) == 0:
        print("No data available for plotting after filtering")
        return

    # Create a figure with a larger size for better readability
    plt.figure(figsize=(14, 10))

    # Create a color map for different targets - using a colormap that ends with red for highest values
    colors = plt.cm.get_cmap("RdYlBu_r", len(common_targets))

    # Create a subplot grid for small multiples
    num_targets = len(common_targets)
    num_cols = min(3, num_targets)
    num_rows = (num_targets + num_cols - 1) // num_cols  # Ceiling division

    # Create small multiples - one subplot per target distance
    for i, target in enumerate(common_targets):
        ax = plt.subplot(num_rows, num_cols, i + 1)

        # Get data for this target
        target_data = filtered_data[filtered_data["TargetDistance"] == target]

        if len(target_data) > 0:
            # Plot the line
            ax.plot(
                target_data["Date"],
                target_data["Measurement_Score"],
                "o-",
                linewidth=2,
                markersize=8,
                color=colors(i / len(common_targets)),
            )

            # Add data labels
            for date, score in zip(
                target_data["Date"], target_data["Measurement_Score"]
            ):
                ax.annotate(
                    f"{score:.0f}",
                    (date, score),
                    textcoords="offset points",
                    xytext=(0, 5),
                    ha="center",
                    fontsize=9,
                )

        # Set title and labels
        if isinstance(target, (int, float)):
            ax.set_title(f"{target} yards", fontsize=12)
        else:
            ax.set_title(f"{target}", fontsize=12)

        # Format x-axis to show dates nicely
        ax.tick_params(axis="x", rotation=45)

        # Format x-axis dates to be more readable
        date_format = mdates.DateFormatter("%m/%d/%y")
        ax.xaxis.set_major_formatter(date_format)

        # Set y-axis limits consistently across subplots
        all_scores = filtered_data["Measurement_Score"]
        if not all_scores.empty:
            min_score = max(0, all_scores.min() - 10)
            max_score = min(100, all_scores.max() + 10)
            ax.set_ylim(min_score, max_score)

        # Add a grid
        ax.grid(True, linestyle="--", alpha=0.7)

    # Add a common y-label
    plt.figtext(
        0.04, 0.5, "Median Score", va="center", rotation="vertical", fontsize=14
    )

    # Add a common x-label
    plt.figtext(0.5, 0.04, "Date", ha="center", fontsize=14)

    # Add an overall title
    plt.suptitle("Median Scores by Target Distance Over Time", fontsize=16, y=0.98)

    # Adjust layout
    plt.tight_layout(rect=(0.05, 0.05, 0.95, 0.95))

    # Save the figure
    plt.savefig(
        os.path.join(ANALYSIS_DIR, "combine_score_medians_over_time.png"), dpi=150
    )
    print(
        f"Saved combine score medians over time visualization to {os.path.join(ANALYSIS_DIR, 'combine_score_medians_over_time.png')}"
    )

    plt.close()

    # Create a second visualization: heatmap of scores by date and distance
    plt.figure(figsize=(14, 8))

    # Format dates for better readability in the heatmap
    date_strings = [
        d.strftime("%m/%d/%y") for d in sorted(median_scores["Date"].unique())
    ]

    # Pivot the data to create a matrix suitable for a heatmap
    pivot_data = median_scores.pivot(
        index="TargetDistance", columns="Date", values="Measurement_Score"
    )

    # Sort the index by target distance, with "Driver" at the end
    if "Driver" in pivot_data.index:
        numeric_indices = [
            idx for idx in pivot_data.index if isinstance(idx, (int, float))
        ]
        pivot_data = pivot_data.loc[sorted(numeric_indices) + ["Driver"]]
    else:
        pivot_data = pivot_data.sort_index()

    # Create the heatmap
    ax = sns.heatmap(
        pivot_data,
        cmap="RdYlBu_r",
        annot=True,
        fmt=".0f",
        linewidths=0.5,
        cbar_kws={"label": "Median Score"},
    )

    # Set title and labels
    plt.title("Median Scores by Target Distance and Date", fontsize=16)
    plt.xlabel("Date", fontsize=14)
    plt.ylabel("Target Distance (yards)", fontsize=14)

    # Format x-axis to show dates nicely
    plt.xticks(
        np.arange(len(date_strings)) + 0.5,  # Position ticks in the center of cells
        date_strings,
        rotation=45,
        ha="right",
    )

    # Adjust layout
    plt.tight_layout()

    # Save the figure
    plt.savefig(os.path.join(ANALYSIS_DIR, "combine_score_heatmap.png"), dpi=150)
    print(
        f"Saved combine score heatmap to {os.path.join(ANALYSIS_DIR, 'combine_score_heatmap.png')}"
    )

    plt.close()


def visualize_combine_data():
    """Generate visualizations for Trackman Combine data."""
    # Ensure the analysis directory exists
    os.makedirs(ANALYSIS_DIR, exist_ok=True)

    if not os.path.exists(COMBINE_SHOTS):
        print(f"No combine data found at {COMBINE_SHOTS}")
        return

    # Load the data
    df = pd.read_csv(COMBINE_SHOTS)

    # Generate the performance metrics visualization
    plot_combine_performance(df)

    # Load the shot groups data for the scores over time visualization
    if os.path.exists(COMBINE_GROUPS):
        groups_df = pd.read_csv(COMBINE_GROUPS)
        plot_combine_scores_over_time(groups_df)
        plot_combine_distance_medians(groups_df)

        # Generate the new score medians over time visualization
        plot_combine_score_medians_over_time(
            df
        )  # Using the shot data which has individual scores

    print("Combine visualizations created")


if __name__ == "__main__":
    main()
