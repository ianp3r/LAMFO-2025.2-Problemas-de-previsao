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
# Lembre-se de instalar as dependências:
# pip install pandas selenium openpyxl


# --- FUNÇÃO PARA CONFIGURAR O DRIVER ---
def setup_driver():
    """Configura e retorna uma instância do WebDriver para o Firefox."""
    print("Configurando o driver do Firefox (usando o Selenium Manager)...")
    # Cada chamada cria uma nova instância
    return webdriver.Firefox()


# --- FUNÇÃO PARA COLETAR AS EMPRESAS AUTOMATICAMENTE ---
def coletar_empresas_automaticamente(url_listagem: str, limite: int | None = None):
    """
    Acessa a página de listagem e extrai pares (nome, url_do_perfil) das empresas.
    Define o limite para controlar a quantidade retornada (None coleta todas encontradas).
    """
    XPATH_EMPRESAS = "//*[@id='conteudo-decorator']/div/div[3]/fieldset/div[1]/div[1]"

    print(f"Buscando empresas automaticamente em {url_listagem}...")
    navegador = setup_driver()
    empresas = []

    try:
        navegador.get(url_listagem)
        wait = WebDriverWait(navegador, 20)

        container_empresas = wait.until(
            EC.presence_of_element_located((By.XPATH, XPATH_EMPRESAS))
        )

        links = container_empresas.find_elements(
            By.XPATH, ".//a[contains(@href, '/pages/empresa/') and contains(@href, '/perfil')]"
        )

        vistos = set()
        for link in links:
            nome = link.text.strip()
            href = link.get_attribute("href")

            if not nome or not href:
                continue

            if href in vistos:
                continue

            vistos.add(href)
            empresas.append((nome, href))

            if limite is not None and len(empresas) >= limite:
                break

        print(f"Total de empresas encontradas: {len(empresas)}")

    except Exception as e:
        print(f"❌ Erro ao coletar empresas automaticamente: {e}")

    finally:
        navegador.quit()
        print("Navegador fechado após coletar empresas.")

    return empresas

# --- FUNÇÃO DE RASPAGEM (COM MAIS ROBUSTEZ) ---
def extrair_nome_empresa(navegador):
    """Tenta extrair o nome da empresa já com a página carregada."""
    candidatos = [
        (By.CSS_SELECTOR, "div.perfil-empresa h1"),
        (By.CSS_SELECTOR, "h1.nome-empresa"),
        (By.CSS_SELECTOR, "div#conteudo-decorator h1"),
    ]

    for by, seletor in candidatos:
        try:
            elemento = WebDriverWait(navegador, 5).until(
                EC.presence_of_element_located((by, seletor))
            )
            texto = elemento.text.strip()
            if texto:
                return texto
        except Exception:
            continue

    titulo = (navegador.title or "").strip()
    if " - " in titulo:
        return titulo.split(" - ")[0].strip() or None
    return titulo or None


def raspar_dados_consumidor(url_empresa: str):
    """Raspa os dados de uma empresa no Consumidor.gov.br e retorna (df, nome_detectado)."""
    
    # 1. CRIA UM NOVO NAVEGADOR
    navegador = setup_driver()
    dados_coletados = []
    nome_empresa_detectado = None

    try:
        navegador.get(url_empresa)
        wait = WebDriverWait(navegador, 20)

        print("Aguardando o carregamento da página e dos indicadores...")
        wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "abas-perfil")))

        nome_empresa_detectado = extrair_nome_empresa(navegador)

        ano_atual = datetime.datetime.now().year
        ano_anterior = ano_atual - 1

        periodos = {
            'ultimos_30_dias': 'link_tab_dia',
            'ultimos_6_meses': 'link_tab_mes',
            f'ano_{ano_atual}': str(ano_atual),
            f'ano_{ano_anterior}': str(ano_anterior),
            'geral': 'link_tab_ano'
        }

        def _extrair_indicador(seletor_css):
            """Função auxiliar para extrair um indicador com segurança."""
            try:
                elemento = WebDriverWait(navegador, 5).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, seletor_css))
                )
                return elemento.text if elemento.text else "N/A"
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
                # Espera maior para garantir a renderização do JS
                time.sleep(4) 

                dados_periodo = {'periodo_nome': nome_periodo}
                
                # Seletores ajustados para buscar dentro da aba ativa
                seletor_base_aba_ativa = "div.tab-pane.active "
                dados_periodo['total_reclamacoes_finalizadas'] = _extrair_indicador(seletor_base_aba_ativa + "span.indicadorTotal")
                dados_periodo['indice_solucao'] = _extrair_indicador(seletor_base_aba_ativa + "div[id^='solucao'] .fonteResultado")
                dados_periodo['satisfacao_atendimento'] = _extrair_indicador(seletor_base_aba_ativa + "div[id^='atendimento'] .fonteResultado")
                dados_periodo['reclamacoes_respondidas'] = _extrair_indicador(seletor_base_aba_ativa + "div[id^='respondidas'] .fonteResultado")
                dados_periodo['prazo_medio_resposta'] = _extrair_indicador(seletor_base_aba_ativa + "div[id^='prazo'] .fonteResultadoDia")
                
                dados_coletados.append(dados_periodo)
                print("Dados do período coletados com sucesso.")

            except (NoSuchElementException, TimeoutException) as e:
                print(f"Erro ao processar o período {nome_periodo}: A aba pode não existir. Pulando...")
                continue
        
        print("\nColeta finalizada.")

    except Exception as e:
        print(f"❌ Erro geral ao processar a URL {url_empresa}: {e}")
        # Retorna lista vazia ou parcial em caso de erro
    
    finally:
        # 2. FECHA O NAVEGADOR (SEMPRE)
        if 'navegador' in locals():
            navegador.quit()
            print(f"Navegador fechado para {url_empresa}.")

    # --- Processamento do DataFrame (Fora do Try/Finally) ---
    if not dados_coletados:
        return pd.DataFrame(), nome_empresa_detectado

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
    
    return df_resumo, nome_empresa_detectado

# --- 2. SEÇÃO DE LIMPEZA E PADRONIZAÇÃO DE DADOS ---

def limpar_valor_numerico_consumidor(valor):
    """
    Converte um valor string (ex: '98,6%', '7,5', '1.543') em um float.
    Trata vírgula como decimal e remove pontos de milhar e '%'.
    Retorna pd.NA se a conversão falhar.
    """
    if pd.isna(valor):
        return pd.NA
    
    s = str(valor).strip()
    if s.lower() in ['n/a', 'n/d', '']:
        return pd.NA

    try:
        # Remove caracteres indesejados: '%' e '.' (milhar)
        s = s.replace('%', '').replace('.', '').strip()
        # Substitui a vírgula decimal por ponto
        s = s.replace(',', '.')
        
        # Converte para float e arredonda
        return round(float(s), 2)
    except (ValueError, TypeError):
        return pd.NA

def limpar_dados_consumidor(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica todas as funções de limpeza ao DataFrame do Consumidor.gov.br.
    """
    print("Iniciando limpeza e padronização dos dados (Consumidor.gov)...")
    df_limpo = df.copy()

    colunas_para_limpar = [
        'total_reclamacoes_finalizadas', 
        'indice_solucao',
        'satisfacao_atendimento', 
        'reclamacoes_respondidas', 
        'prazo_medio_resposta'
    ]

    for col in colunas_para_limpar:
        if col in df_limpo.columns:
            df_limpo[col] = df_limpo[col].apply(limpar_valor_numerico_consumidor)
            df_limpo[col] = pd.to_numeric(df_limpo[col], errors='coerce')

    df_limpo = df_limpo.rename(columns={
        'indice_solucao': 'indice_solucao_perc',
        'satisfacao_atendimento': 'satisfacao_atendimento_nota',
        'reclamacoes_respondidas': 'reclamacoes_respondidas_perc',
        'prazo_medio_resposta': 'prazo_medio_resposta_dias'
    })
    
    colunas_ordenadas = [
        'periodo_nome', 'total_reclamacoes_finalizadas', 'indice_solucao_perc',
        'satisfacao_atendimento_nota', 'reclamacoes_respondidas_perc', 
        'prazo_medio_resposta_dias', 'data_coleta', 'hora_coleta'
    ]
    colunas_presentes = [col for col in colunas_ordenadas if col in df_limpo.columns]
    df_limpo = df_limpo[colunas_presentes]
            
    print("Limpeza finalizada.")
    return df_limpo


# --- 3. FUNÇÃO PARA SALVAR OS DADOS (NO FORMATO CONSOLIDADO) ---
def salvar_dados_excel(df_novos, nome_empresa):
    """
    Salva o DataFrame no arquivo "coletas_consumidor_gov.xlsx", 
    usando uma aba por empresa e concatenando com dados existentes.
    """
    if df_novos.empty:
        print("Nenhum dado novo para salvar.")
        return

    caminho_arquivo = "coletas_consumidor_gov.xlsx"
    
    try:
        nome_planilha = re.sub(r'[\\/*?:\[\]]', '', nome_empresa)
        nome_planilha = nome_planilha[:31]
    except Exception as e:
        print(f"Erro ao gerar nome da planilha: {e}. Usando 'default'.")
        nome_planilha = "default"

    print(f"Preparando para salvar em '{caminho_arquivo}' na aba '{nome_planilha}'...")

    try:
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
    
    dados_existentes[nome_planilha] = df_final

    try:
        with pd.ExcelWriter(caminho_arquivo, engine='openpyxl') as writer:
            for nome_aba, df_aba in dados_existentes.items():
                df_aba.to_excel(writer, sheet_name=nome_aba, index=False)
        
        print(f"✅ Dados salvos com sucesso em '{caminho_arquivo}', na aba '{nome_planilha}'")
    
    except Exception as e:
        print(f"❌ Erro ao salvar o arquivo Excel '{caminho_arquivo}': {e}")


# --- EXECUÇÃO PRINCIPAL (COM LIMPEZA) ---
def main():
    """
    Função principal para executar o processo de coleta.
    """
    # Basta informar apenas os links das páginas de perfil das empresas.
    EMPRESAS_ALVO = [
        "https://www.consumidor.gov.br/pages/empresa/20140206000001701/perfil", "https://www.consumidor.gov.br/pages/empresa/20140206000001101/perfil", "https://www.consumidor.gov.br/pages/empresa/20140206000001216/perfil", "https://www.consumidor.gov.br/pages/empresa/20140206000002101/perfil", "https://www.consumidor.gov.br/pages/empresa/20140206000002000/perfil", "https://www.consumidor.gov.br/pages/empresa/20150122000050251/perfil", "https://www.consumidor.gov.br/pages/empresa/20150105000046030/perfil", "https://www.consumidor.gov.br/pages/empresa/20141023000031224/perfil", "https://www.consumidor.gov.br/pages/empresa/20150127000051386/perfil", "https://www.consumidor.gov.br/pages/empresa/20160321000236631/perfil", "https://www.consumidor.gov.br/pages/empresa/20140731000017601/perfil", "https://www.consumidor.gov.br/pages/empresa/20141220000043918/perfil", "https://www.consumidor.gov.br/pages/empresa/20160608000298369/perfil", "https://www.consumidor.gov.br/pages/empresa/20151002000159149/perfil", "https://www.consumidor.gov.br/pages/empresa/20150413000095197/perfil", "https://www.consumidor.gov.br/pages/empresa/20140206000001501/perfil", "https://www.consumidor.gov.br/pages/empresa/20150127000051402/perfil", "https://www.consumidor.gov.br/pages/empresa/20180325000884145/perfil", "https://www.consumidor.gov.br/pages/empresa/20150204000053619/perfil", "https://www.consumidor.gov.br/pages/empresa/20141222000044027/perfil", "https://www.consumidor.gov.br/pages/empresa/20190503001376215/perfil", "https://www.consumidor.gov.br/pages/empresa/20141217000043040/perfil", "https://www.consumidor.gov.br/pages/empresa/20170805000643430/perfil", "https://www.consumidor.gov.br/pages/empresa/20150707000127945/perfil", "https://www.consumidor.gov.br/pages/empresa/20191119001741080/perfil", "https://www.consumidor.gov.br/pages/empresa/20150617000121756/perfil", "https://www.consumidor.gov.br/pages/empresa/20181206001199622/perfil", "https://www.consumidor.gov.br/pages/empresa/20141226000044793/perfil", "https://www.consumidor.gov.br/pages/empresa/20150112000047736/perfil", "https://www.consumidor.gov.br/pages/empresa/20150226000077341/perfil", "https://www.consumidor.gov.br/pages/empresa/20190723001495894/perfil", "https://www.consumidor.gov.br/pages/empresa/20170726000634071/perfil", "https://www.consumidor.gov.br/pages/empresa/20140206000001321/perfil", "https://www.consumidor.gov.br/pages/empresa/20140206000001341/perfil", "https://www.consumidor.gov.br/pages/empresa/20140206000001301/perfil", "https://www.consumidor.gov.br/pages/empresa/20140206000001361/perfil", "https://www.consumidor.gov.br/pages/empresa/20140206000001361/perfil", "https://www.consumidor.gov.br/pages/empresa/20150224000075957/perfil", "https://consumidor.gov.br/pages/empresa/20140828000022383/perfil", "https://consumidor.gov.br/pages/empresa/20140429000000564/perfil", "https://consumidor.gov.br/pages/empresa/20140429000000563/perfil", "https://consumidor.gov.br/pages/empresa/20200414002008990/perfil", "https://consumidor.gov.br/pages/empresa/20151012000165999/perfil", "https://consumidor.gov.br/pages/empresa/20141013000029304/perfil", "https://consumidor.gov.br/pages/empresa/20140206000001481/perfil", "https://consumidor.gov.br/pages/empresa/20140429000000562/perfil", "https://consumidor.gov.br/pages/empresa/20140502000000585/perfil", "https://consumidor.gov.br/pages/empresa/20140206000001401/perfil", "https://consumidor.gov.br/pages/empresa/20140811000019302/perfil", "https://consumidor.gov.br/pages/empresa/20141222000044136/perfil", "https://consumidor.gov.br/pages/empresa/20141220000043920/perfil", "https://consumidor.gov.br/pages/empresa/20140206000001410/perfil", "https://consumidor.gov.br/pages/empresa/20140206000001402/perfil", "https://consumidor.gov.br/pages/empresa/20200820002339875/perfil", "https://consumidor.gov.br/pages/empresa/20140820000021003/perfil", "https://consumidor.gov.br/pages/empresa/20140206000001381/perfil", "https://consumidor.gov.br/pages/empresa/20140206000001410/perfil", "https://consumidor.gov.br/pages/empresa/20150105000046168/perfil", "https://consumidor.gov.br/pages/empresa/20170830000668638/perfil", "https://consumidor.gov.br/pages/empresa/20181026001150445/perfil", "https://consumidor.gov.br/pages/empresa/20141009000028828/perfil", "https://consumidor.gov.br/pages/empresa/20170608000585401/perfil", "https://consumidor.gov.br/pages/empresa/20160610000300054/perfil", "https://consumidor.gov.br/pages/empresa/20140903000023795/perfil", "https://consumidor.gov.br/pages/empresa/20141231000045552/perfil", "https://consumidor.gov.br/pages/empresa/20160621000306055/perfil", "https://consumidor.gov.br/pages/empresa/20140206000001113/perfil", "https://consumidor.gov.br/pages/empresa/20140206000001208/perfil", "https://consumidor.gov.br/pages/empresa/20161026000387063/perfil", "https://consumidor.gov.br/pages/empresa/20140717000015203/perfil", "https://consumidor.gov.br/pages/empresa/20150115000048601/perfil", "https://consumidor.gov.br/pages/empresa/20140603000001426/perfil", "https://consumidor.gov.br/pages/empresa/20150106000046365/perfil", "https://consumidor.gov.br/pages/empresa/20200408001996506/perfil", "https://consumidor.gov.br/pages/empresa/20150127000051312/perfil", "https://consumidor.gov.br/pages/empresa/20140729000017171/perfil", "https://consumidor.gov.br/pages/empresa/20160419000248826/perfil", "https://consumidor.gov.br/pages/empresa/20151002000160493/perfil", "https://consumidor.gov.br/pages/empresa/20150714000130265/perfil", "https://consumidor.gov.br/pages/empresa/20171128000754548/perfil", "https://consumidor.gov.br/pages/empresa/20150219000068275/perfil", "https://consumidor.gov.br/pages/empresa/20201207002607916/perfil", "https://consumidor.gov.br/pages/empresa/20150526000113230/perfil", "https://consumidor.gov.br/pages/empresa/20140206000001112/perfil", "https://consumidor.gov.br/pages/empresa/20140206000004002/perfil", "https://consumidor.gov.br/pages/empresa/20150219000069103/perfil", "https://consumidor.gov.br/pages/empresa/20150324000089145/perfil", "https://consumidor.gov.br/pages/empresa/20150126000051085/perfil", "https://consumidor.gov.br/pages/empresa/20140814000020203/perfil", "https://consumidor.gov.br/pages/empresa/20140825000021577/perfil", "https://consumidor.gov.br/pages/empresa/20140925000027109/perfil", "https://consumidor.gov.br/pages/empresa/20141218000043148/perfil", "https://consumidor.gov.br/pages/empresa/20241002006257153/perfil", "https://consumidor.gov.br/pages/empresa/20240523005915047/perfil", "https://consumidor.gov.br/pages/empresa/20240612005962118/perfil", "https://consumidor.gov.br/pages/empresa/20240806006096831/perfil", "https://consumidor.gov.br/pages/empresa/20240709006026181/perfil", "https://consumidor.gov.br/pages/empresa/20250203006809215/perfil", "https://consumidor.gov.br/pages/empresa/20240223005665599/perfil", "https://consumidor.gov.br/pages/empresa/20250113006709856/perfil", "https://consumidor.gov.br/pages/empresa/20250414007120935/perfil", "https://consumidor.gov.br/pages/empresa/20240816006121325/perfil", "https://consumidor.gov.br/pages/empresa/20240820006129449/perfil", "https://consumidor.gov.br/pages/empresa/20240930006248759/perfil", "https://consumidor.gov.br/pages/empresa/20240809006105233/perfil", "https://consumidor.gov.br/pages/empresa/20240717006045991/perfil"
    ]


    print(f"--- Iniciando processo para {len(EMPRESAS_ALVO)} empresas ---")

    for entrada in EMPRESAS_ALVO:
        if isinstance(entrada, tuple) and len(entrada) == 2:
            nome_manual, url_empresa = entrada
        else:
            nome_manual, url_empresa = None, entrada

        print(f"\n--- Iniciando coleta para URL: {url_empresa} ---")
        
        try:
            # 1. Coleta (abre e fecha um navegador)
            df_coletado, nome_detectado = raspar_dados_consumidor(url_empresa)

            nome_empresa = nome_detectado or "empresa_desconhecida"

            if not df_coletado.empty:
                # 2. Limpeza
                df_limpo = limpar_dados_consumidor(df_coletado)
                
                print("\n--- Dados Limpos (Numéricos) ---")
                print(df_limpo.to_string())
                
                # 3. Salva
                salvar_dados_excel(df_limpo, nome_empresa)
            else:
                print(f"Nenhum dado foi coletado para {url_empresa}")
        
        except Exception as e:
            print(f"❌ Erro crítico no loop principal para {url_empresa}: {e}")
            # Continua para a próxima empresa mesmo se uma falhar
            continue

    print("\n--- Processo de coleta finalizado para todas as empresas ---")

if __name__ == "__main__":
    main()