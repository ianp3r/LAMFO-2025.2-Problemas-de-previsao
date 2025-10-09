from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.chrome.service import Service

import csv
import os
import argparse

import constants


def arguments():
    parser = argparse.ArgumentParser('Reclame Aqui Scraper')
    parser.add_argument('-i', '--id', help='Link ou ID da empresa no Reclame Aqui',
                        required=True)
    parser.add_argument('-p', '--pages', help='Número de páginas para coletar',
                        required=True, type=int)
    parser.add_argument('-f', '--file', help='Nome do arquivo em que será salvo os dados da coleta',
                        required=True)
    parser.add_argument('-b', '--browser', help='Browser que será utilizado para a coleta, (F) para Firefox e (C) para Chrome',
                        default="f")
    return parser.parse_args()


def driver_chrome():
    chrome_options = ChromeOptions()
    chrome_options.add_argument("--headless")  # melhor forma de ativar modo headless
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver


def driver_firefox():
    firefox_options = FirefoxOptions()
    firefox_options.add_argument("--headless")
    driver = webdriver.Firefox(executable_path=GeckoDriverManager().install(),
                               options=firefox_options)
    return driver


def define_browser(argument):
    if argument.lower() in ["c", "chrome"]:
        return driver_chrome()
    else:
        return driver_firefox()


def csv_writer(reclamacao, nome):
    caminho = f"Arquivos/{nome}.csv"
    with open(caminho, 'a', encoding='utf8', newline='') as arquivo_csv:
        writer = csv.DictWriter(arquivo_csv, fieldnames=constants.CSV_FILE_HEADERS)
        file_is_empty = os.stat(caminho).st_size == 0
        if file_is_empty:
            writer.writeheader()
        writer.writerow(reclamacao)


def format_url(url):
    url_str = str(url)
    return url_str.replace("(", "").replace(")", "").replace("'", "").replace(",", "")
