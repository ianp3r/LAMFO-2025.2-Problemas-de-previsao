from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

import pandas as pd
import datetime
import time
import re
import os

def setup_driver():
    """Configura e retorna uma instância do WebDriver para o Firefox."""
    print("Configurando o driver do Firefox (usando o Selenium Manager)...")
    return webdriver.Firefox()

def raspar_dados_consumidor(url_empresa: str):
    """Raspa os dados de uma empresa no Consumidor.gov.br."""
    navegador = setup_driver()
    navegador.get(url_empresa)
    wait = WebDriverWait(navegador, 20)

    print("Aguardando o carregamento da página e dos indicadores...")
    wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "abas-perfil")))

    periodos = {
        'ultimos_30_dias': 'link_tab_dia',
        'ultimos_6_meses': 'link_tab_mes',
        # TODO: The year is hardcoded based on the current date. 
        # I might need to make this dynamic in the future.
        'ano_2025': '2025', 
        'geral': 'link_tab_ano'
    }

    dados_coletados = []

    def _extrair_indicador(seletor_css):
        try:

            elemento = WebDriverWait(navegador, 5).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, seletor_css))
            )

            texto_limpo = re.search(r'[\d,.]+', elemento.text)
            return texto_limpo.group(0) if texto_limpo else "N/A"
        except (NoSuchElementException, TimeoutException):
            return "N/A"

    print("Iniciando a coleta de dados por período...")
    for nome_periodo, seletor_aba in periodos.items():
        try:
            print(f"--- Coletando dados para o período: {nome_periodo} ---")
            
            if 'ano_' in nome_periodo:

                botao_periodo = wait.until(
                    EC.element_to_be_clickable((By.XPATH, f"//ul[contains(@class, 'abas-perfil')]//a[contains(text(), '{seletor_aba}')]"))
                )
            else:

                botao_periodo = wait.until(EC.element_to_be_clickable((By.ID, seletor_aba)))
            
            navegador.execute_script("arguments[0].click();", botao_periodo)

            time.sleep(4) 

            dados_periodo = {'periodo_nome': nome_periodo}
            
            # 1. Total de Reclamações Finalizadas
            dados_periodo['total_reclamacoes_finalizadas'] = _extrair_indicador("div.tab-pane.active span.indicadorTotal")

            # 2. Índice de Solução
            dados_periodo['indice_solucao'] = _extrair_indicador("div.tab-pane.active div[id^='solucao'] .fonteResultado")
            
            # 3. Satisfação com o Atendimento
            dados_periodo['satisfacao_atendimento'] = _extrair_indicador("div.tab-pane.active div[id^='atendimento'] .fonteResultado")
            
            # 4. Reclamações Respondidas
            dados_periodo['reclamacoes_respondidas'] = _extrair_indicador("div.tab-pane.active div[id^='respondidas'] .fonteResultado")
            
            # 5. Prazo Médio de Respostas (this one has a slightly different class name)
            dados_periodo['prazo_medio_resposta'] = _extrair_indicador("div.tab-pane.active div[id^='prazo'] .fonteResultadoDia")
            
            dados_coletados.append(dados_periodo)
            print("Dados do período coletados com sucesso.")

        except (NoSuchElementException, TimeoutException) as e:
            print(f"Erro ao processar o período {nome_periodo}: A aba pode não existir ou a página não carregou. {e}")
            continue
    
    navegador.quit()
    print("\nColeta finalizada.")

    if not dados_coletados:
        return pd.DataFrame()

    df_resumo = pd.DataFrame(dados_coletados)

    agora = datetime.datetime.now()
    df_resumo['data_coleta'] = agora.date()
    df_resumo['hora_coleta'] = agora.time().strftime('%H:%M:%S')

    colunas_ordenadas = [
        'periodo_nome', 'total_reclamacoes_finalizadas', 'indice_solucao',
        'satisfacao_atendimento', 'reclamacoes_respondidas', 'prazo_medio_resposta',
        'data_coleta', 'hora_coleta'
    ]
    colunas_presentes = [col for col in colunas_ordenadas if col in df_resumo.columns]
    df_resumo = df_resumo[colunas_presentes]
    
    return df_resumo

def salvar_dados_excel(df_novos, nome_empresa, nome_planilha="Registros_ConsumidorGov"):
    """Salva o DataFrame em um arquivo Excel, concatenando com dados existentes."""
    if df_novos.empty:
        print("Nenhum dado novo para salvar.")
        return

    nome_arquivo_limpo = re.sub(r'[^a-zA-Z0-9]', '_', nome_empresa)
    caminho_arquivo = f"{nome_arquivo_limpo}_consumidor_gov.xlsx"

    try:
        if os.path.exists(caminho_arquivo):
            df_existente = pd.read_excel(caminho_arquivo, sheet_name=nome_planilha)
            df_final = pd.concat([df_existente, df_novos], ignore_index=True)
            print(f"Arquivo '{caminho_arquivo}' encontrado. Adicionando novos registros...")
        else:
            df_final = df_novos
            print(f"Criando novo arquivo '{caminho_arquivo}'...")

        df_final.to_excel(caminho_arquivo, sheet_name=nome_planilha, index=False)
        print(f"✅ Dados salvos com sucesso em '{caminho_arquivo}', na planilha '{nome_planilha}'")

    except Exception as e:
        print(f"Ocorreu um erro ao salvar o arquivo Excel: {e}")

if __name__ == "__main__":
    URL_ALVO = "https://www.consumidor.gov.br/pages/empresa/20201207002607916/perfil;acoesSessaoCookie=21B42BF4450F4583D57BD9B8931BDB2C"
    NOME_EMPRESA = "Prudential do Brasil"
    
    df_coletado = raspar_dados_consumidor(URL_ALVO)

    if not df_coletado.empty:
        print("\n--- Dados Coletados ---")
        print(df_coletado.to_string())
        salvar_dados_excel(df_coletado, NOME_EMPRESA)