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

def setup_driver():
    """Configura e retorna uma instância do WebDriver para o Firefox."""
    print("Configurando o driver do Firefox (usando o Selenium Manager)...")
    # Cada chamada a esta função cria uma nova instância independente
    return webdriver.Firefox()

def raspar_dados_empresa(url_empresa: str):
    """Raspa os dados de reputação de uma empresa no Reclame Aqui."""
    
    navegador = setup_driver()
    print(f"Acessando: {url_empresa}")
    
    try:
        navegador.get(url_empresa)
        wait = WebDriverWait(navegador, 15)

        periodos = {
            'seis_meses': 'newPerformanceCard-tab-1',
            'doze_meses': 'newPerformanceCard-tab-2',
            'ano_2025': 'newPerformanceCard-tab-3', # O site mostrará os anos relevantes
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

                try:
                    seletor_nota_media = "div#ra-new-reputation span[class*='go'] > b[class*='go']"
                    # Usar wait para garantir que o elemento exista antes de tentar acessá-lo
                    elemento_nota = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, seletor_nota_media)))
                    nota_texto = elemento_nota.text
                    
                    # Extrai apenas o número (ex: "8.7" de "8.7/10.")
                    nota_media_reputacao = re.search(r'[\d.,]+', nota_texto).group(0) if re.search(r'[\d.,]+', nota_texto) else "N/A"
                    dados_periodo['nota_media_reputacao'] = nota_media_reputacao
                    print(f"Nota de reputação encontrada: {nota_media_reputacao}")

                except (NoSuchElementException, TimeoutException):
                    print("Nota de reputação principal não encontrada para este período.")
                    dados_periodo['nota_media_reputacao'] = "N/A"

                # --- DADOS DOS BLOCOS (INDICADORES) ---
                # Espera que os blocos de indicadores estejam presentes
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.go4263471347")))
                blocos = navegador.find_elements(By.CSS_SELECTOR, "div.go4263471347")

                for bloco in blocos:
                    texto = bloco.text.strip()
                    if not texto:
                        continue
                    
                    try:
                        valor_strong = bloco.find_element(By.TAG_NAME, "strong").text
                    except NoSuchElementException:
                        valor_strong = "N/A" # Caso algum bloco não tenha <strong>

                    if "recebeu" in texto:
                        dados_periodo["num_reclamacoes"] = valor_strong
                    elif "Respondeu" in texto:
                        dados_periodo["perc_recl_resp"] = valor_strong
                    elif "aguardando resposta" in texto:
                        dados_periodo["reclamacoes_aguardando"] = valor_strong
                    elif "avaliadas" in texto:
                        nota_match = re.search(r"nota média.*?([\d.,]+)", texto, re.IGNORECASE)
                        nota_consumidor = nota_match.group(1) if nota_match else "N/A"
                        dados_periodo["num_avaliadas"] = valor_strong
                        dados_periodo["nota_consumidor"] = nota_consumidor
                    elif "voltariam a fazer negócio" in texto:
                        dados_periodo["novam_negoc"] = valor_strong
                    elif "resolveu" in texto:
                        dados_periodo["indice_solucao"] = valor_strong
                    elif "tempo médio de resposta" in texto:
                        dados_periodo["tempo_medio_resposta"] = valor_strong

                # --- INTERVALO DE TEMPO DO PERÍODO ---
                try:
                    periodo_texto = navegador.find_element(By.CSS_SELECTOR, "span.go2159339046").text
                    dados_periodo["periodo_intervalo"] = periodo_texto.split("período de")[-1].strip()
                except NoSuchElementException:
                    dados_periodo["periodo_intervalo"] = "N/A"

                dados_coletados.append(dados_periodo)

            except (NoSuchElementException, TimeoutException) as e:
                print(f"Erro ao coletar dados para o período {nome_periodo}: {e}. Pulando...")
        
        print("Coleta finalizada.")

    except Exception as e:
        print(f"Erro geral ao processar a URL {url_empresa}: {e}")
    
    finally:
        # 2. FECHA O NAVEGADOR APÓS TERMINAR ESTA URL
        if 'navegador' in locals():
            navegador.quit()
            print(f"Navegador fechado para {url_empresa}.")

    if not dados_coletados:
        return pd.DataFrame()

    df_resumo = pd.DataFrame(dados_coletados)

    agora = datetime.datetime.now()
    df_resumo['data_coleta'] = agora.date()
    df_resumo['hora_coleta'] = agora.time().strftime('%H:%M:%S')

    # Reorganiza as colunas
    colunas_ordenadas = [
        'periodo_nome', 'nota_media_reputacao', 'nota_consumidor', 'num_reclamacoes', 
        'perc_recl_resp', 'indice_solucao', 'novam_negoc', 'num_avaliadas',
        'reclamacoes_aguardando', 'tempo_medio_resposta_dias', 'periodo_intervalo', 
        'data_coleta', 'hora_coleta'
    ]
    colunas_presentes = [col for col in colunas_ordenadas if col in df_resumo.columns]
    df_resumo = df_resumo[colunas_presentes]
    
    return df_resumo

# --- 2. SEÇÃO DE LIMPEZA E PADRONIZAÇÃO DE DADOS ---

def limpar_valor_numerico(valor):
    """
    Converte um valor string (ex: '98.6%', '83058', '8.2') em um float.
    Retorna pd.NA se a conversão falhar.
    """
    if pd.isna(valor):
        return pd.NA
    
    s = str(valor).strip()
    if s.lower() in ['n/a', 'n/d', '']:
        return pd.NA

    # Extrai o primeiro número (int ou float) que encontrar na string
    # Funciona para '98.6%', '8.2', '83058 reclamacoes'
    match = re.search(r'^-?([\d.]+)', s)
    
    if not match:
        return pd.NA
    
    try:
        # Converte o número encontrado para float e arredonda
        return round(float(match.group(1)), 2)
    except (ValueError, TypeError):
        return pd.NA

def limpar_tempo(valor):
    """
    Converte uma string de tempo (ex: '3 dias 2h') em um número decimal de dias.
    """
    if pd.isna(valor) or str(valor).lower() in ['n/a', 'n/d', '']:
        return pd.NA

    s = str(valor).lower()
    total_dias = 0.0
    
    try:
        match_dias = re.search(r'(\d+)\s*dias?', s)
        if match_dias:
            total_dias += float(match_dias.group(1))
            
        match_horas = re.search(r'(\d+)\s*h', s)
        if match_horas:
            total_dias += float(match_horas.group(1)) / 24.0
            
        match_min = re.search(r'(\d+)\s*min', s)
        if match_min:
            total_dias += float(match_min.group(1)) / (24.0 * 60.0)
            
        return round(total_dias, 2) if total_dias > 0 else pd.NA
    except Exception:
        return pd.NA

def limpar_dados_ra(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica todas as funções de limpeza ao DataFrame do Reclame Aqui.
    """
    print("Iniciando limpeza e padronização dos dados...")
    df_limpo = df.copy()

    # Colunas que devem ser convertidas para número
    colunas_numericas = [
        'nota_media_reputacao', 'nota_consumidor', 'num_reclamacoes', 
        'perc_recl_resp', 'indice_solucao', 'novam_negoc', 'num_avaliadas',
        'reclamacoes_aguardando'
    ]

    for col in colunas_numericas:
        if col in df_limpo.columns:
            df_limpo[col] = df_limpo[col].apply(limpar_valor_numerico)
            df_limpo[col] = pd.to_numeric(df_limpo[col], errors='coerce')

    # Limpeza especial para a coluna de tempo
    if 'tempo_medio_resposta' in df_limpo.columns:
        df_limpo['tempo_medio_resposta_dias'] = df_limpo['tempo_medio_resposta'].apply(limpar_tempo)
        # Remove a coluna de string original
        df_limpo = df_limpo.drop(columns=['tempo_medio_resposta'])
    
    print("Limpeza finalizada.")
    return df_limpo


# --- 3. FUNÇÃO PARA SALVAR OS DADOS (NO FORMATO CONSOLIDADO) ---

def salvar_dados_excel(df_novos, url_empresa):
    """
    Salva o DataFrame no arquivo "coletas.xlsx", 
    usando uma aba por empresa e concatenando com dados existentes.
    """
    if df_novos.empty:
        print("Nenhum dado novo para salvar.")
        return

    caminho_arquivo = "coletas_reclame_aqui.xlsx" # Nome do arquivo centralizado
    
    try:
        # Cria um nome de planilha mais limpo a partir da URL
        nome_planilha = url_empresa.strip("/").split("/")[-1]
        nome_planilha = re.sub(r'[\\/*?:\[\]]', '', nome_planilha) # Remove caracteres inválidos
        nome_planilha = nome_planilha[:31] # Limita ao tamanho máximo de aba do Excel
    except Exception as e:
        print(f"Erro ao gerar nome da planilha: {e}. Usando 'default'.")
        nome_planilha = "default"

    print(f"Preparando para salvar em '{caminho_arquivo}' na aba '{nome_planilha}'...")

    try:
        # Tenta ler o arquivo existente
        dados_existentes = pd.read_excel(caminho_arquivo, sheet_name=None, engine='openpyxl')
    except FileNotFoundError:
        print(f"Arquivo '{caminho_arquivo}' não encontrado. Será criado um novo.")
        dados_existentes = {}
    except Exception as e:
        print(f"Erro ao ler '{caminho_arquivo}': {e}. Começando do zero.")
        dados_existentes = {}

    if nome_planilha in dados_existentes:
        print(f"Aba '{nome_planilha}' encontrada. Adicionando novos dados...")
        df_antigo = dados_existentes[nome_planilha]
        df_final = pd.concat([df_antigo, df_novos], ignore_index=True)
    else:
        print(f"Aba '{nome_planilha}' não encontrada. Criando nova aba.")
        df_final = df_novos
    
    # Atualiza o dicionário com os dados (novos ou concatenados)
    dados_existentes[nome_planilha] = df_final

    try:
        # Salva TODAS as abas de volta no arquivo
        with pd.ExcelWriter(caminho_arquivo, engine='openpyxl') as writer:
            for nome_aba, df_aba in dados_existentes.items():
                df_aba.to_excel(writer, sheet_name=nome_aba, index=False)
        
        print(f"✅ Dados salvos com sucesso em '{caminho_arquivo}', na aba '{nome_planilha}'")
    
    except Exception as e:
        print(f"❌ Erro ao salvar o arquivo Excel '{caminho_arquivo}': {e}")

def main():

    URLS_ALVO = [
       "https://www.reclameaqui.com.br/empresa/banco-do-brasil/", "https://www.reclameaqui.com.br/empresa/bradesco/", "reclameaqui.com.br/empresa/bradesco/", "https://www.reclameaqui.com.br/empresa/santander/", "https://www.reclameaqui.com.br/empresa/caixa-economica-federal/", "https://www.reclameaqui.com.br/empresa/banco-mercantil-do-brasil/", "https://www.reclameaqui.com.br/empresa/banco-safra/", "https://www.reclameaqui.com.br/empresa/banco-pan/", "https://www.reclameaqui.com.br/empresa/banco-daycoval/", "https://www.reclameaqui.com.br/empresa/banco-abc-brasil-s-a/", "https://www.reclameaqui.com.br/empresa/bv-financeira/", "https://www.reclameaqui.com.br/empresa/banrisul/", "https://www.reclameaqui.com.br/empresa/banco-da-amazonia/", "https://www.reclameaqui.com.br/empresa/banco-do-nordeste/", "https://www.reclameaqui.com.br/empresa/banco-industrial-do-brasil-s-a/", "https://www.reclameaqui.com.br/empresa/banco-bmg/", "https://www.reclameaqui.com.br/empresa/tribanco/", "https://www.reclameaqui.com.br/empresa/banco-master/", "https://www.reclameaqui.com.br/empresa/nubank/", "https://www.reclameaqui.com.br/empresa/inter/", "https://www.reclameaqui.com.br/empresa/c6-bank/", "https://www.reclameaqui.com.br/empresa/mercado-pago/", "https://www.reclameaqui.com.br/empresa/picpay/", "https://www.reclameaqui.com.br/empresa/pagseguro/", "https://www.reclameaqui.com.br/empresa/btg-mais/", "https://www.reclameaqui.com.br/empresa/banco-original/", "https://www.reclameaqui.com.br/empresa/conta-super/", "https://www.reclameaqui.com.br/empresa/banco-neon/", "https://www.reclameaqui.com.br/empresa/will-bank/", "http://reclameaqui.com.br/empresa/banco-bs2/", "https://www.reclameaqui.com.br/empresa/barigui-financeira/", "https://www.reclameaqui.com.br/empresa/xp-investimentos/", "https://www.reclameaqui.com.br/empresa/z1/", "https://www.reclameaqui.com.br/empresa/ton-solucoes-de-pagamento/", "https://www.reclameaqui.com.br/empresa/b-uni/", "https://www.reclameaqui.com.br/empresa/sidepay-fintech/", "https://www.reclameaqui.com.br/empresa/stone/", "https://www.reclameaqui.com.br/empresa/banco-intercap-s-a/", "https://www.reclameaqui.com.br/empresa/transferwise/", "https://www.reclameaqui.com.br/empresa/nomad-global/", "https://www.reclameaqui.com.br/empresa/vivo-celular-fixo-internet-tv/", "https://www.reclameaqui.com.br/empresa/claro/", "https://www.reclameaqui.com.br/empresa/tim-celular/", "https://www.reclameaqui.com.br/empresa/oi-internet/", "https://www.reclameaqui.com.br/empresa/algar-telecom/", "https://www.reclameaqui.com.br/empresa/sercomtel-pr-telecomunicacoes/", "https://www.reclameaqui.com.br/empresa/nextel/", "https://www.reclameaqui.com.br/empresa/correios-celular/", "https://www.reclameaqui.com.br/empresa/carrefour-loja-online/", "https://www.reclameaqui.com.br/empresa/pao-de-acucar/", "https://www.reclameaqui.com.br/empresa/extra-loja-online/", "https://www.reclameaqui.com.br/empresa/assai-atacadista/", "https://www.reclameaqui.com.br/empresa/atacadao/", "https://www.reclameaqui.com.br/empresa/super-nosso-loja-fisica/", "https://www.reclameaqui.com.br/empresa/cencosud-brasil-atacado/", "https://www.reclameaqui.com.br/empresa/oba-hortifruti/", "https://www.reclameaqui.com.br/empresa/super-muffato-loja-fisica/", "https://www.reclameaqui.com.br/empresa/magazine-luiza-loja-online/", "https://www.reclameaqui.com.br/empresa/casas-bahia-loja-online/", "https://www.reclameaqui.com.br/empresa/ponto-frio-loja-online/", "https://www.reclameaqui.com.br/empresa/fast-shop/", "https://www.reclameaqui.com.br/empresa/lojas-colombo-loja-online/", "https://www.reclameaqui.com.br/empresa/amazon/", "https://www.reclameaqui.com.br/empresa/mercado-livre/", "https://www.reclameaqui.com.br/empresa/submarino/", "https://www.reclameaqui.com.br/empresa/americanas-com-loja-online/", "https://www.reclameaqui.com.br/empresa/shopee/", "https://www.reclameaqui.com.br/empresa/kabum/", "https://www.reclameaqui.com.br/empresa/decolar-com/", "https://www.reclameaqui.com.br/empresa/submarino-viagens/", "https://www.reclameaqui.com.br/empresa/hotel-urbano/", "https://www.reclameaqui.com.br/empresa/tam-viagens/", "https://www.reclameaqui.com.br/empresa/azul-viagens/", "https://www.reclameaqui.com.br/empresa/agaxtur-agencia-de-viagens-e-turismo/", "https://www.reclameaqui.com.br/empresa/flytour-com/", "https://www.reclameaqui.com.br/empresa/viagens-visual-visual-turismo/", "https://www.reclameaqui.com.br/empresa/123-milhas/", "https://www.reclameaqui.com.br/empresa/maxmilhas/", "https://www.reclameaqui.com.br/empresa/viajanet/", "https://www.reclameaqui.com.br/empresa/kayak-brasil/", "https://www.reclameaqui.com.br/empresa/booking-com/", "https://www.reclameaqui.com.br/empresa/juntos-pelo-mundo-ltda/", "https://www.reclameaqui.com.br/empresa/trip-com/", "https://www.reclameaqui.com.br/empresa/porto-seguro/", "https://www.reclameaqui.com.br/empresa/bradesco-seguros/", "https://www.reclameaqui.com.br/empresa/itau-seguros-e-capitalizacao/", "https://www.reclameaqui.com.br/empresa/bb-seguros/", "https://www.reclameaqui.com.br/empresa/caixa-seguradora/", "https://www.reclameaqui.com.br/empresa/sulamerica-saude/", "https://www.reclameaqui.com.br/empresa/mapfre-seguros/", "https://www.reclameaqui.com.br/empresa/tokio-marine-seguradora/", "https://www.reclameaqui.com.br/empresa/hdi-seguros/", "https://www.reclameaqui.com.br/empresa/allianz-seguros/", "https://www.reclameaqui.com.br/empresa/zurich-seguros/", "https://www.reclameaqui.com.br/empresa/zurich-seguros/", "https://www.reclameaqui.com.br/empresa/metlife/", "https://www.reclameaqui.com.br/empresa/ace-seguradora/", "https://www.reclameaqui.com.br/empresa/generali-seguros/", "https://www.reclameaqui.com.br/empresa/aig-seguros-brasil/", "https://www.reclameaqui.com.br/empresa/prudential-do-brasil-seguros-de-vida/", "https://www.reclameaqui.com.br/empresa/hapvida-saude/", "https://www.reclameaqui.com.br/empresa/bradesco-saude/", "https://www.reclameaqui.com.br/empresa/amil/", "https://www.reclameaqui.com.br/empresa/sulamerica-saude/", "https://www.reclameaqui.com.br/empresa/unimed-do-est-r-j-federacao-est-das-cooperativas-med/", "https://www.reclameaqui.com.br/empresa/prevent-senior/", "https://www.reclameaqui.com.br/empresa/porto-seguro/", "https://www.reclameaqui.com.br/empresa/golden-cross/", "https://www.reclameaqui.com.br/empresa/assim-saude/", "https://www.reclameaqui.com.br/empresa/medsenior/", "https://www.reclameaqui.com.br/df/rede-d-or_FO55REYdT_DN6Kmz/", "https://www.reclameaqui.com.br/empresa/dasa-laboratorio/", "https://www.reclameaqui.com.br/empresa/hapvida-saude/", "reclameaqui.com.br/empresa/hapvida-saude/", "https://www.reclameaqui.com.br/empresa/hospital-mater-dei/", "https://www.reclameaqui.com.br/empresa/farmacia-pague-menos/", "https://www.reclameaqui.com.br/empresa/droga-raia/", "https://www.reclameaqui.com.br/empresa/panvel-farmacias/", "https://www.reclameaqui.com.br/empresa/nestle/", "https://www.reclameaqui.com.br/empresa/ambev/", "https://www.reclameaqui.com.br/empresa/brf-food-services/", "https://www.reclameaqui.com.br/empresa/jbs-alimentos-friboi/", "https://www.reclameaqui.com.br/empresa/coca-cola-brasil/", "https://www.reclameaqui.com.br/empresa/pepsico-do-brasil/", "https://www.reclameaqui.com.br/empresa/unilever/", "https://www.reclameaqui.com.br/empresa/mondelez-kraft-foods-brasil/", "https://www.reclameaqui.com.br/empresa/danone/", "https://www.reclameaqui.com.br/empresa/heinz-brasil/", "https://www.reclameaqui.com.br/empresa/betano/", "https://www.reclameaqui.com.br/empresa/bet365/", "https://www.reclameaqui.com.br/empresa/bet-boom/", "https://www.reclameaqui.com.br/empresa/superbet-brasil/", "https://www.reclameaqui.com.br/empresa/novibet/", "https://www.reclameaqui.com.br/empresa/f12-bet/", "https://www.reclameaqui.com.br/empresa/stake_1179824/", "https://www.reclameaqui.com.br/empresa/mc-games/", "https://www.reclameaqui.com.br/empresa/esportiva-bet/", "https://www.reclameaqui.com.br/empresa/rivalo-brasil/", "https://www.reclameaqui.com.br/empresa/multibet-games/", "https://www.reclameaqui.com.br/empresa/br4bet/", "https://www.reclameaqui.com.br/empresa/gol-de-bet/", "https://www.reclameaqui.com.br/empresa/vbet/", "https://www.reclameaqui.com.br/empresa/betfair/"
    ]

    print(f"--- Iniciando processo para {len(URLS_ALVO)} URLs ---")

    for url in URLS_ALVO:
        print(f"\n--- Coletando dados para: {url} ---")
        try:
            # 1. Coleta os dados (abre e fecha um navegador)
            df_coletado = raspar_dados_empresa(url)

            if not df_coletado.empty:
                # 2. Limpa os dados coletados
                df_limpo = limpar_dados_ra(df_coletado)
                
                print("\n--- Dados Limpos (Numéricos) ---")
                print(df_limpo.to_string()) 
                
                # 3. Salva os dados limpos no Excel
                salvar_dados_excel(df_limpo, url)
            else:
                print(f"Nenhum dado foi coletado para {url}")
        
        except Exception as e:
            print(f"Erro crítico no loop principal para {url}: {e}")
            # Continua para a próxima URL mesmo se uma falhar
            continue 

    print("\n--- Processo de coleta finalizado para todas as URLs ---")

if __name__ == "__main__":
    main()