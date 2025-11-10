# Reclame-Aqui / ZenRows Scrapers

Conjunto de scrapers em Python para coletar reclamações do Reclame Aqui (várias versões) e indicadores do Consumidor.gov.br.  
Inclui variações que usam Selenium (driver local) e ZenRows (API de rendering).

Principais scripts
- [Reclame-Aqui-Scraper/main.py](Reclame-Aqui-Scraper/main.py) — Orquestra coleta de URLs e extração de detalhes via ZenRows. Usa [`utils.arguments`](Reclame-Aqui-Scraper/utils.py).
- [Reclame-Aqui-Scraper/scraper.py](Reclame-Aqui-Scraper/scraper.py) — Funções: [`collect_complaint_urls`](Reclame-Aqui-Scraper/scraper.py), [`scrape_complaint_details`](Reclame-Aqui-Scraper/scraper.py).
- [Reclame-Aqui-Scraper/constants.py](Reclame-Aqui-Scraper/constants.py) — Selectors e SQL.
- [Reclame-Aqui-Scraper/utils.py](Reclame-Aqui-Scraper/utils.py) — Escrita CSV via [`utils.csv_writer`](Reclame-Aqui-Scraper/utils.py).
- [Reclame-Aqui-Scraper/database.py](Reclame-Aqui-Scraper/database.py) — DB helpers: [`db_conn`](Reclame-Aqui-Scraper/database.py), [`db_writer`](Reclame-Aqui-Scraper/database.py).
- [Reclame-Aqui-Scraper/url_collector.py](Reclame-Aqui-Scraper/url_collector.py) — Coleta URLs com Selenium: [`url_collector`](Reclame-Aqui-Scraper/url_collector.py).
- [Reclame-Aqui-Scraper/Reclamacao.py](Reclame-Aqui-Scraper/Reclamacao.py) — Modelo `Reclamacao`.

Versões alternativas
- [zenrows_version/main.py](zenrows_version/main.py) — Versão que também usa ZenRows; veja [`zenrows_version/constants.ZENROWS_API_KEY`](zenrows_version/constants.py).
- [zenrows_version/scraper.py](zenrows_version/scraper.py) — Implementação compatível com ZenRows (`_fetch_html_with_zenrows`).
- [scraper_v1/Scraper/scraper.py](scraper_v1/Scraper/scraper.py) — Versão Selenium (Firefox).
- [scraper_v1/Scraper/scraper_multiplo.py](scraper_v1/Scraper/scraper_multiplo.py) — Reuso de navegador para múltiplas empresas; veja [`setup_driver`](scraper_v1/Scraper/scraper_multiplo.py) e [`raspar_dados_empresa`](scraper_v1/Scraper/scraper_multiplo.py).
- [scraper_v1/Scraper/scraper_consumidorgov.py](scraper_v1/Scraper/scraper_consumidorgov.py) — Scraper para consumidor.gov.br (Selenium).

Pré-requisitos
- Python 3.8+
- pip packages (ex.: requests, beautifulsoup4, selenium, webdriver-manager, pandas)
- Navegador Chrome ou Firefox instalado (para versões Selenium)
- Chave ZenRows (se usar ZenRows): configure [`ZENROWS_API_KEY`](zenrows_version/constants.py)

Instalação rápida
```sh
python -m pip install -r requirements.txt  # se houver requirements.txt
pip install requests beautifulsoup4 selenium webdriver-manager pandas
