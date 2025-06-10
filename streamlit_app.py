import streamlit as st
import pandas as pd
import os
import sys
import time
import tempfile
from datetime import datetime
from pathlib import Path
import logging
from io import StringIO
import re

# Selenium imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

# ============= SCRAPER CLASS =============

class OptimizedIndiGoScraper:
    def __init__(self, csv_file_path, output_file_path="booking_details.csv", headless=True):
        self.csv_file_path = csv_file_path
        self.output_file_path = output_file_path
        self.headless = headless
        self.driver = None
        self.wait = None
        self.scraped_data = []
        
        # Setup logging with UTF-8 encoding
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('indigo_optimized_scraper.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def setup_driver(self):
        """Setup Chrome WebDriver with optimized performance settings"""
        try:
            chrome_options = Options()
            
            # Performance optimizations
            if self.headless:
                chrome_options.add_argument('--headless=new')
                self.logger.info("Running in headless mode")
            else:
                self.logger.info("Running in visible mode")
            
            # Speed optimizations (keeping images disabled like in local version)
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-images')  # From local version
            chrome_options.add_argument('--disable-plugins')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-background-timer-throttling')
            chrome_options.add_argument('--disable-backgrounding-occluded-windows')
            chrome_options.add_argument('--disable-renderer-backgrounding')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # Performance prefs
            prefs = {
                "profile.managed_default_content_settings.images": 2,
                "profile.default_content_settings.popups": 0,
                "profile.managed_default_content_settings.media_stream": 2,
            }
            chrome_options.add_experimental_option("prefs", prefs)
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Initialize driver with proper error handling
            try:
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            except Exception as e:
                self.logger.error(f"Failed to initialize Chrome driver: {str(e)}")
                # Try alternative initialization
                self.driver = webdriver.Chrome(options=chrome_options)
            
            # Set optimized timeouts (matching local version)
            self.driver.set_page_load_timeout(20)
            self.driver.implicitly_wait(3)
            
            # Remove webdriver property
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.wait = WebDriverWait(self.driver, 10)
            
            self.logger.info("WebDriver setup completed successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to setup WebDriver: {str(e)}")
            raise
    
    def load_csv_data(self):
        """Load and validate CSV data with BMS booking code"""
        try:
            df = pd.read_csv(self.csv_file_path)
            
            if len(df.columns) < 3:
                raise ValueError("CSV must have at least 3 columns (PNR, Last Name, and BMS Code)")
            
            pnr_column = df.columns[0]
            lastname_column = df.columns[1]
            bms_column = df.columns[2]
            
            bookings = []
            for _, row in df.iterrows():
                pnr = str(row[pnr_column]).strip()
                lastname = str(row[lastname_column]).strip()
                bms_code = str(row[bms_column]).strip() if pd.notna(row[bms_column]) else ""
                
                if pnr and lastname and pnr.lower() != 'nan' and lastname.lower() != 'nan':
                    bookings.append((pnr, lastname, bms_code))
            
            print(f"📋 Loaded {len(bookings)} booking records from CSV")
            self.logger.info(f"Loaded {len(bookings)} booking records from CSV")
            return bookings
            
        except Exception as e:
            self.logger.error(f"Failed to load CSV data: {str(e)}")
            raise
    
    def navigate_to_edit_booking(self):
        """Navigate to the edit booking page"""
        try:
            url = "https://www.goindigo.in/edit-booking.html"
            self.driver.get(url)
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(1)  # Reduced from 3 seconds to match local version
            self.logger.info("Successfully navigated to edit booking page")
            
        except Exception as e:
            self.logger.error(f"Failed to navigate to page: {str(e)}")
            raise
    
    def fill_booking_details(self, pnr, lastname):
        """Fill PNR and Last Name with targeted selectors from local version"""
        try:
            # Find PNR input field with more targeted selectors
            pnr_input = None
            pnr_selectors = [
                "input[placeholder*='PNR']",
                "input[placeholder*='Booking Reference']", 
                "input[placeholder*='Booking reference']",  # Added this specific variant
                "input[name*='pnr']",
                "input[id*='pnr']",
                "input[type='text']:first-of-type"
            ]
            
            for selector in pnr_selectors:
                try:
                    pnr_input = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                    if pnr_input and pnr_input.is_displayed() and pnr_input.is_enabled():
                        break
                except:
                    continue
            
            if not pnr_input:
                raise NoSuchElementException("Could not find PNR input field")
            
            # Find Last Name input with targeted selectors
            lastname_input = None
            lastname_selectors = [
                "input[placeholder*='Last Name']",
                "input[placeholder*='Last name']",  # Case variation
                "input[placeholder*='Email']",
                "input[placeholder*='Email ID']",  # More specific
                "input[name*='lastname']",
                "input[name*='email']",
                "input[type='text']:last-of-type"
            ]
            
            for selector in lastname_selectors:
                try:
                    lastname_input = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if lastname_input and lastname_input.is_displayed() and lastname_input.is_enabled() and lastname_input != pnr_input:
                        break
                except:
                    continue
            
            if not lastname_input:
                raise NoSuchElementException("Could not find Last Name input field")
            
            # Clear and fill the form
            pnr_input.clear()
            pnr_input.send_keys(pnr)
            lastname_input.clear()
            lastname_input.send_keys(lastname)
            
            self.logger.info(f"Successfully filled PNR: {pnr}, Last Name: {lastname}")
            
        except Exception as e:
            self.logger.error(f"Failed to fill booking details for PNR {pnr}: {str(e)}")
            raise
    
    def click_get_itinerary(self):
        """Click the Get Itinerary button with targeted selectors"""
        try:
            button = None
            button_selectors = [
                "//button[contains(text(), 'Get Itinerary')]",
                "//input[@value='Get Itinerary']",
                "button[type='submit']",
                ".btn-primary",
                "button:last-of-type"
            ]
            
            for selector in button_selectors:
                try:
                    if selector.startswith("//"):
                        button = self.driver.find_element(By.XPATH, selector)
                    else:
                        button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    
                    if button and button.is_displayed() and button.is_enabled():
                        break
                except:
                    continue
            
            if not button:
                raise NoSuchElementException("Could not find Get Itinerary button")
            
            # Scroll and click
            self.driver.execute_script("arguments[0].scrollIntoView(true);", button)
            time.sleep(0.5)
            
            try:
                button.click()
            except:
                self.driver.execute_script("arguments[0].click();", button)
            
            self.logger.info("Successfully clicked Get Itinerary button")
            time.sleep(3)  # Wait for page load
            
        except Exception as e:
            self.logger.error(f"Failed to click Get Itinerary button: {str(e)}")
            raise
    
    def check_booking_loaded(self):
        """Check if booking details page has loaded successfully"""
        try:
            # Wait for page to load first
            time.sleep(2)
            
            # Check for error messages first
            error_selectors = [
                "//*[contains(text(), 'Invalid')]",
                "//*[contains(text(), 'not found')]", 
                "//*[contains(text(), 'incorrect')]",
                "//*[contains(text(), 'error')]"
            ]
            
            for selector in error_selectors:
                try:
                    error_elem = self.driver.find_element(By.XPATH, selector)
                    if error_elem.is_displayed():
                        self.logger.warning(f"Error message found: {error_elem.text}")
                        return False
                except:
                    pass
            
            # Look for success indicators using targeted selectors from local version
            success_indicators = [
                ".view-itinerary",
                ".itinerary-details-title", 
                ".booking-info",
                ".flight-details",
                ".passenger-details"  # Key indicator for passenger data
            ]
            
            for indicator in success_indicators:
                try:
                    element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, indicator)))
                    if element and element.is_displayed():
                        self.logger.info(f"Found success indicator: {indicator}")
                        return True
                except:
                    continue
            
            # Additional check for URL change
            current_url = self.driver.current_url.lower()
            if "itinerary" in current_url or "booking-details" in current_url:
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking if booking loaded: {str(e)}")
            return False
    
    def extract_flight_details(self, input_pnr, input_lastname, bms_code):
        """Extract flight details using targeted selectors from local version"""
        flight_details = {
            'BMS_Code': bms_code,
            'PNR': input_pnr,
            'Last_Name': input_lastname,
            'Source': 'Not found',
            'Destination': 'Not found',
            'Departure_Date': 'Not found',
            'Flight_Number': 'Not found',
            'Departure_Time': 'Not found',
            'Arrival_Time': 'Not found',
            'Stop_Type': 'Not found',
            'Cabin_Baggage': 'Not found',
            'Checkin_Baggage': 'Not found',
        }
        
        try:
            # Extract route from flight-journey-tab-container (from local version)
            try:
                route_container = self.driver.find_element(By.CSS_SELECTOR, ".flight-journey-tab-container__leg")
                route_spans = route_container.find_elements(By.TAG_NAME, "span")
                if len(route_spans) >= 2:
                    flight_details['Source'] = route_spans[0].text.strip()
                    flight_details['Destination'] = route_spans[1].text.strip()
                    self.logger.info(f"Found route: {flight_details['Source']} to {flight_details['Destination']}")
            except Exception as e:
                self.logger.warning(f"Could not extract route: {str(e)}")
            
            # Extract date from booking-info-container-other-info__date (from local version)
            try:
                date_element = self.driver.find_element(By.CSS_SELECTOR, ".booking-info-container-other-info__date span")
                flight_details['Departure_Date'] = date_element.text.strip()
                self.logger.info(f"Found date: {flight_details['Departure_Date']}")
            except Exception as e:
                self.logger.warning(f"Could not extract date: {str(e)}")
            
            # Extract flight number from flight-code (from local version)
            try:
                flight_code_element = self.driver.find_element(By.CSS_SELECTOR, ".flight-code")
                flight_details['Flight_Number'] = flight_code_element.text.strip()
                self.logger.info(f"Found flight number: {flight_details['Flight_Number']}")
            except Exception as e:
                self.logger.warning(f"Could not extract flight number: {str(e)}")
            
            # Extract departure time (from local version)
            try:
                departure_time_element = self.driver.find_element(By.CSS_SELECTOR, ".departure-time")
                flight_details['Departure_Time'] = departure_time_element.text.strip()
                self.logger.info(f"Found departure time: {flight_details['Departure_Time']}")
            except Exception as e:
                self.logger.warning(f"Could not extract departure time: {str(e)}")
            
            # Extract arrival time (from local version)
            try:
                arrival_time_element = self.driver.find_element(By.CSS_SELECTOR, ".arrival-time")
                flight_details['Arrival_Time'] = arrival_time_element.text.strip()
                self.logger.info(f"Found arrival time: {flight_details['Arrival_Time']}")
            except Exception as e:
                self.logger.warning(f"Could not extract arrival time: {str(e)}")
            
            # Extract stop type from flight-stops (from local version)
            try:
                stop_element = self.driver.find_element(By.CSS_SELECTOR, ".flight-stops")
                flight_details['Stop_Type'] = stop_element.text.strip()
                self.logger.info(f"Found stop type: {flight_details['Stop_Type']}")
            except Exception as e:
                self.logger.warning(f"Could not extract stop type: {str(e)}")
            
            # Extract baggage information (corrected from local version)
            try:
                # Cabin baggage 
                cabin_baggage_element = self.driver.find_element(By.CSS_SELECTOR, ".cabin .cabin-value")
                cabin_value = cabin_baggage_element.text.strip()
                flight_details['Cabin_Baggage'] = f"{cabin_value} Cabin"
                self.logger.info(f"Found cabin baggage: {flight_details['Cabin_Baggage']}")
            except Exception as e:
                self.logger.warning(f"Could not extract cabin baggage: {str(e)}")
            
            try:
                # Check-in baggage
                checkin_baggage_element = self.driver.find_element(By.CSS_SELECTOR, ".checkin .checkin-value")
                checkin_value = checkin_baggage_element.text.strip()
                flight_details['Checkin_Baggage'] = f"{checkin_value} Check-in"
                self.logger.info(f"Found checkin baggage: {flight_details['Checkin_Baggage']}")
            except Exception as e:
                self.logger.warning(f"Could not extract checkin baggage: {str(e)}")
            
        except Exception as e:
            self.logger.error(f"Error extracting flight details: {str(e)}")
        
        return flight_details
    
    def extract_passenger_details(self):
        """Extract passenger details using targeted selectors from local version"""
        passengers = []
        
        try:
            # Find all passenger detail sections (from local version)
            passenger_sections = self.driver.find_elements(By.CSS_SELECTOR, ".passenger-details")
            self.logger.info(f"Found {len(passenger_sections)} passenger sections")
            
            for i, section in enumerate(passenger_sections):
                try:
                    passenger = {}
                    
                    # Extract passenger name (from local version)
                    try:
                        name_element = section.find_element(By.CSS_SELECTOR, ".passenger-details__top-section__full-name span")
                        passenger['Name'] = name_element.text.strip()
                        self.logger.info(f"Found passenger name: {passenger['Name']}")
                    except Exception as e:
                        self.logger.warning(f"Could not extract passenger name from section {i}: {str(e)}")
                        continue
                    
                    # Extract gender and age category (from local version)
                    try:
                        p_info_elements = section.find_elements(By.CSS_SELECTOR, ".passenger-details__top-section__p-info__age-group")
                        if len(p_info_elements) >= 2:
                            passenger['Gender'] = p_info_elements[0].text.strip()
                            passenger['Age_Category'] = p_info_elements[1].text.strip()
                            self.logger.info(f"Found gender: {passenger['Gender']}, age category: {passenger['Age_Category']}")
                        else:
                            passenger['Gender'] = 'Unknown'
                            passenger['Age_Category'] = 'Adult'
                            self.logger.warning("Could not extract gender/age category, using defaults")
                    except Exception as e:
                        passenger['Gender'] = 'Unknown'
                        passenger['Age_Category'] = 'Adult'
                        self.logger.warning(f"Error extracting gender/age: {str(e)}")
                    
                    # Extract seat number (from local version with improved regex)
                    try:
                        seat_element = section.find_element(By.CSS_SELECTOR, ".passenger-details__bottom-section__seat-info")
                        seat_text = seat_element.text.strip()
                        # Extract seat number (like 16A, 16B, 16C)
                        seat_match = re.search(r'\b\d{1,2}[A-Z]\b', seat_text)
                        if seat_match:
                            passenger['Seat_Number'] = seat_match.group()
                            self.logger.info(f"Found seat number: {passenger['Seat_Number']}")
                        else:
                            passenger['Seat_Number'] = 'Not assigned'
                            self.logger.warning("No seat number found in text")
                    except Exception as e:
                        passenger['Seat_Number'] = 'Not assigned'
                        self.logger.warning(f"Could not extract seat number: {str(e)}")
                    
                    # Extract flight status (from local version) - This is the MOST IMPORTANT field
                    try:
                        status_element = section.find_element(By.CSS_SELECTOR, ".sector-chip-no-show")
                        passenger['Flight_Status'] = status_element.text.strip()
                        self.logger.info(f"Found flight status: {passenger['Flight_Status']}")
                    except Exception as e:
                        # Try alternative selectors for flight status
                        try:
                            # Look for other possible status indicators
                            status_selectors = [
                                ".flight-status",
                                ".booking-status", 
                                ".status-chip",
                                "[class*='status']",
                                "[class*='chip']"
                            ]
                            
                            status_found = False
                            for status_selector in status_selectors:
                                try:
                                    alt_status_element = section.find_element(By.CSS_SELECTOR, status_selector)
                                    if alt_status_element.text.strip():
                                        passenger['Flight_Status'] = alt_status_element.text.strip()
                                        self.logger.info(f"Found flight status (alternative): {passenger['Flight_Status']}")
                                        status_found = True
                                        break
                                except:
                                    continue
                            
                            if not status_found:
                                passenger['Flight_Status'] = 'Confirmed'  # Default assumption
                                self.logger.warning("Could not extract flight status, defaulting to 'Confirmed'")
                        except:
                            passenger['Flight_Status'] = 'Unknown'
                            self.logger.warning(f"Could not extract flight status: {str(e)}")
                    
                    # Only add passenger if we have at least the name
                    if passenger.get('Name'):
                        passengers.append(passenger)
                        self.logger.info(f"Successfully extracted passenger {i+1}: {passenger['Name']}")
                    else:
                        self.logger.warning(f"Skipping passenger section {i} - no name found")
                    
                except Exception as e:
                    self.logger.warning(f"Error processing passenger section {i}: {str(e)}")
                    continue
            
            self.logger.info(f"Successfully extracted {len(passengers)} passengers")
            
        except Exception as e:
            self.logger.error(f"Error extracting passenger details: {str(e)}")
        
        return passengers
    
    def scrape_booking_details(self, pnr, lastname, bms_code):
        """Main method to scrape all booking details"""
        try:
            # Navigate and fill form
            self.navigate_to_edit_booking()
            self.fill_booking_details(pnr, lastname)
            self.click_get_itinerary()
            
            # Check if booking details are loaded
            if self.check_booking_loaded():
                self.logger.info(f"Booking details loaded successfully for PNR: {pnr}")
                
                # Extract flight details
                flight_details = self.extract_flight_details(pnr, lastname, bms_code)
                
                # Extract passenger details
                passengers = self.extract_passenger_details()
                
                # Combine flight and passenger details
                if passengers:
                    for passenger in passengers:
                        combined_data = {**flight_details, **passenger}
                        combined_data['Passenger_Count'] = len(passengers)
                        self.scraped_data.append(combined_data)
                        self.logger.info(f"Combined data for passenger: {passenger.get('Name', 'Unknown')}")
                    return True
                else:
                    # If no passengers found, still save flight details with default passenger info
                    flight_details['Passenger_Count'] = 0
                    flight_details['Name'] = 'No passenger details found'
                    flight_details['Gender'] = 'Unknown'
                    flight_details['Age_Category'] = 'Unknown'
                    flight_details['Seat_Number'] = 'Not found'
                    flight_details['Flight_Status'] = 'Check manually'
                    self.scraped_data.append(flight_details)
                    self.logger.warning("No passenger details found, saved flight details only")
                    return False
                    
            else:
                # Save basic info even if booking not loaded properly
                basic_data = {
                    'BMS_Code': bms_code,
                    'PNR': pnr,
                    'Last_Name': lastname,
                    'Source': 'Failed to load',
                    'Destination': 'Failed to load', 
                    'Departure_Date': 'Failed to load',
                    'Flight_Number': 'Failed to load',
                    'Departure_Time': 'Failed to load',
                    'Arrival_Time': 'Failed to load',
                    'Stop_Type': 'Failed to load',
                    'Cabin_Baggage': 'Failed to load',
                    'Checkin_Baggage': 'Failed to load',
                    'Passenger_Count': 0,
                    'Name': 'Failed to load',
                    'Gender': 'Unknown',
                    'Age_Category': 'Unknown', 
                    'Seat_Number': 'Not found',
                    'Flight_Status': 'Failed'
                }
                self.scraped_data.append(basic_data)
                self.logger.warning(f"Booking details not loaded for PNR: {pnr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to scrape booking details for PNR {pnr}: {str(e)}")
            # Save error data
            error_data = {
                'BMS_Code': bms_code,
                'PNR': pnr,
                'Last_Name': lastname,
                'Source': f'Error: {str(e)[:50]}',
                'Destination': 'Error',
                'Departure_Date': 'Error',
                'Flight_Number': 'Error',
                'Departure_Time': 'Error',
                'Arrival_Time': 'Error',
                'Stop_Type': 'Error',
                'Cabin_Baggage': 'Error',
                'Checkin_Baggage': 'Error',
                'Passenger_Count': 0,
                'Name': 'Error',
                'Gender': 'Unknown',
                'Age_Category': 'Unknown',
                'Seat_Number': 'Error',
                'Flight_Status': 'Error'
            }
            self.scraped_data.append(error_data)
            return False
    
    def export_to_csv(self):
        """Export scraped data to CSV file"""
        try:
            if not self.scraped_data:
                print("⚠️ No data to export")
                self.logger.warning("No data to export")
                return
            
            # Define CSV columns with important fields prioritized
            columns = [
                'BMS_Code', 'PNR', 'Last_Name', 'Name', 'Flight_Status', 'Seat_Number',
                'Source', 'Destination', 'Departure_Date', 'Flight_Number', 
                'Departure_Time', 'Arrival_Time', 'Stop_Type', 'Cabin_Baggage', 
                'Checkin_Baggage', 'Passenger_Count', 'Gender', 'Age_Category'
            ]
            
            # Create DataFrame
            df = pd.DataFrame(self.scraped_data)
            
            # Ensure all columns exist
            for col in columns:
                if col not in df.columns:
                    df[col] = 'Not found'
            
            # Reorder columns to prioritize important fields
            df = df[columns]
            
            # Export to CSV
            df.to_csv(self.output_file_path, index=False, encoding='utf-8')
            
            print(f"\n🎉 Export successful! File saved as: {self.output_file_path}")
            print(f"📊 Total records exported: {len(self.scraped_data)}")
            
            self.logger.info(f"Successfully exported {len(self.scraped_data)} records to {self.output_file_path}")
            
        except Exception as e:
            print(f"❌ Export failed: {str(e)}")
            self.logger.error(f"Failed to export data to CSV: {str(e)}")
            raise
    
    def run_scraper(self):
        """Main method to run the optimized scraper"""
        start_time = time.time()
        
        try:
            print("🚀 Starting IndiGo Scraper")
            print("=" * 50)
            
            # Setup WebDriver
            self.setup_driver()
            
            # Load CSV data
            bookings = self.load_csv_data()
            
            if not bookings:
                print("❌ No valid bookings found")
                self.logger.warning("No valid booking data found in CSV")
                return
            
            print(f"📋 Processing {len(bookings)} bookings...")
            
            # Process each booking
            successful_scrapes = 0
            for i, (pnr, lastname, bms_code) in enumerate(bookings, 1):
                print(f"\n[{i}/{len(bookings)}] Processing PNR: {pnr}")
                
                if self.scrape_booking_details(pnr, lastname, bms_code):
                    successful_scrapes += 1
                    print(f"✅ Success")
                else:
                    print(f"⚠️ Partial data retrieved")
                
                # Small delay between bookings (matching local version)
                if i < len(bookings):
                    time.sleep(2)
            
            # Final summary
            duration = time.time() - start_time
            print(f"\n📊 Scraping completed: {successful_scrapes}/{len(bookings)} successful")
            print(f"⏱️ Total time: {duration:.1f} seconds")
            
            # Always export data, even if partially successful
            self.export_to_csv()
            
        except Exception as e:
            print(f"❌ Scraper failed: {str(e)}")
            self.logger.error(f"Scraper failed: {str(e)}")
            
            # Try to export whatever data we have
            if self.scraped_data:
                print("Attempting to export partial data...")
                self.export_to_csv()
            
        finally:
            if self.driver:
                self.driver.quit()
                self.logger.info("WebDriver closed")


# ============= STREAMLIT UI =============

# Page configuration
st.set_page_config(
    page_title="IndiGo Booking Scraper",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .stButton > button {
        width: 100%;
        background-color: #FF6B35;
        color: white;
        font-weight: bold;
    }
    .stButton > button:hover {
        background-color: #FF5722;
    }
    .success-message {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #D4EDDA;
        border: 1px solid #C3E6CB;
        color: #155724;
    }
    .error-message {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #F8D7DA;
        border: 1px solid #F5C6CB;
        color: #721C24;
    }
    .important-fields {
        background-color: #FFF3CD;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #FFEAA7;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'scraping_in_progress' not in st.session_state:
    st.session_state.scraping_in_progress = False
if 'scraping_complete' not in st.session_state:
    st.session_state.scraping_complete = False
if 'result_file' not in st.session_state:
    st.session_state.result_file = None

# Header
st.title("✈️ IndiGo Booking Scraper - By Analytics")
st.markdown("Extract detailed booking information including **Flight Status**, **Seat Numbers**, and **Passenger Names**")

# Important fields notice
st.markdown("""
<div class="important-fields">
    <strong>🎯 Priority Fields Being Extracted:</strong><br>
    • <strong>Flight Status</strong> - Confirmed/Cancelled/No-show status<br>
    • <strong>Seat Number</strong> - Assigned seat (e.g., 16A, 12C)<br>
    • <strong>Passenger Name</strong> - Full passenger name<br>
    • <strong>Flight Details</strong> - Route, times, flight number<br>
</div>
""", unsafe_allow_html=True)

# Create columns for layout
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("### 📤 Upload CSV File")
    st.markdown("Your CSV should have 3 columns in this order: **PNR**, **Last Name**, **BMS Booking Code**")
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Choose a CSV file",
        type=['csv'],
        help="Upload a CSV file with PNR, Last Name, and BMS Code columns"
    )
    
    if uploaded_file is not None:
        # Preview the uploaded file
        try:
            df_preview = pd.read_csv(uploaded_file)
            uploaded_file.seek(0)  # Reset file pointer
            
            st.markdown("### 📊 File Preview")
            
            # Show file info
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric("Total Rows", len(df_preview))
            with col_b:
                st.metric("Total Columns", len(df_preview.columns))
            with col_c:
                st.metric("File Size", f"{uploaded_file.size / 1024:.1f} KB")
            
            # Show data preview
            st.dataframe(df_preview.head(10), use_container_width=True)
            
            # Validate columns
            if len(df_preview.columns) < 3:
                st.error("⚠️ CSV must have at least 3 columns (PNR, Last Name, BMS Code)")
            else:
                st.success("✅ File uploaded successfully!")
                
        except Exception as e:
            st.error(f"Error reading CSV file: {str(e)}")

with col2:
    st.markdown("### ⚙️ Settings")
    
    # Scraper settings
    headless_mode = st.checkbox(
        "Run in Headless Mode",
        value=True,
        help="Run browser in background (faster) or show browser window (slower)"
    )
    
    delay_seconds = st.slider(
        "Delay between bookings (seconds)",
        min_value=1,
        max_value=10,
        value=2,  # Reduced default to match local version
        help="Time to wait between processing each booking"
    )
    
    st.markdown("### 📋 Instructions")
    st.markdown("""
    1. Upload your CSV file
    2. Adjust settings if needed  
    3. Click 'Start Scraping'
    4. Wait for completion
    5. Download results
    
    **Note:** Enhanced version focuses on extracting Flight Status, Seat Numbers, and Passenger Names more reliably.
    """)

# Progress section
if uploaded_file is not None and len(df_preview.columns) >= 3:
    st.markdown("---")
    
    # Create a custom scraper class that captures logs
    class StreamlitIndiGoScraper(OptimizedIndiGoScraper):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.progress_callback = None
            
        def scrape_booking_details(self, pnr, lastname, bms_code):
            """Override to add progress callback"""
            if self.progress_callback:
                self.progress_callback(pnr, lastname)
            return super().scrape_booking_details(pnr, lastname, bms_code)
    
    # Scraping section
    col_left, col_right = st.columns([3, 1])
    
    with col_left:
        if st.button("🚀 Start Enhanced Scraping", type="primary", disabled=st.session_state.scraping_in_progress):
            st.session_state.scraping_in_progress = True
            st.session_state.scraping_complete = False
            
            # Create temporary file for input
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_input:
                df_preview.to_csv(tmp_input, index=False)
                tmp_input_path = tmp_input.name
            
            # Create output filename
            output_filename = f"booking_details_enhanced_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            output_path = os.path.join(tempfile.gettempdir(), output_filename)
            
            # Progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            log_container = st.container()
            
            total_bookings = len(df_preview)
            processed_count = [0]
            
            def update_progress(pnr, lastname):
                processed_count[0] += 1
                progress = processed_count[0] / total_bookings
                progress_bar.progress(progress)
                status_text.text(f"Processing {processed_count[0]}/{total_bookings}: PNR {pnr}")
            
            # Run enhanced scraper
            try:
                with st.spinner("Initializing enhanced scraper..."):
                    scraper = StreamlitIndiGoScraper(
                        csv_file_path=tmp_input_path,
                        output_file_path=output_path,
                        headless=headless_mode
                    )
                    scraper.progress_callback = update_progress
                    
                    # Patch the delay
                    original_sleep = time.sleep
                    def custom_sleep(seconds):
                        if seconds == 2:  # Replace the hardcoded 2-second delay
                            original_sleep(delay_seconds)
                        else:
                            original_sleep(seconds)
                    
                    time.sleep = custom_sleep
                    
                    # Run the scraper
                    scraper.run_scraper()
                    
                    # Restore original sleep
                    time.sleep = original_sleep
                
                # Check if output file was created
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    st.session_state.result_file = output_path
                    st.session_state.scraping_complete = True
                    st.success("✅ Enhanced scraping completed successfully!")
                    
                    # Show results preview with focus on important fields
                    result_df = pd.read_csv(output_path)
                    st.markdown("### 📊 Results Preview")
                    
                    # Show key metrics
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Records", len(result_df))
                    with col2:
                        unique_pnrs = result_df['PNR'].nunique() if 'PNR' in result_df.columns else 0
                        st.metric("Unique PNRs", unique_pnrs)
                    with col3:
                        # Count records with flight status (not 'Not found' or error)
                        valid_status = len(result_df[
                            (result_df['Flight_Status'] != 'Not found') & 
                            (result_df['Flight_Status'] != 'Error') &
                            (result_df['Flight_Status'] != 'Failed')
                        ]) if 'Flight_Status' in result_df.columns else 0
                        st.metric("Flight Status Found", valid_status)
                    with col4:
                        # Count records with seat numbers
                        valid_seats = len(result_df[
                            (result_df['Seat_Number'] != 'Not found') & 
                            (result_df['Seat_Number'] != 'Not assigned') &
                            (result_df['Seat_Number'] != 'Error')
                        ]) if 'Seat_Number' in result_df.columns else 0
                        st.metric("Seat Numbers Found", valid_seats)
                    
                    # Show preview focusing on important columns
                    important_cols = ['PNR', 'Name', 'Flight_Status', 'Seat_Number', 'Source', 'Destination', 'Flight_Number']
                    preview_cols = [col for col in important_cols if col in result_df.columns]
                    if preview_cols:
                        st.dataframe(result_df[preview_cols].head(10), use_container_width=True)
                    else:
                        st.dataframe(result_df.head(10), use_container_width=True)
                    
                    # Success rate calculation
                    success_rate = (unique_pnrs / len(df_preview)) * 100 if len(df_preview) > 0 else 0
                    if success_rate >= 80:
                        st.success(f"🎉 High success rate: {success_rate:.1f}%")
                    elif success_rate >= 50:
                        st.warning(f"⚠️ Moderate success rate: {success_rate:.1f}%")
                    else:
                        st.error(f"❌ Low success rate: {success_rate:.1f}%")
                        
                else:
                    st.warning("⚠️ Scraping completed but some data may be missing. Check the downloaded file for details.")
                    
            except Exception as e:
                st.error(f"❌ An error occurred during scraping: {str(e)}")
                st.info("💡 **Troubleshooting Tips:**")
                st.info("• Make sure Chrome browser is installed")
                st.info("• Check your internet connection")
                st.info("• Verify PNR and Last Name combinations are correct")
                st.info("• Try running with headless mode disabled to see what's happening")
                
            finally:
                st.session_state.scraping_in_progress = False
                
                # Clean up temporary input file
                if os.path.exists(tmp_input_path):
                    os.remove(tmp_input_path)
    
    # Download section
    if st.session_state.scraping_complete and st.session_state.result_file:
        with col_right:
            if os.path.exists(st.session_state.result_file):
                with open(st.session_state.result_file, "rb") as file:
                    st.download_button(
                        label="📥 Download Best Results",
                        data=file.read(),
                        file_name=os.path.basename(st.session_state.result_file),
                        mime="text/csv",
                        type="secondary"
                    )
                st.success("CSV includes prioritized columns: Flight Status, Seat Numbers, and Passenger Names")

# Footer with tips
st.markdown("---")
st.markdown("""
### Tips for Better Results:
- Ensure PNR and Last Name combinations are exactly as they appear in your IndiGo booking
- Run during off-peak hours for better website response
- If scraping fails, try reducing the delay between bookings
- The enhanced version prioritizes extracting Flight Status, Seat Numbers, and Passenger Names
""")