import pandas as pd
import time
import logging
import csv
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

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
            
            # Speed optimizations
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-images')
            chrome_options.add_argument('--disable-plugins')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-background-timer-throttling')
            chrome_options.add_argument('--disable-backgrounding-occluded-windows')
            chrome_options.add_argument('--disable-renderer-backgrounding')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            
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
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Set optimized timeouts
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
        try:
            url = "https://www.goindigo.in/edit-booking.html"
            self.driver.get(url)
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(1)
            self.logger.info("Successfully navigated to edit booking page")
            
        except Exception as e:
            self.logger.error(f"Failed to navigate to page: {str(e)}")
            raise
    
    def fill_booking_details(self, pnr, lastname):
        """Fill PNR and Last Name in the form with improved selectors"""
        try:
            # Find PNR input field
            pnr_input = None
            pnr_selectors = [
                "input[placeholder*='PNR']",
                "input[placeholder*='Booking Reference']",
                "input[name*='pnr']",
                "input[id*='pnr']",
                "input[type='text']:first-of-type"
            ]
            
            for selector in pnr_selectors:
                try:
                    pnr_input = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                    if pnr_input:
                        break
                except:
                    continue
            
            if not pnr_input:
                raise NoSuchElementException("Could not find PNR input field")
            
            # Find Last Name input field
            lastname_input = None
            lastname_selectors = [
                "input[placeholder*='Last Name']",
                "input[placeholder*='Email']",
                "input[name*='lastname']",
                "input[name*='email']",
                "input[type='text']:last-of-type"
            ]
            
            for selector in lastname_selectors:
                try:
                    lastname_input = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if lastname_input and lastname_input != pnr_input:
                        break
                except:
                    continue
            
            if not lastname_input:
                raise NoSuchElementException("Could not find Last Name input field")
            
            # Fill the form
            pnr_input.clear()
            pnr_input.send_keys(pnr)
            lastname_input.clear()
            lastname_input.send_keys(lastname)
            
            self.logger.info(f"Successfully filled PNR: {pnr}, Last Name: {lastname}")
            
        except Exception as e:
            self.logger.error(f"Failed to fill booking details for PNR {pnr}: {str(e)}")
            raise
    
    def click_get_itinerary(self):
        """Click the Get Itinerary button"""
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
                    
                    if button and button.is_enabled():
                        break
                except:
                    continue
            
            if not button:
                raise NoSuchElementException("Could not find Get Itinerary button")
            
            # Click the button
            self.driver.execute_script("arguments[0].scrollIntoView(true);", button)
            time.sleep(0.5)
            
            try:
                button.click()
            except:
                self.driver.execute_script("arguments[0].click();", button)
            
            self.logger.info("Successfully clicked Get Itinerary button")
            time.sleep(3)
            
        except Exception as e:
            self.logger.error(f"Failed to click Get Itinerary button: {str(e)}")
            raise
    
    def extract_flight_details(self, input_pnr, input_lastname, bms_code):
        """Extract flight details based on the actual HTML structure"""
        flight_details = {
            'BMS_Code': bms_code,  # Add BMS code at the beginning
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
            # Extract route from flight-journey-tab-container
            try:
                route_container = self.driver.find_element(By.CSS_SELECTOR, ".flight-journey-tab-container__leg")
                route_spans = route_container.find_elements(By.TAG_NAME, "span")
                if len(route_spans) >= 2:
                    flight_details['Source'] = route_spans[0].text.strip()
                    flight_details['Destination'] = route_spans[1].text.strip()
            except:
                pass
            
            # Extract date from booking-info-container-other-info__date
            try:
                date_element = self.driver.find_element(By.CSS_SELECTOR, ".booking-info-container-other-info__date span")
                flight_details['Departure_Date'] = date_element.text.strip()
            except:
                pass
            
            # Extract flight number from flight-code
            try:
                flight_code_element = self.driver.find_element(By.CSS_SELECTOR, ".flight-code")
                flight_details['Flight_Number'] = flight_code_element.text.strip()
            except:
                pass
            
            # Extract departure time from departure-time
            try:
                departure_time_element = self.driver.find_element(By.CSS_SELECTOR, ".departure-time")
                flight_details['Departure_Time'] = departure_time_element.text.strip()
            except:
                pass
            
            # Extract arrival time from arrival-time
            try:
                arrival_time_element = self.driver.find_element(By.CSS_SELECTOR, ".arrival-time")
                flight_details['Arrival_Time'] = arrival_time_element.text.strip()
            except:
                pass
            
            # Extract stop type from flight-stops
            try:
                stop_element = self.driver.find_element(By.CSS_SELECTOR, ".flight-stops")
                flight_details['Stop_Type'] = stop_element.text.strip()
            except:
                pass
            
            # Extract baggage information from flight-baggage-cabin__wrapper
            try:
                cabin_baggage_element = self.driver.find_element(By.CSS_SELECTOR, ".checkin .checkin-value")
                cabin_value = cabin_baggage_element.text.strip()
                flight_details['Cabin_Baggage'] = f"{cabin_value} Cabin"
            except:
                pass
            
            try:
                checkin_baggage_element = self.driver.find_element(By.CSS_SELECTOR, ".cabin .cabin-value")
                checkin_value = checkin_baggage_element.text.strip()
                flight_details['Checkin_Baggage'] = f"{checkin_value} Check-in"
            except:
                pass
            
        except Exception as e:
            self.logger.error(f"Error extracting flight details: {str(e)}")
        
        return flight_details
    
    def extract_passenger_details(self):
        """Extract passenger details based on the actual HTML structure"""
        passengers = []
        
        try:
            # Find all passenger detail sections
            passenger_sections = self.driver.find_elements(By.CSS_SELECTOR, ".passenger-details")
            
            for i, section in enumerate(passenger_sections):
                try:
                    passenger = {}
                    
                    # Extract passenger name from passenger-details__top-section__full-name
                    try:
                        name_element = section.find_element(By.CSS_SELECTOR, ".passenger-details__top-section__full-name span")
                        passenger['Name'] = name_element.text.strip()
                    except:
                        continue
                    
                    # Extract gender and age category from passenger-details__top-section__p-info
                    try:
                        p_info_elements = section.find_elements(By.CSS_SELECTOR, ".passenger-details__top-section__p-info__age-group")
                        if len(p_info_elements) >= 2:
                            passenger['Gender'] = p_info_elements[0].text.strip()
                            passenger['Age_Category'] = p_info_elements[1].text.strip()
                        else:
                            passenger['Gender'] = 'Unknown'
                            passenger['Age_Category'] = 'Adult'
                    except:
                        passenger['Gender'] = 'Unknown'
                        passenger['Age_Category'] = 'Adult'
                    
                    # Extract seat number from seat-info
                    try:
                        seat_element = section.find_element(By.CSS_SELECTOR, ".passenger-details__bottom-section__seat-info")
                        seat_text = seat_element.text.strip()
                        # Extract seat number (like 16A, 16B, 16C)
                        import re
                        seat_match = re.search(r'\b\d{1,2}[A-Z]\b', seat_text)
                        if seat_match:
                            passenger['Seat_Number'] = seat_match.group()
                        else:
                            passenger['Seat_Number'] = 'Not assigned'
                    except:
                        passenger['Seat_Number'] = 'Not assigned'
                    
                    # Extract flight status from sector-chip-no-show
                    try:
                        status_element = section.find_element(By.CSS_SELECTOR, ".sector-chip-no-show")
                        passenger['Flight_Status'] = status_element.text.strip()
                    except:
                        passenger['Flight_Status'] = 'Unknown'
                    
                    if passenger.get('Name'):
                        passengers.append(passenger)
                    
                except Exception as e:
                    continue
            
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
                        self.logger.info(f"Extracted data for passenger: {passenger.get('Name', 'Unknown')}")
                else:
                    # If no passengers found, still save flight details
                    flight_details['Passenger_Count'] = 0
                    self.scraped_data.append(flight_details)
                    self.logger.warning("No passenger details found, saved flight details only")
                
                return True
            else:
                self.logger.warning(f"No booking details loaded for PNR: {pnr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to scrape booking details for PNR {pnr}: {str(e)}")
            return False
    
    def check_booking_loaded(self):
        """Check if booking details page has loaded successfully"""
        try:
            # Look for the main itinerary container
            success_indicators = [
                ".view-itinerary",
                ".itinerary-details-title",
                ".booking-info",
                ".flight-details"
            ]
            
            for indicator in success_indicators:
                try:
                    element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, indicator)))
                    if element:
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking if booking loaded: {str(e)}")
            return False
    
    def export_to_csv(self):
        """Export scraped data to CSV file"""
        try:
            if not self.scraped_data:
                print("⚠️ No data to export")
                self.logger.warning("No data to export")
                return
            
            # Define CSV columns with BMS_Code at the beginning
            columns = [
                'BMS_Code', 'PNR', 'Last_Name', 'Source', 'Destination', 
                'Departure_Date', 'Flight_Number', 'Departure_Time', 'Arrival_Time', 
                'Stop_Type', 'Cabin_Baggage', 'Checkin_Baggage', 'Passenger_Count', 
                'Name', 'Gender', 'Age_Category', 'Seat_Number', 'Flight_Status'
            ]
            
            # Create DataFrame
            df = pd.DataFrame(self.scraped_data)
            
            # Reorder columns (only include existing ones)
            existing_columns = [col for col in columns if col in df.columns]
            df = df[existing_columns]
            
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
                    print(f"❌ Failed")
                
                # Small delay between bookings
                if i < len(bookings):
                    time.sleep(2)
            
            # Final summary
            duration = time.time() - start_time
            print(f"\n📊 Scraping completed: {successful_scrapes}/{len(bookings)} successful")
            print(f"⏱️ Total time: {duration:.1f} seconds")
            
            # Export to CSV
            if self.scraped_data:
                self.export_to_csv()
            else:
                print("⚠️ No data was scraped successfully")
            
        except Exception as e:
            print(f"❌ Scraper failed: {str(e)}")
            self.logger.error(f"Scraper failed: {str(e)}")
            
        finally:
            if self.driver:
                self.driver.quit()
                self.logger.info("WebDriver closed")

def main():
    """Main function"""
    # Configuration
    CSV_FILE_PATH = "PNR_LastName.csv"  # Update with your CSV file path
    OUTPUT_FILE_PATH = f"booking_details_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    HEADLESS_MODE = True  # Set to False to see browser window (slower)
    
    try:
        # Create and run optimized scraper
        scraper = OptimizedIndiGoScraper(
            csv_file_path=CSV_FILE_PATH,
            output_file_path=OUTPUT_FILE_PATH,
            headless=HEADLESS_MODE
        )
        scraper.run_scraper()
        
    except Exception as e:
        print(f"❌ Script failed: {str(e)}")

if __name__ == "__main__":
    main()