import os
import subprocess
import sys
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


ROOT_DIR = Path(__file__).resolve().parent.parent
BASE_URL = "http://127.0.0.1:8765"


class UISmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server_process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8765"],
            cwd=ROOT_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
        cls._wait_for_server()
        cls.driver = cls._create_driver()
        cls.wait = WebDriverWait(cls.driver, 20)

    @classmethod
    def tearDownClass(cls):
        driver = getattr(cls, "driver", None)
        if driver is not None:
            driver.quit()

        process = getattr(cls, "server_process", None)
        if process is not None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()

    @classmethod
    def _wait_for_server(cls):
        deadline = time.time() + 30
        last_error = None
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(BASE_URL, timeout=2) as response:
                    if response.status == 200:
                        return
            except (urllib.error.URLError, TimeoutError) as exc:
                last_error = exc
                time.sleep(0.5)
        raise RuntimeError(f"Server did not start in time: {last_error}")

    @classmethod
    def _create_driver(cls):
        edge_binary = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
        if edge_binary.exists():
            edge_options = EdgeOptions()
            edge_options.binary_location = str(edge_binary)
            edge_options.add_argument("--headless=new")
            edge_options.add_argument("--window-size=1440,1200")
            edge_options.add_argument("--disable-gpu")
            return webdriver.Edge(options=edge_options)

        chrome_binary = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
        if chrome_binary.exists():
            chrome_options = ChromeOptions()
            chrome_options.binary_location = str(chrome_binary)
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--window-size=1440,1200")
            chrome_options.add_argument("--disable-gpu")
            return webdriver.Chrome(options=chrome_options)

        raise unittest.SkipTest("No supported browser binary found for Selenium smoke tests.")

    def test_dashboard_loads_and_navigates_to_crafting(self):
        self.driver.get(f"{BASE_URL}/dashboard")
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "header.steam-header")))
        self.assertEqual(
            self.driver.find_element(By.CSS_SELECTOR, "#dashboard-page.active h1").text,
            "Обзор сессии",
        )

        crafting_nav = self.driver.find_element(By.CSS_SELECTOR, "a.nav-item[data-page='crafting']")
        crafting_nav.click()
        self.wait.until(
            lambda driver: "active" in driver.find_element(By.ID, "crafting-page").get_attribute("class").split()
        )
        self.wait.until(
            lambda driver: len(driver.find_elements(By.CSS_SELECTOR, "#crafting-grid .recipe-card")) > 0
        )
        self.assertEqual(
            self.driver.find_element(By.CSS_SELECTOR, "#crafting-page.active h1").text,
            "Рецепты крафта",
        )

    def test_dashboard_navigates_to_settings_and_shows_prompt_form(self):
        self.driver.get(f"{BASE_URL}/dashboard")
        settings_nav = self.wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a.nav-item[data-page='settings']"))
        )
        settings_nav.click()

        self.wait.until(
            lambda driver: "active" in driver.find_element(By.ID, "settings-page").get_attribute("class").split()
        )
        self.wait.until(EC.presence_of_element_located((By.ID, "dashboard-prompt-form")))

        self.assertEqual(
            self.driver.find_element(By.CSS_SELECTOR, "#settings-page.active h1").text,
            "Настройки",
        )
        self.assertTrue(self.driver.find_element(By.ID, "dashboard-state-prompt").is_displayed())
        self.assertIn(
            "role-playing Minecraft game companion",
            self.driver.find_element(By.ID, "dashboard-state-prompt").get_attribute("value"),
        )

    def test_wiki_search_shows_recipe_grid(self):
        self.driver.get(f"{BASE_URL}/admin/wiki")
        search_input = self.wait.until(EC.presence_of_element_located((By.ID, "searchInput")))
        search_input.clear()
        search_input.send_keys("палка")
        search_input.send_keys(Keys.ENTER)

        self.wait.until(lambda driver: driver.find_element(By.ID, "resultArea").value_of_css_property("display") != "none")
        self.wait.until(lambda driver: driver.find_element(By.ID, "recipeName").text.strip() != "")

        self.assertEqual(self.driver.find_element(By.ID, "recipeName").text.strip(), "Палка")
        self.assertGreaterEqual(len(self.driver.find_elements(By.CSS_SELECTOR, "#craftingGrid .slot-filled")), 2)


if __name__ == "__main__":
    unittest.main()
