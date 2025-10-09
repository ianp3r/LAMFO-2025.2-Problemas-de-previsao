from utils import define_browser, arguments
from database import db_conn
from scraper import scrape_page
from url_collector import url_collector
import sys
import traceback


def main():
    print('\n-- RECLAME AQUI SCRAPER --')

    try:
        # Parse CLI arguments
        args = arguments()
        args.pages = min(args.pages, 50)

        # Start browser
        driver = define_browser(args.browser)

        # Connect to database
        conn, cursor = db_conn()

        # Collect complaint URLs
        print(f"[+] Collecting URLs for '{args.id}' (up to {args.pages} pages)")
        coletor = url_collector(driver, args.file, args.id, args.pages, conn, cursor)

        # Scrape complaint details
        print(f"[+] Starting scraping of collected URLs...")
        scrape_page(driver, page_url=coletor.url)

        print("[✓] Scraping complete!")

    except Exception as e:
        print("[!] An error occurred:")
        traceback.print_exc()
        sys.exit(1)

    finally:
        # Clean shutdown
        try:
            if driver:
                driver.quit()
        except:
            pass
        try:
            if conn:
                conn.close()
        except:
            pass


if __name__ == '__main__':
    main()
