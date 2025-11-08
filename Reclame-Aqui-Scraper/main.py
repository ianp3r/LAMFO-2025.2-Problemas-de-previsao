# main.py

import sys
import time
import logging
from contextlib import closing

import constants
import database
import scraper
import utils

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    """Função principal que orquestra o processo de scraping."""
    
    # 1. Validação e Configuração Inicial
    if constants.ZENROWS_API_KEY == "SUA_CHAVE_API_ZENROWS":
        logging.error("ERRO: Por favor, configure sua ZENROWS_API_KEY no arquivo constants.py.")
        sys.exit(1)

    args = utils.arguments()
    utils.create_folders()
    
    try:
        with closing(database.db_conn()) as (conn, cursor):
            # 2. FASE 1: Coleta de URLs
            logging.info(f"[FASE 1] Iniciando coleta de URLs para a empresa '{args.id}' em {args.pages} página(s).")
            complaint_urls = scraper.collect_complaint_urls(args.id, args.pages)
            
            if not complaint_urls:
                logging.warning("Nenhuma URL foi coletada. Encerrando o script.")
                sys.exit(0)
            
            logging.info(f"{len(complaint_urls)} URLs únicas encontradas. Salvando no banco de dados...")
            database.db_writer(complaint_urls, args.id, conn, cursor)
            logging.info("URLs salvas com sucesso.")
            
            # 3. FASE 2: Extração de Detalhes
            logging.info("\n[FASE 2] Iniciando extração de detalhes das reclamações.")
            cursor.execute(constants.SQL_SELECT_URL, (args.id,))
            urls_to_scrape = [row[0] for row in cursor.fetchall()]
            
            total_urls = len(urls_to_scrape)
            logging.info(f"Encontradas {total_urls} reclamações para extrair.")
            
            for i, url in enumerate(urls_to_scrape):
                logging.info(f"Processando URL {i+1}/{total_urls}...")
                reclamacao_obj = scraper.scrape_complaint_details(url)
                
                if reclamacao_obj and reclamacao_obj.titulo:
                    # Sucesso
                    utils.csv_writer(reclamacao_obj.to_dict(), args.file)
                    database.update_status(cursor, constants.SQL_SUCCESS_STATUS, url, args.id)
                    logging.info(f"Dados salvos para: {url}")
                else:
                    # Erro
                    database.update_status(cursor, constants.SQL_ERROR_STATUS, url, args.id)
                    logging.error(f"Falha ao extrair dados de: {url}")

                conn.commit()
                time.sleep(1) # Pausa para evitar sobrecarregar a API

    except Exception as e:
        logging.critical(f"Ocorreu um erro fatal: {e}", exc_info=True)
        sys.exit(1)

    logging.info("\n[✓] Processo de scraping concluído com sucesso!")


if __name__ == '__main__':
    main()