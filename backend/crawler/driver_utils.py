from selenium import webdriver  # Import from seleniumwire
from webdriver_manager.chrome import ChromeDriverManager
import os


def create_profile_driver(profile_path: str = "./chromeprofile") -> webdriver.Chrome:
    chrome_options = webdriver.ChromeOptions()
    agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36'
    chrome_options.add_experimental_option('excludeSwitches', ['enable-automation']) 
    # chrome_options.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2})
    chrome_options.add_argument("--disable-blink-features")
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--allow-running-insecure-content')
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('window-size=1920x1080')
    chrome_options.add_argument(f'--user-agent={agent}')
    chrome_options.add_argument(f"--user-data-dir={profile_path}")
    # mobile_emulation = { "deviceName": "Nexus 5" }
    # chrome_options.add_experimental_option("mobileEmulation", mobile_emulation)
    capabilities = chrome_options.to_capabilities()
    capabilities['goog:loggingPrefs'] = {'performance': 'ALL'}
    os.system("pgrep -f user-data-dir= | xargs kill -9")
    driver = webdriver.Chrome(ChromeDriverManager().install(),options=chrome_options)
    return driver

