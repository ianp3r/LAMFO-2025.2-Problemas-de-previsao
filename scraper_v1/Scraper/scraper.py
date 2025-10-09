# --- IMPORTAÇÕES ---
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

import pandas as pd
import datetime
import time
import re


# --- FUNÇÃO PARA CONFIGURAR O DRIVER (MODERNIZADA) ---
def setup_driver():
    """Configura e retorna uma instância do WebDriver para o Firefox."""
    print("Configurando o driver do Firefox (usando o Selenium Manager)...")
    # Selenium 4.6+ gerencia o GeckoDriver automaticamente.
    return webdriver.Firefox() # <-- ALTERAÇÃO PRINCIPAL


# --- FUNÇÃO PARA EXTRAIR DADOS DE UMA EMPRESA ---
def raspar_dados_empresa(url_empresa: str):
    """Raspa os dados de reputação de uma empresa no Reclame Aqui."""
    navegador = setup_driver()
    navegador.get(url_empresa)

    wait = WebDriverWait(navegador, 15)

    """
    try:
        print("Procurando o banner de cookies para aceitá-lo...")
        botao_cookies = wait.until(EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler")))
        botao_cookies.click()
        print("Banner de cookies fechado com sucesso.")
        time.sleep(1)
    except TimeoutException:
        print("Banner de cookies não foi encontrado (provavelmente já foi aceito ou não existe).")
    """

    periodos = {
        'seis_meses': 'newPerformanceCard-tab-1',
        'doze_meses': 'newPerformanceCard-tab-2',
        'ano_2025': 'newPerformanceCard-tab-3', 
        'ano_2024': 'newPerformanceCard-tab-4',
        'geral': 'newPerformanceCard-tab-5'
    }

    dados_coletados = []

    print("Iniciando a coleta de dados...")
    for nome_periodo, id_periodo in periodos.items():
        try:
            print(f"Coletando dados para o período: {nome_periodo}")
            botao_periodo = wait.until(EC.element_to_be_clickable((By.ID, id_periodo)))
            navegador.execute_script("arguments[0].click();", botao_periodo)
            time.sleep(2)

            dados_periodo = {'periodo_nome': nome_periodo}
            blocos = navegador.find_elements(By.CSS_SELECTOR, "div.go4263471347")

            for bloco in blocos:
                texto = bloco.text.strip()
                if not texto:
                    continue

                if "recebeu" in texto:
                    dados_periodo["num_reclamacoes"] = bloco.find_element(By.TAG_NAME, "strong").text
                elif "Respondeu" in texto:
                    dados_periodo["perc_recl_resp"] = bloco.find_element(By.TAG_NAME, "strong").text
                elif "aguardando resposta" in texto:
                    dados_periodo["reclamacoes_aguardando"] = bloco.find_element(By.TAG_NAME, "strong").text
                elif "avaliadas" in texto:
                    reclamacoes_avaliadas = bloco.find_element(By.TAG_NAME, "strong").text
                    nota_match = re.search(r"nota média.*?([\d.,]+)", texto)
                    nota_consumidor = nota_match.group(1) if nota_match else "N/A"
                    dados_periodo["num_avaliadas"] = reclamacoes_avaliadas
                    dados_periodo["nota_consumidor"] = nota_consumidor
                elif "voltariam a fazer negócio" in texto:
                    dados_periodo["novam_negoc"] = bloco.find_element(By.TAG_NAME, "strong").text
                elif "resolveu" in texto:
                    dados_periodo["indice_solucao"] = bloco.find_element(By.TAG_NAME, "strong").text
                elif "tempo médio de resposta" in texto:
                    dados_periodo["tempo_medio_resposta"] = bloco.find_element(By.TAG_NAME, "strong").text

            try:
                periodo_texto = navegador.find_element(By.CSS_SELECTOR, "span.go2159339046").text
                dados_periodo["periodo_intervalo"] = periodo_texto.split("período de")[-1].strip()
            except NoSuchElementException:
                dados_periodo["periodo_intervalo"] = "N/A"

            dados_coletados.append(dados_periodo)

        except (NoSuchElementException, TimeoutException) as e:
            print(f"Erro ao coletar dados para o período {nome_periodo}: {e}. Pulando...")

    navegador.quit()
    print("Coleta finalizada.")

    if not dados_coletados:
        return pd.DataFrame()

    df_resumo = pd.DataFrame(dados_coletados)

    agora = datetime.datetime.now()
    df_resumo['data_coleta'] = agora.date()
    df_resumo['hora_coleta'] = agora.time()

    return df_resumo


# --- FUNÇÃO PARA SALVAR OS DADOS ---
def salvar_dados_excel(df_novos, url_empresa, nome_planilha="Registros"):
    """Salva o DataFrame em um arquivo Excel, concatenando com dados existentes se o arquivo já existir."""
    if df_novos.empty:
        print("Nenhum dado novo para salvar.")
        return

    nome_empresa = url_empresa.strip("/").split("/")[-1]
    caminho_arquivo = f"{nome_empresa}.xlsx"

    try:
        df_existente = pd.read_excel(caminho_arquivo, sheet_name=nome_planilha)
        df_final = pd.concat([df_existente, df_novos], ignore_index=True)
    except FileNotFoundError:
        df_final = df_novos

    df_final.to_excel(caminho_arquivo, sheet_name=nome_planilha, index=False)
    print(f"✅ Dados salvos com sucesso em '{caminho_arquivo}', na planilha '{nome_planilha}'")


# --- EXECUÇÃO PRINCIPAL ---
if __name__ == "__main__":
    URL_ALVO = "https://www.reclameaqui.com.br/empresa/prudential-do-brasil-seguros-de-vida/"

    df_coletado = raspar_dados_empresa(URL_ALVO)

    if not df_coletado.empty:
        print("\n--- Dados Coletados ---")
        print(df_coletado)
        salvar_dados_excel(df_coletado, URL_ALVO)