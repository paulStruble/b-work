import hashlib
import os
import shutil
from pathlib import Path
from selenium.common import exceptions
import User
from selenium import webdriver
from WebAutomation import *
from WorkOrderRequest import *
from User import *


class Scraper:
    def __init__(self, chrome_path: Path, chromedriver_path: Path, user: User = None, process_id: int = 0,
                 headless: bool = True):
        """An automated webscraper for retrieving work order and work order request data.

        Args:
            chrome_path: Path pointing to the chrome directory
            chromedriver_path: Path pointing to the chromedriver directory
            user: Calnet user for Calnet login and authorization
            process_id: Unique process id for this scraper (for parallel processing)
            headless: True to run the webdriver in headless mode
        """
        self.chrome_path = chrome_path
        self.chromedriver_path = chromedriver_path
        self.user = user
        self.process_id = process_id
        self.headless = headless
        self.driver = self.initialize_driver()
        self.login_calnet()

    def initialize_driver(self) -> WebDriver:
        """Initialize the webdriver instance (chromedriver).

        Returns:
            A configured WebDriver instance
        """
        chrome_executable_path = str(self.chrome_path / 'chrome.exe')
        chromedriver_executable_path = str(self.chromedriver_path / 'chromedriver.exe')
        chrome_service = webdriver.ChromeService(chromedriver_executable_path)
        chrome_options = webdriver.ChromeOptions()

        # Set Chrome to correct version (from Browser directory)
        chrome_options.binary_location = chrome_executable_path

        # Headless mode.
        if self.headless:
            chrome_options.add_argument("--headless")

        # Load or create a unique Chrome profile for this webdriver instance:
        # The primary (driver) scraper has process id 0 ("p0")
        # All parallel scrapers copy the primary scraper's Chrome profile to skip Duo Mobile login (using saved cookies)
        profile_name = hashlib.sha256(self.user.username.encode('utf-8')).hexdigest()
        profile_path = Path.cwd() / 'Profiles' / f'{profile_name}'
        profile_instance_path = profile_path / f'p{self.process_id}'  # The profile instance unique to this scraper
        if not os.path.exists(profile_instance_path):
            if self.process_id == 0:  # Base scraper/profile
                os.makedirs(profile_instance_path)
            else:  # Parallel scraper/profile
                base_instance_path = profile_path / 'p0'
                shutil.copytree(base_instance_path, profile_instance_path)  # Duplicate base profile
        chrome_options.add_argument(f"user-data-dir={profile_instance_path}")  # Use this profile for the scraper

        # Initialize driver
        driver = webdriver.Chrome(options=chrome_options, service=chrome_service)
        if not self.headless:
            driver.set_window_size(1280, 720)
        return driver

    def login_calnet(self) -> None:
        """Login to the user's Calnet account (and prompt for credentials if necessary).

        Note: incorrect login credentials and DUO mobile timeout cause a crash
        """
        if not self.user:
            print('CALNET LOGIN:\n')
            self.user = User.login_prompt()

        WebAutomation.login_calnet(self.driver, self.user)

    def scrape_request(self, request_id: int) -> WorkOrderRequest:
        """Scrape a single work request.

        Args:
            request_id: The id of the work request

        Returns:
            The scraped work request as a WorkOrderRequest object
        """
        WebAutomation.select_item(self.driver, 'WR')
        try:
            return WebAutomation.scrape_request(self.driver, request_id)
        except:
            return WorkOrderRequest(request_id)  # Return an empty request if request cannot be found

    def scrape_order(self, order_number: str) -> WorkOrder:
        """Scrape a single work order.

        Args:
            order_number: The order number of the work order

        Returns:
            The scraped work order as a WorkOrder object
        """
        WebAutomation.select_item(self.driver, 'WO')
        try:
            return WebAutomation.scrape_order(self.driver, order_number)
        except:
            return WorkOrder(order_number)  # Return an empty work order if none can be found

    def get_cookies(self) -> list[dict]:
        """Get a list of the webdriver cookies that are currently visible (cookies from the current domain).

        Returns:
            List of dictionary-representations of cookies
        """
        return self.driver.get_cookies()

    def add_cookies(self, cookies: list[dict]) -> None:
        """Add a list of cookies to the webdriver.\n
        NOTE: Selenium only supports adding cookies for the current domain.

        Args:
            cookies: List of dictionary-representations of cookies
        """
        for cookie in cookies:
            try:
                self.driver.add_cookie(cookie)
            except exceptions.InvalidCookieDomainException as e:
                print(f"failed to add cookie with name [{cookie.get('name')}] (wrong domain)")

    def close(self) -> None:
        """Close the webdriver."""
        self.driver.close()
