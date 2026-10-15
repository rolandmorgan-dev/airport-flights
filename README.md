# Airport Flights

A modern PySide6 desktop application for viewing airport arrivals and departures.

## Overview

Airport Flights allows you to select from 9,000 airports worldwide and view their current arrival and departure information. Flight data can be searched, copied, and exported to PDF or TXT files with a single click.

The application features a custom graphical interface, with instant switching between English and Hungarian language.

**[IMAGE 1 — Main application window showing the overall GUI and flight table]**

## Features

- **9,000 Airports** — Select an airport from the available list. The list can be extended by editing `airports.json`.
- **Arrivals and Departures** — View flight information in separate tabs.
- **Search Flights** — Quickly filter the displayed flight data.
- **Copy Data** — Copy flight information from the application.
- **PDF and TXT Export** — Save flight data in either format.
- **English and Hungarian** — Switch languages without restarting the application.
- **Localized Exports** — PDF and TXT files use the currently selected language.
- **Custom GUI** — A modern desktop interface built with PySide6.

## Demo

**[GIF 1 — Short application walkthrough showing airport selection, arrivals/departures, language switching, search, and export]**

## Screenshots

**[IMAGE 2 — Arrivals tab with flight data loaded]**

**[IMAGE 3 — Departures tab with flight data loaded]**

**[IMAGE 4 — Example of an exported PDF or TXT file]**

## Built With

- Python
- PySide6
- FlightRadarAPI — an unofficial Python wrapper for accessing Flightradar24 flight data
- ReportLab — PDF generation

## Project Structure

```text
Airport-Flights/
├── images/          # Application images and assets
├── src/             # JSON configuration files
├── flights.py          # Application entry point
├── LICENSE          # Project license
└── README.md        # Project documentation
```


# Disclaimer

*This project is for educational and portfolio purposes only. It uses an unofficial Python API wrapper to fetch flight data. Flightradar24 AB is the service provider. This project is not affiliated with, endorsed by, or sponsored by Flightradar24.*
