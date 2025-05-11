# Trackman Data Extraction and Analysis Framework

This project provides a framework for extracting, aggregating, and analyzing golf shot data from Trackman reports.

## Overview

The framework consists of three main components:

1. **Data Extraction**: Scripts to extract shot data from Trackman reports via their API
2. **Data Storage**: Organized file-based storage for extracted data
3. **Data Analysis**: Tools for analyzing and visualizing the shot data

## How It Works

### Data Extraction

The extraction process works by:

1. Following redirect links from Trackman emails to the actual report URLs
2. Extracting the report IDs from the URLs
3. Making POST requests to the Trackman API to fetch the report data
4. Parsing the JSON response to extract shot data and metrics

The importer provides a simple interface for:
- Adding individual URLs
- Adding multiple URLs in bulk
- Tracking the status of URL processing
- Handling duplicate reports

### Data Storage

The extracted data is stored in an organized directory structure:

- **Raw Data**: JSON files containing the complete API response
- **Processed Data**: CSV files containing individual shot metrics and shot group data
- **Visualizations**: Generated charts and reports

The system handles:
- Reports with shots that exist in other reports (deduplication)
- Reports with columns that don't exist in previous reports (schema evolution)

### Data Analysis

The analysis component provides:

- Basic statistical analysis of shot metrics
- Visualizations of shot data
- Performance trends over time
- Shot dispersion patterns
- Club path and face angle analysis

## Project Structure

```
trackman-scraper/
├── data/
│   ├── raw/                  # Raw JSON data from the API
│   ├── processed/            # Processed CSV files
│   └── visualizations/       # Generated charts and reports
├── src/
│   ├── trackman_api_scraper.py   # Core API scraping functionality
│   ├── trackman_importer.py      # URL import interface
│   └── trackman_analysis.py      # Data analysis and visualization
├── trackman_app.py           # Main application entry point
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## Getting Started

### Prerequisites

- Python 3.6+
- Required packages: requests, beautifulsoup4, pandas, matplotlib, seaborn

### Installation

1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`

### Usage

Run the main application:

```
python trackman_app.py
```

This will present a menu with options to:
1. Import Trackman Data
2. Analyze Trackman Data

#### Importing Data

The importer provides options to:
- Add a single URL
- Add multiple URLs
- Process pending URLs
- Update combined data files

#### Analyzing Data

The analyzer provides options to:
- Generate all visualizations and reports
- Perform specific analyses (club performance, shot dispersion, etc.)
- Generate a text report with key insights

## Technical Details

### API Endpoints

The Trackman API uses the following endpoints:

- `https://golf-player-activities.trackmangolf.com/api/reports/getreport` - Main endpoint for fetching report data

### Data Structure

The Trackman data is structured as follows:

- Reports contain multiple "StrokeGroups" (sessions with a specific club)
- Each StrokeGroup contains multiple "Strokes" (individual shots)
- Each Stroke contains detailed metrics including:
  - Ball data (speed, launch angle, spin rate, etc.)
  - Club data (club speed, path, face angle, etc.)
  - Impact data (location, dynamic loft, etc.)
  - Result data (carry distance, total distance, etc.)

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Trackman for providing the golf shot data
- The open-source community for the tools and libraries used in this project 