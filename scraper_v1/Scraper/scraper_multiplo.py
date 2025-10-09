# 1. Importar as bibliotecas necessárias
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
import re


# --- FUNÇÃO PARA CONFIGURAR O DRIVER ---
# (Sem alterações)
def setup_driver():
    """Configura e retorna uma instância do WebDriver do Chrome."""
    print("Configurando o navegador...")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service)


# --- FUNÇÃO PARA EXTRAIR DADOS DE UMA EMPRESA ---
# (Alteração: Recebe o 'navegador' como argumento para não criar um novo a cada vez)
def raspar_dados_empresa(navegador, url_empresa: str):
    """
    Navega até a URL de uma empresa e extrai os dados de reputação de diferentes períodos.
    Reutiliza a instância do navegador fornecida.
    """
    navegador.get(url_empresa)
    wait = WebDriverWait(navegador, 10)

    # Períodos disponíveis (IDs dos botões)
    periodos = {
        'seis_meses': 'newPerformanceCard-tab-1',
        'doze_meses': 'newPerformanceCard-tab-2',
        'ano_2024': 'newPerformanceCard-tab-3',
        'ano_2023': 'newPerformanceCard-tab-4',
        'geral': 'newPerformanceCard-tab-5'
    }

    dados_coletados = []

    print(f"Iniciando a coleta para: {url_empresa}")
    for nome_periodo, id_periodo in periodos.items():
        try:
            # print(f"  - Coletando dados para o período: {nome_periodo}")

            # Clica no botão do período e espera os dados atualizarem
            botao_periodo = wait.until(EC.element_to_be_clickable((By.ID, id_periodo)))
            botao_periodo.click()
            time.sleep(2)  # Pausa para garantir que o conteúdo da página foi atualizado

            dados_periodo = {'periodo_nome': nome_periodo}

            # Encontra todos os blocos de dados de performance
            blocos = navegador.find_elements(By.CSS_SELECTOR, "div.go4263471347")

            for bloco in blocos:
                texto = bloco.text.strip()
                if not texto:
                    continue
                
                # Extrai cada métrica baseada no texto do bloco
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
            
            # Extrai o intervalo de datas do período
            try:
                periodo_texto = navegador.find_element(By.CSS_SELECTOR, "span.go2159339046").text
                dados_periodo["periodo_intervalo"] = periodo_texto.split("período de")[-1].strip()
            except NoSuchElementException:
                dados_periodo["periodo_intervalo"] = "N/A"

            dados_coletados.append(dados_periodo)

        except (NoSuchElementException, TimeoutException) as e:
            print(f"    -> Erro ao coletar período {nome_periodo}, pulando... (Erro: {e})")

    if not dados_coletados:
        return pd.DataFrame()

    df_resumo = pd.DataFrame(dados_coletados)

    # Adiciona data e hora da coleta
    agora = datetime.datetime.now()
    df_resumo['data_coleta'] = agora.date()
    df_resumo['hora_coleta'] = agora.time()

    return df_resumo


# --- FUNÇÃO PARA SALVAR OS DADOS ---
# (Sem alterações)
def salvar_dados_excel(df_novos, url_empresa, nome_planilha="Registros"):
    """
    Salva o DataFrame em um arquivo Excel. O nome do arquivo é derivado da URL.
    Se o arquivo já existir, os novos dados são adicionados.
    """
    if df_novos.empty:
        print(f"Nenhum dado novo para salvar para a empresa: {url_empresa}")
        return

    # Extrai o nome da empresa da URL para usar como nome do arquivo
    nome_empresa = url_empresa.strip("/").split("/")[-1]
    caminho_arquivo = f"{nome_empresa}.xlsx"

    try:
        # Tenta ler o arquivo existente
        df_existente = pd.read_excel(caminho_arquivo, sheet_name=nome_planilha)
        # Concatena os dados existentes com os novos
        df_final = pd.concat([df_existente, df_novos], ignore_index=True)
    except FileNotFoundError:
        # Se o arquivo não existe, o DataFrame final é apenas o novo
        df_final = df_novos

    df_final.to_excel(caminho_arquivo, sheet_name=nome_planilha, index=False)
    print(f"✅ Dados salvos/atualizados em '{caminho_arquivo}'")


# --- EXECUÇÃO PRINCIPAL ---
if __name__ == "__main__":
    
    
    lista_de_urls = [
        "https://www.reclameaqui.com.br/empresa/banco-do-brasil/",
        "https://www.reclameaqui.com.br/empresa/bradesco/",
        "https://www.reclameaqui.com.br/empresa/itau-unibanco/",
        "https://www.reclameaqui.com.br/empresa/santander/",
        "https://www.reclameaqui.com.br/empresa/caixa-economica-federal/",
        "https://www.reclameaqui.com.br/empresa/banco-mercantil-do-brasil/",
        "https://www.reclameaqui.com.br/empresa/citibank/",
        "https://www.reclameaqui.com.br/empresa/banco-safra/",
        "https://www.reclameaqui.com.br/empresa/banco-pan/",
        "https://www.reclameaqui.com.br/empresa/banco-daycoval/",
        "https://www.reclameaqui.com.br/empresa/banco-abc-brasil/",
        "https://www.reclameaqui.com.br/empresa/banco-bv/",
        "https://www.reclameaqui.com.br/empresa/banrisul/",
        "https://www.reclameaqui.com.br/empresa/banco-da-amazonia/",
        "https.www.reclameaqui.com.br/empresa/banco-do-nordeste-do-brasil-s-a/",
        "https://www.reclameaqui.com.br/empresa/banco-alfa/",
        "https://www.reclameaqui.com.br/empresa/banco-industrial-do-brasil-sa/",
        "https://www.reclameaqui.com.br/empresa/banco-bmg/",
        "https://www.reclameaqui.com.br/empresa/tribanco/",
        "https://www.reclameaqui.com.br/empresa/banco-master/",
        "https://www.reclameaqui.com.br/empresa/nubank/",
        "https://www.reclameaqui.com.br/empresa/banco-inter/",
        "https://www.reclameaqui.com.br/empresa/c6-bank/",
        "https://www.reclameaqui.com.br/empresa/mercado-pago/",
        "https://www.reclameaqui.com.br/empresa/picpay/",
        "https://www.reclameaqui.com.br/empresa/pagbank-pagseguro/",
        "https://www.reclameaqui.com.br/empresa/banco-btg-pactual/",
        "https://www.reclameaqui.com.br/empresa/banco-original/",
        "https://www.reclameaqui.com.br/empresa/superdigital/",
        "https://www.reclameaqui.com.br/empresa/neon-pagamentos/",
        "https://www.reclameaqui.com.br/empresa/will-bank/",
        "https://www.reclameaqui.com.br/empresa/banco-bs2/",
        "https://www.reclameaqui.com.br/empresa/banco-bari/",
        "https://www.reclameaqui.com.br/empresa/xp-investimentos/",
        "https://www.reclameaqui.com.br/empresa/z1-conta-digital-para-adolescentes/",
        "https://www.reclameaqui.com.br/empresa/ton/",
        "https://www.reclameaqui.com.br/empresa/banco-sofisa-direto/",
        "https://www.reclameaqui.com.br/empresa/banco-voiter/",
        "https://www.reclameaqui.com.br/empresa/banco-ourinvest/",
        "https://www.reclameaqui.com.br/empresa/nomad/"
        # Adicione até 40 URLs ou mais aqui
    ]
    # ==============================================================================

    navegador = setup_driver() # Abre o navegador UMA VEZ

    try:
        # Loop para processar cada URL da lista
        for i, url in enumerate(lista_de_urls):
            print("\n" + "="*50)
            print(f"PROCESSANDO URL {i+1}/{len(lista_de_urls)}")
            
            # Chama a função de scraping, passando o navegador e a URL atual
            df_coletado = raspar_dados_empresa(navegador, url)

            # Se algum dado foi coletado, salva no arquivo Excel correspondente
            if not df_coletado.empty:
                salvar_dados_excel(df_coletado, url)
            else:
                print(f"Não foi possível coletar dados para a URL: {url}")
            
            # Pausa respeitosa entre as requisições
            time.sleep(3)

    finally:
        # Garante que o navegador será fechado no final, mesmo que ocorra um erro
        print("\n" + "="*50)
        print("Processo finalizado. Fechando o navegador.")
        navegador.quit()