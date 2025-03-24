import time
import json
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from getpass import getpass


class LinkedInConnectionManager:
    def __init__(self, email, password, headless=False):
        """Initialize the LinkedIn Connection Manager with login credentials."""
        self.email = email
        self.password = password
        
        # Setup Chrome options
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-notifications')
        
        # Initialize the webdriver
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 10)
        self.connections = []
        self.to_remove_list = []
        
    def login(self):
        """Log in to LinkedIn."""
        try:
            self.driver.get('https://www.linkedin.com/login')
            
            # Enter email
            email_field = self.wait.until(EC.presence_of_element_located((By.ID, 'username')))
            email_field.send_keys(self.email)
            
            # Enter password
            password_field = self.driver.find_element(By.ID, 'password')
            password_field.send_keys(self.password)
            
            # Click sign in button
            sign_in_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            sign_in_button.click()
            
            # Wait for login to complete
            time.sleep(3)
            
            # Check if login was successful
            if 'feed' in self.driver.current_url or 'voyager' in self.driver.current_url:
                print("Successfully logged in to LinkedIn")
                return True
            else:
                print("Login unsuccessful. Please check your credentials.")
                return False
                
        except Exception as e:
            print(f"Error during login: {e}")
            return False

    def get_connections(self):
        """Scrape all LinkedIn connections."""
        try:
            # Navigate to connections page
            self.driver.get('https://www.linkedin.com/mynetwork/invite-connect/connections/')
            time.sleep(3)
            
            # Initialize list to store connections
            self.connections = []
            
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            
            # Scroll to load all connections
            while True:
                # Scroll down
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                
                # Wait for page to load
                time.sleep(2)
                
                # Calculate new scroll height and compare with last scroll height
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
                
                # Print progress
                print(f"Loaded {len(self.driver.find_elements(By.XPATH, '//li[contains(@class, "mn-connection-card")]'))} connections...")
            
            # Get all connection elements
            connection_elements = self.driver.find_elements(By.XPATH, '//li[contains(@class, "mn-connection-card")]')
            
            for element in connection_elements:
                try:
                    # Extract connection details
                    name = element.find_element(By.XPATH, './/span[contains(@class, "mn-connection-card__name")]').text
                    
                    # Get profile link
                    profile_link_elem = element.find_element(By.XPATH, './/a[contains(@class, "mn-connection-card__link")]')
                    profile_link = profile_link_elem.get_attribute('href')
                    
                    # Store basic connection info
                    connection = {
                        'name': name,
                        'profile_link': profile_link,
                        'companies': []
                    }
                    
                    self.connections.append(connection)
                    
                except NoSuchElementException as e:
                    print(f"Error extracting connection info: {e}")
                    continue
            
            print(f"Found {len(self.connections)} connections.")
            return self.connections
            
        except Exception as e:
            print(f"Error retrieving connections: {e}")
            return []

    def get_connection_details(self):
        """Get detailed information about each connection by visiting their profiles."""
        for i, connection in enumerate(self.connections):
            try:
                print(f"Processing connection {i+1}/{len(self.connections)}: {connection['name']}")
                
                # Visit profile page
                self.driver.get(connection['profile_link'])
                time.sleep(2)
                
                # Get experience section
                try:
                    # Wait for experience section to load
                    WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, "//section[contains(@class, 'experience-section') or contains(@id, 'experience-section')]"))
                    )
                    
                    # Extract company names
                    experience_elements = self.driver.find_elements(By.XPATH, "//a[contains(@href, '/company/')]")
                    companies = []
                    
                    for exp in experience_elements:
                        try:
                            company_name = exp.text.strip()
                            if company_name and company_name not in companies:
                                companies.append(company_name)
                        except:
                            continue
                    
                    connection['companies'] = companies
                    
                except TimeoutException:
                    print(f"Could not find experience section for {connection['name']}")
                
                # Sleep to avoid rate limiting
                time.sleep(1)
                
            except Exception as e:
                print(f"Error processing connection {connection['name']}: {e}")
                continue
        
        return self.connections

    def filter_connections(self, whitelisted_connections=None, whitelisted_companies=None):
        """Filter connections based on whitelist criteria."""
        if whitelisted_connections is None:
            whitelisted_connections = []
        
        if whitelisted_companies is None:
            whitelisted_companies = []
        
        self.to_remove_list = []
        
        for connection in self.connections:
            # Check if connection name is in whitelist
            if connection['name'] in whitelisted_connections:
                continue
            
            # Check if connection has worked at any whitelisted company
            has_whitelisted_company = False
            for company in connection['companies']:
                if any(wl_company.lower() in company.lower() for wl_company in whitelisted_companies):
                    has_whitelisted_company = True
                    break
            
            if not has_whitelisted_company:
                self.to_remove_list.append(connection)
        
        return self.to_remove_list

    def display_removal_list(self):
        """Display the list of connections to be removed."""
        if not self.to_remove_list:
            print("No connections to remove based on your criteria.")
            return False
        
        print(f"\n===== CONNECTIONS TO REMOVE ({len(self.to_remove_list)}) =====")
        for i, connection in enumerate(self.to_remove_list):
            companies_str = ", ".join(connection['companies']) if connection['companies'] else "No companies found"
            print(f"{i+1}. {connection['name']} - Companies: {companies_str}")
            print(f"   Profile: {connection['profile_link']}")
        
        return True

    def remove_connections(self):
        """Remove connections in the to_remove_list."""
        if not self.to_remove_list:
            print("No connections to remove.")
            return
        
        for i, connection in enumerate(self.to_remove_list):
            try:
                print(f"Removing connection {i+1}/{len(self.to_remove_list)}: {connection['name']}")
                
                # Go to the connection's profile
                self.driver.get(connection['profile_link'])
                time.sleep(2)
                
                # Click the "More" button to reveal the "Remove connection" option
                more_button = self.wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(@aria-label, 'More actions') or contains(@class, 'artdeco-dropdown__trigger')]")
                ))
                more_button.click()
                time.sleep(1)
                
                # Click the "Remove connection" option
                remove_button = self.wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//span[text()='Remove connection' or text()='Remove Connection']/parent::button")
                ))
                remove_button.click()
                time.sleep(1)
                
                # Confirm removal in the dialog
                confirm_button = self.wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(@class, 'artdeco-modal__confirm-dialog-btn') and contains(text(), 'Remove')]")
                ))
                confirm_button.click()
                
                print(f"Successfully removed {connection['name']}")
                time.sleep(2)
                
            except Exception as e:
                print(f"Error removing connection {connection['name']}: {e}")
                continue
    
    def save_connections(self, filename="linkedin_connections.json"):
        """Save connections data to a JSON file."""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.connections, f, indent=4)
        print(f"Connections saved to {filename}")
    
    def load_connections(self, filename="linkedin_connections.json"):
        """Load connections data from a JSON file."""
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                self.connections = json.load(f)
            print(f"Loaded {len(self.connections)} connections from {filename}")
            return True
        else:
            print(f"File {filename} not found.")
            return False
    
    def close(self):
        """Close the webdriver."""
        self.driver.quit()


def main():
    # Get LinkedIn credentials
    email = input("Enter your LinkedIn email: ")
    password = getpass("Enter your LinkedIn password: ")
    
    # Initialize the LinkedIn Connection Manager
    manager = LinkedInConnectionManager(email, password)
    
    # Login to LinkedIn
    if not manager.login():
        print("Login failed. Exiting...")
        manager.close()
        return
    
    # Ask if user wants to load saved connections
    load_saved = input("Do you want to load saved connections? (y/n): ").lower()
    
    if load_saved == 'y' and manager.load_connections():
        print("Using loaded connections.")
    else:
        # Get all connections
        print("Scraping your LinkedIn connections...")
        manager.get_connections()
        
        # Get detailed information about connections
        print("Getting detailed information for each connection...")
        manager.get_connection_details()
        
        # Save connections to file
        manager.save_connections()
    
    # Get whitelist criteria
    print("\nNow, let's set up your whitelist criteria.")
    
    # Whitelisted connections
    whitelisted_connections = []
    while True:
        name = input("Enter a name to whitelist (or press Enter to finish): ")
        if not name:
            break
        whitelisted_connections.append(name)
    
    # Whitelisted companies
    whitelisted_companies = []
    while True:
        company = input("Enter a company to whitelist (or press Enter to finish): ")
        if not company:
            break
        whitelisted_companies.append(company)
    
    # Filter connections based on whitelist
    print("\nFiltering connections based on your whitelist...")
    manager.filter_connections(whitelisted_connections, whitelisted_companies)
    
    # Display connections to be removed
    if manager.display_removal_list():
        # Ask for confirmation
        confirm = input("\nDo you want to remove these connections? (y/n): ").lower()
        
        if confirm == 'y':
            final_confirm = input("Are you sure? This action cannot be undone. (y/n): ").lower()
            
            if final_confirm == 'y':
                print("Removing connections...")
                manager.remove_connections()
                print("Connection removal completed.")
            else:
                print("Removal canceled.")
        else:
            print("No connections were removed.")
    
    # Close the webdriver
    manager.close()
    print("LinkedIn Connection Manager completed successfully.")


if __name__ == "__main__":
    main()