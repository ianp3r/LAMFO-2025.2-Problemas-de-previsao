from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

import pandas as pd
import datetime
import time


def setup_driver():
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service)

def raspar_dados_empresa(url_empresa: str):
    navegador = setup_driver()
    navegador.get(url_empresa)

    wait = WebDriverWait(navegador, 10)

    periodos = {
        'seis_meses': 'newPerformanceCard-tab-1',
        'doze_meses': 'newPerformanceCard-tab-2',
        'ano_2024': 'newPerformanceCard-tab-3',
        'ano_2023': 'newPerformanceCard-tab-4',
        'geral': 'newPerformanceCard-tab-5'
    }

    # Listas para armazenar os dados
    dados_coletados = []

    print("Iniciando a coleta de dados...")
    for nome_periodo, id_periodo in periodos.items():
        try:
            print(f"Coletando dados para o período: {nome_periodo}")

            # Clica no botão do período
            botao_periodo = wait.until(EC.element_to_be_clickable((By.ID, id_periodo)))
            botao_periodo.click()
            time.sleep(2)  # espera atualizar

            dados_periodo = {'periodo_nome': nome_periodo}

            # Captura todos os blocos de indicadores
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
                    partes = texto.split("nota média")
                    reclamacoes_avaliadas = bloco.find_element(By.TAG_NAME, "strong").text
                    nota_consumidor = partes[-1].split()[-1].replace(".", ",")
                    dados_periodo["num_avaliadas"] = reclamacoes_avaliadas
                    dados_periodo["nota_consumidor"] = nota_consumidor
                elif "voltariam a fazer negócio" in texto:
                    dados_periodo["novam_negoc"] = bloco.find_element(By.TAG_NAME, "strong").text
                elif "resolveu" in texto:
                    dados_periodo["indice_solucao"] = bloco.find_element(By.TAG_NAME, "strong").text
                elif "tempo médio de resposta" in texto:
                    dados_periodo["tempo_medio_resposta"] = bloco.find_element(By.TAG_NAME, "strong").text

            # Pega a data do período (ex: "01/04/2025 a 30/09/2025")
            try:
                periodo_texto = navegador.find_element(By.CSS_SELECTOR, "span.go2159339046").text
                dados_periodo["periodo_intervalo"] = periodo_texto.split("período de")[-1].strip()
            except NoSuchElementException:
                dados_periodo["periodo_intervalo"] = "N/A"

            dados_coletados.append(dados_periodo)

        except (NoSuchElementException, TimeoutException):
            print(f"Erro ao coletar período {nome_periodo}, pulando...")

    navegador.quit()
    print("Coleta finalizada.")

    if not dados_coletados:
        return pd.DataFrame()

    df_resumo = pd.DataFrame(dados_coletados)

    agora = datetime.datetime.now()
    df_resumo['data_coleta'] = agora.date()
    df_resumo['hora_coleta'] = agora.time()

    return df_resumo


# Salvar os dados em um arquivo Excel
def salvar_dados_excel(df_novos, caminho_arquivo, nome_planilha):
    try:
        df_existente = pd.read_excel(caminho_arquivo, sheet_name=nome_planilha)
        df_final = pd.concat([df_existente, df_novos], ignore_index=True)
    except FileNotFoundError:
        df_final = df_novos

    df_final.to_excel(caminho_arquivo, sheet_name=nome_planilha, index=False)
    print(f"Dados salvos em '{caminho_arquivo}', planilha '{nome_planilha}'")


if __name__ == "__main__":
    URL_ALVO = "https://www.reclameaqui.com.br/empresa/123-milhas/"
    df_coletado = raspar_dados_empresa(URL_ALVO)

    if not df_coletado.empty:
        print(df_coletado)
        salvar_dados_excel(df_coletado, "registro_indicadores_reclame_aqui.xlsx", "Registros")
