# reclame_aqui_scraper.py

import argparse
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager


def create_driver(browser_choice):
    if browser_choice.lower() == 'c':
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    else:
        options = webdriver.FirefoxOptions()
        options.add_argument("--headless")
        service = FirefoxService(GeckoDriverManager().install())
        driver = webdriver.Firefox(service=service, options=options)
    return driver


def scrape_page(driver, page_url):
    driver.get(page_url)
    wait = WebDriverWait(driver, 10)

    try:
        wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "article.sc-1pe7b5t-0")))
    except TimeoutException:
        print(f"[!] Timeout waiting for complaints to load on {page_url}")
        return []

    complaints = driver.find_elements(By.CSS_SELECTOR, "article.sc-1pe7b5t-0")
    data = []

    for complaint in complaints:
        try:
            url = complaint.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
            content = complaint.find_element(By.CSS_SELECTOR, "p.sc-1pe7b5t-1").text
            status = complaint.find_element(By.CSS_SELECTOR, "span.sc-1pe7b5t-4").text
            date_loc = complaint.find_element(By.CSS_SELECTOR, "span.sc-1pe7b5t-3").text
        except NoSuchElementException:
            continue

        # Separate date and location if possible
        if " - " in date_loc:
            date, location = date_loc.split(" - ", 1)
        else:
            date, location = date_loc, ""

        # ✅ Now log the full URL, not just the ID
        print(f"[LOG] Acessando: {url}")

        data.append({
            "URL": url,
            "Content": content,
            "Status": status,
            "Date": date,
            "Location": location
        })
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--institution", required=True, help="Company name (slug)")
    parser.add_argument("-p", "--pages", type=int, default=1, help="Number of pages to scrape (max 50)")
    parser.add_argument("-f", "--file", default="output", help="Output Excel filename")
    parser.add_argument("-b", "--browser", default="c", help="Browser: C (Chrome) or F (Firefox)")
    args = parser.parse_args()

    # Enforce page limit
    args.pages = min(args.pages, 50)
    base_url = f"https://www.reclameaqui.com.br/empresa/{args.institution}/lista-reclamacoes/?pagina="

    driver = create_driver(args.browser)
    all_data = []

    try:
        for page in range(1, args.pages + 1):
            print(f"[+] Scraping page {page} ...")
            url = base_url + str(page)
            page_data = scrape_page(driver, url)
            if not page_data:
                print("[!] No complaints found — stopping.")
                break
            all_data.extend(page_data)
            time.sleep(2)  # avoid overloading the site
    finally:
        driver.quit()

    if all_data:
        df = pd.DataFrame(all_data)
        out_path = f"{args.file}.xlsx"
        df.to_excel(out_path, index=False)
        print(f"[✓] Saved {len(all_data)} complaints to {out_path}")
    else:
        print("[!] No data scraped.")


if __name__ == "__main__":
    main()
