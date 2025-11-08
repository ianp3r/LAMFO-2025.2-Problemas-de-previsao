# scraper.py

import requests
from bs4 import BeautifulSoup
import logging
import constants
from reclamacao import Reclamacao

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def _fetch_html_with_zenrows(target_url: str):
    """Faz uma requisição para a API do ZenRows e retorna o conteúdo HTML."""
    params = {
        "url": target_url,
        "apikey": constants.ZENROWS_API_KEY,
        "js_render": "true",  # Essencial para carregar conteúdo dinâmico
    }
    try:
        response = requests.get(constants.ZENROWS_URL, params=params, timeout=60)
        response.raise_for_status()  # Lança exceção para códigos de erro (4xx ou 5xx)
        return response.text
    except requests.exceptions.RequestException as e:
        logging.error(f"Falha na requisição para a URL {target_url}: {e}")
        return None

def _get_text_from_soup(soup, selector):
    """Função auxiliar para extrair texto de um elemento de forma segura."""
    element = soup.select_one(selector)
    return element.get_text(strip=True) if element else ""

def collect_complaint_urls(company_id: str, num_pages: int):
    """Coleta as URLs de todas as reclamações das páginas de listagem."""
    collected_urls = []
    for page_num in range(1, num_pages + 1):
        list_url = constants.COMPLAIN_LIST_BASE_URL.format(company_id, page_num)
        logging.info(f"Coletando URLs da página {page_num}: {list_url}")
        
        html = _fetch_html_with_zenrows(list_url)
        if not html:
            logging.warning(f"Não foi possível obter o HTML da página {page_num}. Pulando.")
            continue

        soup = BeautifulSoup(html, "html.parser")
        links = soup.select(constants.COMPLAIN_URL_SELECTOR)
        
        if not links:
            logging.info(f"Nenhuma reclamação encontrada na página {page_num}. Interrompendo coleta.")
            break

        for link in links:
            href = link.get('href')
            if href:
                full_url = constants.BASE_URL + href if href.startswith('/') else href
                collected_urls.append(full_url)
    
    return list(set(collected_urls)) # Remove duplicatas

def scrape_complaint_details(complaint_url: str):
    """Extrai os detalhes de uma única página de reclamação."""
    logging.info(f"Extraindo dados de: {complaint_url}")
    html = _fetch_html_with_zenrows(complaint_url)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")

    try:
        reclamacao_obj = Reclamacao(
            url=complaint_url,
            titulo=_get_text_from_soup(soup, constants.COMPLAIN_TITLE_SELECTOR),
            texto=_get_text_from_soup(soup, constants.COMPLAIN_TEXT_SELECTOR),
            status=_get_text_from_soup(soup, constants.COMPLAIN_STATUS_SELECTOR),
            local=_get_text_from_soup(soup, constants.COMPLAIN_LOCAL_SELECTOR),
            data_hora=_get_text_from_soup(soup, constants.COMPLAIN_DATE_SELECTOR),
            problem_type=_get_text_from_soup(soup, constants.COMPLAIN_CATEGORY_3_SELECTOR),
            product_type=_get_text_from_soup(soup, constants.COMPLAIN_CATEGORY_2_SELECTOR),
            category=_get_text_from_soup(soup, constants.COMPLAIN_CATEGORY_1_SELECTOR)
        )
        return reclamacao_obj
    except Exception as e:
        logging.error(f"Erro ao extrair dados da URL {complaint_url}: {e}")
        return None