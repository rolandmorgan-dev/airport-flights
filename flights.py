import sys
import os
import json
import time
import traceback
from pathlib import Path
import webbrowser

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QFrame, 
                               QVBoxLayout, QHBoxLayout, QTabWidget, QLabel, 
                               QPushButton, QLineEdit, QTreeWidget, QTreeWidgetItem,
                               QHeaderView, QGraphicsBlurEffect, QMessageBox, QSizeGrip,
                               QCompleter, QToolButton, QMenu)
from PySide6.QtGui import QIcon, QPixmap, QAction
from PySide6.QtCore import Qt, QTimer
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from FlightRadarAPI import FlightRadar24API


def get_real_dir(curr_path):
    if getattr(sys, "frozen", False):
        base_path = Path(sys.executable).parent
    else:
        base_path = Path(__file__).parent
    return str(base_path / curr_path)


def ensure_src_dir():
    src_path = get_real_dir("src")
    if not os.path.exists(src_path):
        os.makedirs(src_path)
    return src_path


# --- Load raw data ---
def load_data():
    fr_api = FlightRadar24API()
    airport = fr_api.get_airport_details(selected_airport_code)
    data = airport["airport"]["pluginData"]
    return data


def get_settings_path():
    return os.path.join(ensure_src_dir(), "settings.json")


def load_settings():
    defaults = {
        "language": "EN",
        "last_refresh": 0,
        "airport_name": "",
        "airport_code": ""
    }

    settings_path = get_settings_path()
    if not os.path.exists(settings_path):
        return defaults.copy()

    try:
        with open(settings_path, "r", encoding="utf-8") as file:
            loaded = json.load(file)
        if not isinstance(loaded, dict):
            return defaults.copy()
        merged = defaults.copy()
        for key, value in loaded.items():
            if key in merged:
                merged[key] = value
        return merged
    except Exception:
        return defaults.copy()


def save_settings():
    settings_path = get_settings_path()
    with open(settings_path, "w", encoding="utf-8") as file:
        json.dump(settings, file, ensure_ascii=False, indent=4)


def save_selected_airport(airport_name, airport_code):
    settings["airport_name"] = airport_name
    settings["airport_code"] = airport_code


def load_selected_airport():
    airport_name = settings.get("airport_name", "")
    airport_code = settings.get("airport_code", "")

    if airport_name and airport_code:
        if airport_name in airports and airports.get(airport_name) == airport_code:
            return airport_name, airport_code
        if airport_code.upper() in {value.upper() for value in airports.values()}:
            for name, code in airports.items():
                if code.upper() == airport_code.upper():
                    return name, code

    return "", ""


# --- Extract from raw data ---
def get_data(curr_data, paths_):
    for pth in paths_:
        temp = curr_data
        try:
            for key in pth:
                temp = temp[key]
        except (KeyError, TypeError, IndexError):
            continue

        if temp and isinstance(temp, (str, int, float)):
            return temp
        else:
            continue
    
    error = ("Nincs adat", "Hibás adat") if trs else ("No data", "Invalid data")
    return error[1] if isinstance(temp, str) else error[0]


### airports globals -> Airport_name : Airport_code ###
airports_path = os.path.join(ensure_src_dir(), "airports.json")

with open(airports_path, "r", encoding="utf-8") as file:
    airports = json.load(file)["Airports"]

del airports_path

settings = load_settings()
selected_airport_name, selected_airport_code = load_selected_airport()

### localization globals ###
localization_path = os.path.join(ensure_src_dir(), "localization.json")

with open(localization_path, "r", encoding="utf-8") as file:
    localization_data = json.load(file)

country_mapping_hu = localization_data["country_mapping_hu"]
ui_lang = localization_data["ui_lang"]
error_values = ("Nincs adat", "Hibás adat", "No data", "Invalid data")
del localization_path, localization_data


### globals trs language bool, False -> Eng, True -> Hun ###
trs = settings.get("language", "EN").upper() == "HU"


def get_local_timezone_name():
    tz_name = datetime.now().astimezone().tzname()
    return tz_name or "Local"


def format_local_time(unix_timestamp):
    if unix_timestamp in error_values:
        return unix_timestamp
    dt = datetime.fromtimestamp(unix_timestamp, tz=timezone.utc).astimezone()
    return dt.strftime("%Y.%m.%d %H:%M")

def get_airport_city_name(data):
    selected_airport_city = (
        ("details", "position", "region", "city"),
        ("details", "position", "city"),
        ("details", "city"),
        ("position", "region", "city"),
        ("position", "city"),
        ("city",))
    
    selected_airport_city = get_data(data, selected_airport_city)
    if selected_airport_city in error_values:
        selected_airport_city = selected_airport_name
    
    return selected_airport_city

def load_departures(data):
    departures = data["schedule"]["departures"]["data"]
    departure_list = []
    selected_airport_city = get_airport_city_name(data)
    for item in departures:
        unix_timestamp = (
            ("flight", "time", "scheduled", "departure", "time"),
            ("flight", "time", "scheduled", "departure"),
            ("flight", "time", "estimated", "departure"),
            ("flight", "time", "estimated", "departure", "time"),
            ("flight", "time", "real", "departure"),
            ("flight", "time", "actual", "departure"),
            ("flight", "time", "departure"),
            ("flight", "time", "timestamp", "departure"),
            ("flight", "time", "real", "departure", "time"),
            ("flight", "time", "actual", "departure", "time"),
            ("time", "scheduled", "departure"),
            ("time", "estimated", "departure"),
        )
        unix_timestamp = get_data(item, unix_timestamp)
        time_value = format_local_time(unix_timestamp)

        flight_number = (
            ("flight", "identification", "number", "default"),
            ("flight", "identification", "number", "default", "text"),
            ("flight", "identification", "callsign"),
            ("flight", "callsign"),
            ("flight", "identification", "number"),
            ("flight", "identification", "number", "registration"),
            ("flight", "identification", "number", "iata"),
        )
        flight_number = get_data(item, flight_number)

        destination = (
            ("flight", "airport", "destination", "position", "region", "city"),
            ("flight", "airport", "destination", "position", "city"),
            ("flight", "airport", "destination", "position", "name"),
            ("flight", "airport", "destination", "name"),
            ("flight", "airport", "destination", "city"),
            ("flight", "airport", "destination"),
        )
        destination = get_data(item, destination)
        if destination not in error_values:
            destination = f"{selected_airport_city} -> {destination}"

        country = (
            ("flight", "airport", "destination", "position", "country", "name"),
            ("flight", "airport", "destination", "position", "country"),
            ("flight", "airport", "destination", "position", "country", "code"),
            ("flight", "airport", "destination", "country"),
            ("flight", "airport", "destination", "position", "country", "short"),
        )
        country = get_data(item, country)
        if trs:
            country = country_mapping_hu.get(country, country)

        airline = (
            ("flight", "airline", "name"),
            ("flight", "owner", "name"),
            ("flight", "airline", "short"),
            ("flight", "airline", "code"),
            ("flight", "owner", "company"),
            ("flight", "callsign"),
        )
        airline = get_data(item, airline)

        aircraft_type = (
            ("flight", "aircraft", "model", "text"),
            ("flight", "aircraft", "model", "code"),
            ("flight", "aircraft", "model", "name"),
            ("flight", "aircraft", "type", "text"),
            ("flight", "aircraft", "type"),
            ("flight", "aircraft", "registration"),
            ("flight", "aircraft", "model"),
        )
        aircraft_type = get_data(item, aircraft_type)

        status_value = (
            ("flight", "status", "text"),
            ("flight", "status"),
            ("flight", "status", "category"),
            ("flight", "status", "long"),
            ("flight", "status", "description"),
            ("status", "text"),
            ("status",),
        )
        translated_status = get_data(item, status_value)

        status_translation_map = (
            ("Scheduled", "Ütemezve"),
            ("Estimated dep", "Várható"),
            ("Estimated departure", "Várható"),
            ("Estimated", "Várható"),
            ("Departed", "Felszállt"),
            ("Landed", "Földet ért"),
            ("Arrived", "Beérkezett"),
            ("Delayed", "Késik"),
            ("Canceled", "Törölve"),
            ("Diverted", "Átirányítva"))

        if trs:
            for english_text, hungarian_text in status_translation_map:
                translated_status = translated_status.replace(english_text, hungarian_text)

        departure_list.append({
            "time": time_value,
            "id": flight_number,
            "to": destination,
            "country": country,
            "airline": airline,
            "type": aircraft_type,
            "status": translated_status
            })
    return departure_list


def load_arrivals(data):
    arrivals = data["schedule"]["arrivals"]["data"]
    arrival_list = []
    selected_airport_city = get_airport_city_name(data)
    for item in arrivals:
        unix_timestamp = (
            ("flight", "time", "scheduled", "arrival"),
            ("flight", "time", "estimated", "arrival"),
            ("flight", "time", "estimated", "arrival", "time"),
            ("flight", "time", "real", "arrival"),
            ("flight", "time", "actual", "arrival"),
            ("flight", "time", "arrival"),
            ("flight", "time", "timestamp", "arrival"),
            ("flight", "time", "real", "arrival", "time"),
            ("flight", "time", "actual", "arrival", "time"),
            ("time", "scheduled", "arrival"),
            ("time", "estimated", "arrival"),
        )
        unix_timestamp = get_data(item, unix_timestamp)
        time_value = format_local_time(unix_timestamp)

        flight_number = (
            ("flight", "identification", "number", "default"),
            ("flight", "identification", "number", "default", "text"),
            ("flight", "identification", "callsign"),
            ("flight", "callsign"),
            ("flight", "identification", "number"),
            ("flight", "identification", "number", "registration"),
            ("flight", "identification", "number", "iata"),
        )
        flight_number = get_data(item, flight_number)

        origin = (
            ("flight", "airport", "origin", "position", "region", "city"),
            ("flight", "airport", "origin", "position", "city"),
            ("flight", "airport", "origin", "position", "name"),
            ("flight", "airport", "origin", "name"),
            ("flight", "airport", "origin", "city"),
            ("flight", "airport", "origin"),
        )
        origin = get_data(item, origin)
        if origin not in error_values:
            origin = f"{selected_airport_city} <- {origin}"

        country = (
            ("flight", "airport", "origin", "position", "country", "name"),
            ("flight", "airport", "origin", "position", "country"),
            ("flight", "airport", "origin", "position", "country", "code"),
            ("flight", "airport", "origin", "country"),
            ("flight", "airport", "origin", "position", "country", "short"),
        )
        country = get_data(item, country)
        if trs:
            country = country_mapping_hu.get(country, country)

        airline = (
            ("flight", "airline", "name"),
            ("flight", "owner", "name"),
            ("flight", "airline", "short"),
            ("flight", "airline", "code"),
            ("flight", "owner", "company"),
            ("flight", "callsign"),
        )
        airline = get_data(item, airline)

        aircraft_type = (
            ("flight", "aircraft", "model", "text"),
            ("flight", "aircraft", "model", "code"),
            ("flight", "aircraft", "model", "name"),
            ("flight", "aircraft", "type", "text"),
            ("flight", "aircraft", "type"),
            ("flight", "aircraft", "registration"),
            ("flight", "aircraft", "model"),
        )
        aircraft_type = get_data(item, aircraft_type)

        status_value = (
            ("flight", "status", "text"),
            ("flight", "status"),
            ("flight", "status", "category"),
            ("flight", "status", "long"),
            ("flight", "status", "description"),
            ("status", "text"),
            ("status",),
        )
        translated_status = get_data(item, status_value)

        status_translation_map = (
            ("Scheduled", "Ütemezve"),
            ("Estimated dep", "Várható"),
            ("Estimated departure", "Várható"),
            ("Estimated", "Várható"),
            ("Departed", "Felszállt"),
            ("Landed", "Földet ért"),
            ("Arrived", "Beérkezett"),
            ("Delayed", "Késik"),
            ("Canceled", "Törölve"),
            ("Diverted", "Átirányítva"))

        if trs:
            for english_text, hungarian_text in status_translation_map:
                translated_status = translated_status.replace(english_text, hungarian_text)

        arrival_list.append({
            "time": time_value,
            "id": flight_number,
            "from": origin,
            "country": country,
            "airline": airline,
            "type": aircraft_type,
            "status": translated_status
            })
    return arrival_list


class FlightMonitor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.data = None
        
        self.icon_path = get_real_dir("images/gui_airplane.ico")
        self.setWindowIcon(QIcon(self.icon_path))
        self.setWindowTitle(ui_lang["program_name"][trs])
        
        screen = QApplication.primaryScreen().availableGeometry()
        # Safe limits for older hardware
        window_height = min(int(screen.height() * 0.8), 750)
        window_width = min(int(screen.width() * 0.9), 1075)

        self.resize(window_width, window_height)
        self.move(screen.center() - self.rect().center())

        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.bg_label = QLabel(self)
        pix = QPixmap(get_real_dir("images/bg_airplane.jpg"))
        if not pix.isNull():
            self.bg_label.setPixmap(pix)
            self.bg_label.setScaledContents(True)
            blur = QGraphicsBlurEffect()
            blur.setBlurRadius(25)
            self.bg_label.setGraphicsEffect(blur)
            self.bg_label.lower()

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.setup_title_bar()
        
        self.content_area = QWidget()
        self.content_area.setObjectName("MainContent")
        
        # Updated: more transparent background (160) and lighter headers
        self.content_area.setStyleSheet("""
            QWidget#MainContent { 
                background: rgba(20, 30, 45, 160); 
                border-bottom-left-radius: 15px; 
                border-bottom-right-radius: 15px; 
            }
            QTabWidget::pane { border: 1px solid rgba(255,255,255,15); background: transparent; }
            QTabBar::tab { 
                background: rgba(40, 40, 40, 150); 
                color: #ddd; 
                padding: 10px 20px; 
                border-top-left-radius: 8px; 
                border-top-right-radius: 8px; 
                margin-right: 2px; 
            }
            QTabBar::tab:selected { background: rgba(52, 152, 219, 180); color: white; }
            QTreeWidget { 
                background: transparent; 
                border: none; 
                color: white; 
                alternate-background-color: rgba(255,255,255,5); 
            }
            QHeaderView::section { 
                background: rgba(60, 60, 60, 180); 
                color: white; 
                padding: 6px; 
                border: 0.5px solid rgba(255,255,255,20); 
                font-weight: bold;
            }
        """)
        
        self.h_layout = QHBoxLayout(self.content_area)
        self.setup_tabs()
        self.setup_side_panel()
        
        self.main_layout.addWidget(self.content_area)
        
        # Add a QSizeGrip so a frameless window can be resized with the mouse
        self.size_grip = QSizeGrip(self)
        # Reduce the visual footprint so it won't cover nearby buttons
        self.size_grip.setFixedSize(18, 18)
        self.size_grip.setVisible(True)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_countdown)
        self.remaining_time = 0
        self._old_pos = None
        
        self.tabs.currentChanged.connect(self.tab_changed_rename_trigger)
        
        self.check_last_refresh_on_startup()

    def tab_changed_rename_trigger(self):
        current_tab = self.tabs.tabText(self.tabs.currentIndex())
        self.btn_open_flightradar.setText(f"{ui_lang['open_website'][trs]}({current_tab})")

    def populate_airport_selector(self):
        airport_names = sorted(airports.keys())
        self.airport_completer = QCompleter(airport_names, self)
        self.airport_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.airport_completer.setCompletionMode(QCompleter.PopupCompletion)
        self.airport_completer.setFilterMode(Qt.MatchContains)
        self.airport_completer.setModelSorting(QCompleter.CaseInsensitivelySortedModel)
        self.airport_completer.activated.connect(self.apply_selected_airport)

        popup = self.airport_completer.popup()
        popup.setMinimumWidth(420)
        popup.setAlternatingRowColors(False)
        popup.setUniformItemSizes(True)
        popup.setViewportMargins(0, 0, 0, 0)
        popup.setContentsMargins(0, 0, 0, 0)
        popup.setStyleSheet("""
            QListView {
                background: rgba(17, 26, 38, 235);
                color: white;
                border: 1px solid rgba(255,255,255,15);
                selection-background-color: rgba(67, 132, 255, 180);
                selection-color: white;
                outline: none;
                padding: 0px;
                margin: 0px;
                spacing: 0px;
            }
            QListView::item {
                padding: 6px 10px;
                margin: 0px;
                border: none;
                background: transparent;
                min-height: 24px;
            }
            QListView::item:selected {
                background: rgba(67, 132, 255, 180);
                color: white;
            }
            QScrollBar:vertical {
                background: rgba(26, 38, 52, 220);
                width: 12px;
                border: none;
                border-radius: 6px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(135, 185, 255, 200);
                border-radius: 6px;
                min-height: 28px;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
        """)
        popup.verticalScrollBar().setSingleStep(12)
        popup.verticalScrollBar().setPageStep(24)

        self.airport_search.setCompleter(self.airport_completer)
        self.airport_search.setText(selected_airport_name)

    def apply_selected_airport(self, airport_name):
        airport_name = str(airport_name).strip()
        if not airport_name or airport_name not in airports:
            self.update_refresh_button_state()
            return

        global selected_airport_name, selected_airport_code
        selected_airport_name = airport_name
        selected_airport_code = airports[airport_name]
        save_selected_airport(selected_airport_name, selected_airport_code)
        self.airport_search.setText(selected_airport_name)
        self.update_refresh_button_state()

    def update_refresh_button_state(self):
        has_code = bool(selected_airport_code and selected_airport_code.strip())
        cooldown_active = getattr(self, 'remaining_time', 0) > 0
        is_ready = has_code and not cooldown_active

        # ensure the button stays disabled during cooldown even after airport changes
        self.btn_refresh.setEnabled(is_ready)
        if is_ready:
            self.btn_refresh.setStyleSheet("background-color: rgba(46, 204, 113, 140);")
        else:
            # if a cooldown is active, always show the countdown text (prevents flash)
            if cooldown_active:
                self.btn_refresh.setStyleSheet("background-color: #444444; color: #bbbbbb; border: 1px solid #555555;")
                try:
                    self.btn_refresh.setText(f"{ui_lang['wait'][trs]} ({self.remaining_time}s)")
                except Exception:
                    # fallback to generic load text if something goes wrong
                    self.btn_refresh.setText(ui_lang["load"][trs])
            else:
                self.btn_refresh.setStyleSheet("background-color: #444444; color: #bbbbbb; border: 1px solid #555555;")
                self.btn_refresh.setText(ui_lang["load"][trs])

        if hasattr(self, 'btn_open_flightradar'):
            self.update_open_flightradar_button_state()

    def update_open_flightradar_button_state(self):
        is_ready = bool(selected_airport_code and selected_airport_code.strip())
        self.btn_open_flightradar.setEnabled(is_ready)
        if is_ready:
            self.btn_open_flightradar.setStyleSheet("background-color: rgba(120,120,120,220); color: white; border-radius: 8px; padding: 10px; font-weight: bold;")
        else:
            self.btn_open_flightradar.setStyleSheet("background-color: rgba(80,80,80,180); color: rgba(255,255,255,120); border: 1px solid rgba(255,255,255,18); border-radius: 8px; padding: 10px; font-weight: bold;")
        self.tab_changed_rename_trigger()

    def open_airport_popup(self):
        if hasattr(self, 'airport_completer'):
            self.airport_search.setFocus()
            self.airport_search.setText(self.airport_search.text())
            self.airport_completer.complete()

    def handle_airport_search(self):
        global selected_airport_name, selected_airport_code
        text = self.airport_search.text().strip()
        if not text:
            selected_airport_name = ""
            selected_airport_code = ""
            save_selected_airport(selected_airport_name, selected_airport_code)
            self.update_refresh_button_state()
            return
        if text in airports:
            self.apply_selected_airport(text)
        elif text and text.lower() in [name.lower() for name in airports]:
            for airport_name in sorted(airports.keys()):
                if airport_name.lower() == text.lower():
                    self.apply_selected_airport(airport_name)
                    break
        else:
            self.airport_completer.setCompletionPrefix(text)
            self.airport_completer.complete()

    def open_flightradar(self):
        try:
            current = self.tabs.tabText(self.tabs.currentIndex())
        except Exception:
            current = ""
        airport_code = selected_airport_code.lower()
        if current in ("Érkezés", "Arrivals"):
            url = f"https://www.flightradar24.com/data/airports/{airport_code}/arrivals"
        else:
            url = f"https://www.flightradar24.com/data/airports/{airport_code}/departures"
        try:
            webbrowser.open(url)
        except Exception as e:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle(ui_lang["error"][trs])
            msg.setText(f"{ui_lang['browser_open_error'][trs]} {e}")
            msg.exec()

    def set_language(self, is_hungarian):
        global trs
        trs = bool(is_hungarian)
        settings["language"] = "HU" if trs else "EN"

        self.eng_button.setChecked(not trs)
        self.hun_button.setChecked(trs)

        # Taskbar title
        self.setWindowTitle(ui_lang["program_name"][trs])
        # Window title
        self.window_title.setText(ui_lang["program_name"][trs])

        # Tables & tabs
        self.headers_arrivals = ui_lang["headers_arrivals"][trs]
        self.headers_departures = ui_lang["headers_departures"][trs]
        self.table_arrivals.setHeaderLabels(self.headers_arrivals)
        self.table_departures.setHeaderLabels(self.headers_departures)
        self.tabs.setTabText(0, ui_lang["arrivals"][trs])
        self.tabs.setTabText(1, ui_lang["departures"][trs])

        # Side buttons & text
        if self.remaining_time:
            self.btn_refresh.setText(f"{ui_lang['wait'][trs]} ({self.remaining_time}s)")
        else:
            self.btn_refresh.setText(ui_lang["load"][trs])

        self.airport_search.setPlaceholderText(ui_lang["airport_placeholder"][trs])
        self.search_label.setText(ui_lang["search"][trs])
        self.search_input.setPlaceholderText(ui_lang["search_placeholder"][trs])
        self.export_label.setText(ui_lang["export"][trs])
        self.save_input.setPlaceholderText(ui_lang["save_filename"][trs])
        self.btn_save_txt.setText(ui_lang["save_txt"][trs])
        self.btn_save_pdf.setText(ui_lang["save_pdf"][trs])
        self.tab_changed_rename_trigger()
        self.btn_exit.setText(ui_lang["exit"][trs])

    def setup_title_bar(self):
        self.title_bar = QFrame()
        self.title_bar.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1e3c72, stop:1 #2a5298);
                border-top-left-radius: 15px;
                border-top-right-radius: 15px;
            }
            QLabel { color: white; font-weight: bold; }
            QPushButton { background: transparent; color: white; font-size: 18px; border: none; width: 45px; }
            QPushButton:hover { background: rgba(255,255,255,30); }

            QFrame#languageToggle {
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px 6px 0px 0px;
            }
            QFrame#languageToggle > QPushButton {
                background: transparent;
                color: rgba(255,255,255,180);
                font-size: 10px;
                font-weight: bold;
                min-width: 52px;
                min-height: 22px;
                margin: 0px;
                padding: 0px 4px;
            }
            QFrame#languageToggle > QPushButton:checked {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #6bb9ff, stop:1 #2d7ae6);
                color: white;
            }
            QPushButton#engButton {
                border-top-left-radius: 7px;
                border-bottom-left-radius: 7px;
                border-top-right-radius: 0px;
                border-bottom-right-radius: 0px;
            }
            QPushButton#hunButton {
                border-top-left-radius: 0px;
                border-bottom-left-radius: 0px;
                border-top-right-radius: 7px;
                border-bottom-right-radius: 7px;
                margin-right: 2px;
            }
            QPushButton#engButton:checked,
            QPushButton#hunButton:checked {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #6bb9ff, stop:1 #2d7ae6);
            }
            QPushButton#engButton:unchecked,
            QPushButton#hunButton:unchecked {
                background: transparent;
            }
            QLineEdit {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(18, 42, 72, 180),
                    stop:1 rgba(10, 26, 44, 170));
                color: white;
                border: 1px solid rgba(146, 202, 255, 190);
                border-radius: 8px;
                padding: 2px 10px;
                selection-background-color: rgba(88, 154, 255, 180);
            }
            QLineEdit:focus {
                border: 1px solid rgba(173, 219, 255, 240);
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(23, 54, 92, 200),
                    stop:1 rgba(12, 30, 52, 180));
            }
            QToolButton {
                background: rgba(255,255,255,8);
                border: 1px solid rgba(255,255,255,22);
                border-radius: 7px;
                color: white;
                font-size: 12px;
                padding: 0px;
            }
            QToolButton:hover {
                background: rgba(255,255,255,16);
            }
        """)
        layout = QHBoxLayout(self.title_bar)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(8)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(QIcon(self.icon_path).pixmap(24, 24))
        layout.addWidget(icon_lbl)

        self.window_title = QLabel(ui_lang["program_name"][trs])
        self.window_title.setStyleSheet("background: transparent; color: white; font-weight: bold; border: none; padding: 0px; margin: 0px;")
        layout.addWidget(self.window_title)

        layout.addStretch(1)

        self.airport_search_container = QWidget()
        self.airport_search_container.setObjectName("airportSearchContainer")
        self.airport_search_container.setStyleSheet("""
            QWidget#airportSearchContainer {
                background: rgba(13, 30, 52, 160);
                border: 1px solid rgba(146, 202, 255, 220);
                border-radius: 9px;
                padding: 0px;
            }
        """)
        self.airport_search_layout = QHBoxLayout(self.airport_search_container)
        self.airport_search_layout.setContentsMargins(4, 2, 4, 2)
        self.airport_search_layout.setSpacing(4)

        self.airport_search = QLineEdit()
        self.airport_search.setMinimumWidth(285)
        self.airport_search.setMaximumWidth(420)
        self.airport_search.setPlaceholderText(ui_lang["airport_placeholder"][trs])
        self.airport_search.setClearButtonEnabled(False)
        self.airport_search.setStyleSheet("""
            QLineEdit {
                background: transparent;
                color: white;
                border: none;
                border-radius: 0px;
                padding: 0px 8px;
                min-height: 24px;
                max-height: 24px;
                selection-background-color: rgba(88, 154, 255, 180);
            }
            QLineEdit:focus {
                background: transparent;
                border: none;
            }
        """)
        self.airport_search.returnPressed.connect(self.handle_airport_search)
        self.airport_search.textEdited.connect(
            lambda text: self.airport_completer.setCompletionPrefix(text)
            if hasattr(self, "airport_completer") else None
        )

        self.airport_dropdown_button = QToolButton()
        self.airport_dropdown_button.setText("▼")
        self.airport_dropdown_button.setMinimumSize(18, 18)
        self.airport_dropdown_button.setMaximumSize(22, 22)
        self.airport_dropdown_button.setCursor(Qt.PointingHandCursor)
        self.airport_dropdown_button.setToolTip("Open airport list")
        self.airport_dropdown_button.clicked.connect(self.open_airport_popup)
        self.airport_dropdown_button.setStyleSheet("""
            QToolButton {
                background: rgba(255,255,255,8);
                border: 1px solid rgba(255,255,255,22);
                border-radius: 7px;
                color: white;
                font-size: 12px;
                font-weight: bold;
            }
            QToolButton:hover {
                background: rgba(255,255,255,16);
            }
        """)

        self.airport_search_layout.addWidget(self.airport_search)
        self.airport_search_layout.addWidget(self.airport_dropdown_button)
        self.populate_airport_selector()
        layout.addWidget(self.airport_search_container)
        layout.addStretch(1)

        self.language_toggle = QFrame()
        self.language_toggle.setObjectName("languageToggle")
        self.language_toggle.setFixedHeight(30)
        self.language_toggle.setFixedWidth(112)
        language_layout = QHBoxLayout(self.language_toggle)
        language_layout.setContentsMargins(0, 0, 0, 0)
        language_layout.setSpacing(0)

        self.eng_button = QPushButton("ENG")
        self.hun_button = QPushButton("HUN")
        self.eng_button.setObjectName("engButton")
        self.hun_button.setObjectName("hunButton")
        self.eng_button.setCheckable(True)
        self.hun_button.setCheckable(True)
        self.eng_button.clicked.connect(lambda: self.set_language(False))
        self.hun_button.clicked.connect(lambda: self.set_language(True))
        language_layout.addWidget(self.eng_button)
        language_layout.addWidget(self.hun_button)
        layout.addWidget(self.language_toggle)
        layout.addSpacing(6)
        self.eng_button.setChecked(not trs)
        self.hun_button.setChecked(trs)

        btn_min = QPushButton("–")
        btn_min.clicked.connect(self.showMinimized)
        self.btn_max = QPushButton("▢")
        self.btn_max.clicked.connect(self.toggle_maximize)
        btn_close = QPushButton("✕")
        btn_close.clicked.connect(self.close)

        layout.addWidget(btn_min)
        layout.addWidget(self.btn_max)
        layout.addWidget(btn_close)
        self.main_layout.addWidget(self.title_bar)

    def setup_tabs(self):
        self.tabs = QTabWidget()

        self.headers_arrivals = ui_lang["headers_arrivals"][trs]
        self.headers_departures = ui_lang["headers_departures"][trs]

        self.table_arrivals = self.create_tree(self.headers_arrivals)
        self.table_departures = self.create_tree(self.headers_departures)

        self.tabs.addTab(self.table_arrivals, ui_lang["arrivals"][trs])
        self.tabs.addTab(self.table_departures, ui_lang["departures"][trs])

        self.h_layout.addWidget(self.tabs, stretch=1)

    def copy_table_value(self, table, item, column):
        if item is None:
            return
        text = item.text(column) if column >= 0 else "\n".join(item.text(i) for i in range(table.columnCount()))
        if text:
            QApplication.clipboard().setText(text)

    def show_table_context_menu(self, pos):
        table = self.sender()
        item = table.itemAt(pos)
        if item is None:
            return

        table.clearSelection()
        table.setCurrentItem(item)
        table.setFocus()

        column = table.columnAt(pos.x())
        menu = QMenu(table)
        menu.setStyleSheet("""
            QMenu {
                background: rgba(14, 25, 36, 220);
                border: 1px solid rgba(255,255,255,20);
                border-radius: 10px;
                padding: 6px;
                color: white;
            }
            QAction {
                background: transparent;
                color: white;
                padding: 8px 14px;
                border-radius: 6px;
            }
            QAction:hover {
                background: rgba(88, 154, 255, 180);
            }
        """)
        action = QAction("Copy", table)
        action.triggered.connect(lambda: self.copy_table_value(table, item, column))
        menu.addAction(action)
        menu.exec(table.viewport().mapToGlobal(pos))

    def create_tree(self, headers):
        tree = QTreeWidget()
        tree.setColumnCount(len(headers))
        tree.setHeaderLabels(headers)
        tree.setContextMenuPolicy(Qt.CustomContextMenu)
        tree.customContextMenuRequested.connect(self.show_table_context_menu)
        
        header = tree.header()
        
        # 2. 100-POINT COLUMN DISTRIBUTION
        # Total: 100 (as a percentage)
        # Time, Flight, Destination/Departure, Country, Airline, Type, Status
        stretch_factors = [15, 8, 19, 14, 14, 17, 13]
        
        # Calculate the available width (roughly window width - sidebar)
        available_width = self.width() - 250 

        for i, factor in enumerate(stretch_factors):
            # Calculate the initial pixel width from the percentage value
            col_width = int((available_width * factor) / 100)
            tree.setColumnWidth(i, col_width)
            # Allow the user to resize the column if desired
            header.setSectionResizeMode(i, QHeaderView.Interactive)
            
        header.setStretchLastSection(True)
        return tree

    def setup_side_panel(self):
        self.side_panel = QFrame()
        self.side_panel.setFixedWidth(200)
        self.side_panel.setStyleSheet("""
            QPushButton { border-radius: 8px; padding: 10px; color: white; font-weight: bold; }
            QLineEdit { background: rgba(255,255,255,15); border: 1px solid rgba(255,255,255,30); color: white; padding: 8px; border-radius: 5px; }
            QLabel { color: #ccc; font-size: 11px; margin-top: 10px; font-weight: bold; }
        """)
        v_layout = QVBoxLayout(self.side_panel)

        self.btn_refresh = QPushButton(ui_lang["load"][trs])
        self.btn_refresh.setEnabled(False)
        self.btn_refresh.setStyleSheet("background-color: #444444; color: #bbbbbb; border: 1px solid #555555;")
        self.btn_refresh.clicked.connect(self.handle_refresh)
        v_layout.addWidget(self.btn_refresh)
        self.update_refresh_button_state()

        self.search_label = QLabel(ui_lang["search"][trs])
        v_layout.addWidget(self.search_label)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(ui_lang["search_placeholder"][trs])
        self.search_input.textChanged.connect(self.search_data)
        v_layout.addWidget(self.search_input)
        v_layout.addStretch(1)

        self.export_label = QLabel(ui_lang["export"][trs])
        v_layout.addWidget(self.export_label)
        self.save_input = QLineEdit()
        self.save_input.setPlaceholderText(ui_lang["save_filename"][trs])
        v_layout.addWidget(self.save_input)

        self.btn_save_txt = QPushButton(ui_lang["save_txt"][trs])
        self.btn_save_txt.setStyleSheet("background-color: rgba(52, 152, 219, 140);")
        self.btn_save_txt.clicked.connect(lambda: self.export_data("txt"))
        v_layout.addWidget(self.btn_save_txt)

        self.btn_save_pdf = QPushButton(ui_lang["save_pdf"][trs])
        self.btn_save_pdf.setStyleSheet("background-color: rgba(155, 89, 182, 140);")
        self.btn_save_pdf.clicked.connect(lambda: self.export_data("pdf"))
        v_layout.addWidget(self.btn_save_pdf)
        v_layout.addStretch(3)
        

        # Button to open Flightradar (modern gray styling)
        current_tab = self.tabs.tabText(self.tabs.currentIndex())
        self.btn_open_flightradar = QPushButton(f"{ui_lang['open_website'][trs]}({current_tab})")
        self.btn_open_flightradar.setStyleSheet("background-color: rgba(120,120,120,220); color: white; border-radius: 8px; padding: 10px; font-weight: bold;")
        self.btn_open_flightradar.clicked.connect(self.open_flightradar)
        v_layout.addWidget(self.btn_open_flightradar)
        self.update_open_flightradar_button_state()

        self.btn_exit = QPushButton(ui_lang["exit"][trs])
        self.btn_exit.setStyleSheet("background-color: rgba(231, 76, 60, 180);")
        self.btn_exit.clicked.connect(self.close)
        v_layout.addWidget(self.btn_exit)
        self.h_layout.addWidget(self.side_panel)

    def check_last_refresh_on_startup(self):
        last_time = float(settings.get("last_refresh", 0) or 0)
        elapsed = int(time.time() - last_time)
        if elapsed < 15:
            self.start_cooldown(15 - elapsed)

    def handle_refresh(self):
        settings["last_refresh"] = time.time()
        self.data = load_data()
        self.populate_table(self.table_arrivals, load_arrivals(self.data), "from")
        self.populate_table(self.table_departures, load_departures(self.data), "to")
        self.start_cooldown(15)

    def start_cooldown(self, seconds):
        self.remaining_time = seconds
        self.btn_refresh.setEnabled(False)
        self.btn_refresh.setStyleSheet("background-color: #444444; color: #bbbbbb; border: 1px solid #555555;")
        self.btn_refresh.setText(f"{ui_lang['wait'][trs]} ({self.remaining_time}s)")
        self.timer.start(1000)

    def update_countdown(self):
        self.remaining_time -= 1
        self.btn_refresh.setText(f"{ui_lang['wait'][trs]} ({self.remaining_time}s)")
        if self.remaining_time <= 0:
            self.timer.stop()
            self.btn_refresh.setEnabled(True)
            self.btn_refresh.setText(ui_lang["load"][trs])
            self.btn_refresh.setStyleSheet("background-color: rgba(46, 204, 113, 140);")

    def export_data(self, mode):
        active_table = self.tabs.currentWidget()
        name = self.save_input.text().strip() or ui_lang["flight_data"][trs]
        desktop_path = Path.home() / "Desktop"
        file_path = desktop_path / f"{name}.{mode}"

        if mode == "txt":
            self.save_txt(active_table, file_path)
        else:
            self.save_official_pdf(active_table, file_path)

    def save_txt(self, table, path):
        airport_label = selected_airport_name or "www.flightradar24.com"
        current_local_time = datetime.now().astimezone().strftime("%Y.%m.%d %H:%M")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"{ui_lang['source'][trs]}: {airport_label}\n")
                f.write(f"{current_local_time}\n")
                headers = [table.headerItem().text(c) for c in range(table.columnCount())]
                f.write(" | ".join(headers) + "\n")
                f.write("-" * 100 + "\n")
                for i in range(table.topLevelItemCount()):
                    item = table.topLevelItem(i)
                    if not item.isHidden():
                        row = [item.text(c) for c in range(table.columnCount())]
                        f.write(" | ".join(row) + "\n")
        except: pass

    def save_official_pdf(self, table, path):
        font_candidates = (
            "C:/Windows/Fonts/arial.ttf",
            "C:\\Windows\\Fonts\\arial.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        )

        font_name = "Helvetica"
        for candidate in font_candidates:
            if os.path.exists(candidate):
                try:
                    pdfmetrics.registerFont(TTFont("Arial", candidate))
                    font_name = "Arial"
                    break
                except Exception:
                    continue

        if font_name == "Helvetica":
            try:
                pdfmetrics.registerFont(TTFont("Helvetica", "Helvetica"))
            except Exception:
                pass

        doc = SimpleDocTemplate(
            str(path),
            pagesize=landscape(A4),
            leftMargin=18,
            rightMargin=18,
            topMargin=18,
            bottomMargin=18,
        )
        elements = []
        styles = getSampleStyleSheet()
        styles["Title"].fontName = font_name
        styles["Normal"].fontName = font_name

        cell_style = styles["BodyText"].clone("PDFCellStyle")
        cell_style.fontName = font_name
        cell_style.fontSize = 8
        cell_style.alignment = 1
        cell_style.leading = 10

        airport_label = selected_airport_name or "www.flightradar24.com"
        current_local_time = datetime.now().astimezone().strftime("%Y.%m.%d %H:%M")
        title = Paragraph(f"<b>{ui_lang['official_flight_info'][trs]}</b>", styles["Title"])
        info = Paragraph(f"{current_local_time} | {ui_lang['source'][trs]} {airport_label}", styles["Normal"])
        elements.append(title)
        elements.append(info)
        elements.append(Spacer(1, 18))

        data_list = [[Paragraph(str(table.headerItem().text(c)), cell_style) for c in range(table.columnCount())]]
        for i in range(table.topLevelItemCount()):
            item = table.topLevelItem(i)
            if not item.isHidden():
                data_list.append([Paragraph(str(item.text(c)), cell_style) for c in range(table.columnCount())])

        col_widths = [
            doc.width * 0.12,
            doc.width * 0.10,
            doc.width * 0.26,
            doc.width * 0.14,
            doc.width * 0.16,
            doc.width * 0.12,
            doc.width * 0.10,
        ]
        t = Table(data_list, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#BFDBFE")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.HexColor("#ecf0f1")]),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("WORDWRAP", (0, 0), (-1, -1), 1),
            ]))
        elements.append(t)
        doc.build(elements)

    def populate_table(self, table, items, loc_key):
        table.clear()
        if not items: return
        for it in items:
            row = QTreeWidgetItem([
                str(it.get("time", "")), str(it.get("id", "")),
                str(it.get(loc_key, "")), str(it.get("country", "")),
                str(it.get("airline", "")), str(it.get("type", "")),
                str(it.get("status", ""))
            ])
            # insertTopLevelItem always inserts the new item at the top (index 0)
            table.insertTopLevelItem(0, row)

    def search_data(self):
        text = self.search_input.text().lower()
        for table in [self.table_arrivals, self.table_departures]:
            for i in range(table.topLevelItemCount()):
                item = table.topLevelItem(i)
                match = any(text in item.text(c).lower() for c in range(table.columnCount()))
                item.setHidden(not match)

    def toggle_maximize(self):
        if self.isMaximized(): self.showNormal(); self.btn_max.setText("▢")
        else: self.showMaximized(); self.btn_max.setText("❐")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.title_bar.underMouse():
            self._old_pos = event.globalPosition().toPoint()
    def mouseMoveEvent(self, event):
        if self._old_pos:
            delta = event.globalPosition().toPoint() - self._old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self._old_pos = event.globalPosition().toPoint()
    def mouseReleaseEvent(self, event):
        self._old_pos = None

    def resizeEvent(self, event):
        self.bg_label.resize(self.size())
        super().resizeEvent(event)

    def closeEvent(self, event):
        save_settings()
        super().closeEvent(event)


def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
    tb_text = "".join(tb_lines)

    msg = QMessageBox()
    msg.setIcon(QMessageBox.Icon.Critical)
    msg.setWindowTitle(ui_lang["program_error"][trs])
    msg.setText(f"{ui_lang['error'][trs]}: {exc_value}")
    msg.setDetailedText(tb_text)
    msg.exec()


if __name__ == "__main__":
    sys.excepthook = handle_exception
    app = QApplication(sys.argv)
    window = FlightMonitor()
    window.show()
    sys.exit(app.exec())