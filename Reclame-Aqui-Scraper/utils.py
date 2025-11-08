# utils.py

import argparse
import csv
import os
import constants

def arguments():
    """Analisa os argumentos da linha de comando."""
    parser = argparse.ArgumentParser('Reclame Aqui Scraper com ZenRows')
    parser.add_argument('-i', '--id', help='ID da empresa no Reclame Aqui (ex: "ifood")', required=True)
    parser.add_argument('-p', '--pages', help='Número de páginas de listagem para coletar URLs', required=True, type=int)
    parser.add_argument('-f', '--file', help='Nome do arquivo CSV de saída (sem extensão)', required=True)
    return parser.parse_args()

def csv_writer(reclamacao_dict, nome_arquivo):
    """Escreve uma linha de dados no arquivo CSV."""
    caminho = f"Arquivos/{nome_arquivo}.csv"
    file_exists = os.path.isfile(caminho)
    
    with open(caminho, 'a', encoding='utf8', newline='') as arquivo_csv:
        writer = csv.DictWriter(arquivo_csv, fieldnames=constants.CSV_FILE_HEADERS)
        if not file_exists or os.stat(caminho).st_size == 0:
            writer.writeheader()
        writer.writerow(reclamacao_dict)

def create_folders():
    """Cria as pastas 'Arquivos' e 'Database' se não existirem."""
    os.makedirs('Arquivos', exist_ok=True)
    os.makedirs('Database', exist_ok=True)