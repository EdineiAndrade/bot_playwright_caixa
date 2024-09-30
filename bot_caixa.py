from playwright.sync_api import sync_playwright
import shutil
import pandas as pd
from datetime import datetime, timedelta
import time
import os
import re

def configurar_navegador():
    name_file = path_file()
    downloads_path = os.path.dirname(name_file)
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(args=["--window-position=0,0"], headless=False, downloads_path=downloads_path)
    page = browser.new_page()
    return playwright, browser, page, name_file

def download_file(page, name_file):
    base_url = "https://venda-imoveis.caixa.gov.br/sistema/download-lista.asp"
    page.goto(base_url)
    page.locator('#cmb_estado').select_option('geral')

    with page.expect_download() as download_info:
        page.locator('#btn_next1').click()
    download = download_info.value
    download.save_as(name_file)
    download.delete()

    pd.options.display.max_columns = None
    df = pd.read_csv(name_file, skiprows=2, delimiter=';', encoding='latin-1')
    df = clean_dataframe(df)
    return df

def remove_illegal_characters(value):
    if isinstance(value, str):
        return re.sub(r'[\x00-\x1F\x7F-\x9F]', '', value)
    return value

def clean_dataframe(df):
    for col in df.columns:
        df[col] = df[col].apply(remove_illegal_characters)
    return df

def path_file():
    now = datetime.now()
    formatted_date = now.strftime("%d-%m-%y_%H-%M-%S")

    user_path = os.environ.get('USERPROFILE')
    user_dw = os.path.join(user_path, 'Downloads')
    path_file = os.path.join(user_dw, 'imoveis')

    name_file = os.path.join(path_file, f'baixados_{formatted_date}.csv')
    if os.path.exists(path_file):
        shutil.rmtree(path_file)
    os.mkdir(path_file)

    return name_file

def busca_site_caixa(page, name_file, df):
    numero_de_linhas = df.shape[0]
    start_time = datetime.now()    
    ultimo_salvamento = start_time
    nome_excel = name_file.replace('csv', 'xlsx')
        
    for index, row in df.iterrows():
        try:
            now = datetime.now()
            formatted_date = now.strftime("%d/%m/%y %H:%M:%S")        
            # Cálculo de quantas consultas faltam
            faltam = numero_de_linhas - (index + 1)        
            # Tempo decorrido
            elapsed_time = now - start_time
            link = row['Link de acesso']
            page.goto(link)

            seletor_1 = '//*[@class="related-box"]/span/i'

            count = page.locator(seletor_1).count()

            if count > 0:
                if count >= 2:
                    leilao_01 = page.locator('//*[@class="related-box"]/span[4]').inner_text()
                    leilao_02 = page.locator('//*[@class="related-box"]/span[5]').inner_text()
                elif count == 1:
                    leilao_01 = page.locator('//*[@class="related-box"]/span[4]').inner_text()
                    leilao_02 = 'sem informações'
            else:
                leilao_01 = 'sem informações'
                leilao_02 = 'sem informações'

            fgts_info = page.locator('//*[@class="related-box"]/p[3]').inner_text()
            fgts_info = fgts_info.replace('\xa0', '')
            fgts_info = fgts_info.split('\n')

            for info in enumerate(fgts_info):
                fgts = "SIM"
                if "Imóvel NÃO aceita utilização de FGTS" in str(info):
                    fgts = "NÃO"
                if "Permite financiamento na linha de crédito SBPE (Consulte Condições)" in str(info) or "Imovel ACEITA financiamento" in str(info):
                    financiamento = "SIM"
                if "Imóvel NÃO aceita financiamento habitacional" in str(info):
                    financiamento = "NÃO"
                if "Imóvel NÃO aceita parcelamento" in str(info):
                    parcelamento = "NÃO"
                if " Imóvel ACEITA  parcelamento" in str(info):
                    parcelamento = "SIM"

                if "Imóvel NÃO aceita consórcio" in str(info):
                    consorcio = "NÃO"
                if " Imóvel ACEITA  consórcio" in str(info):
                    consorcio = "SIM"

            df.at[index, 'Banco'] = 'Caixa'
            df.at[index, 'Acesso'] = " "
            df.at[index, 'FGTS'] = fgts
            df.at[index, 'Financiamento'] = financiamento
            df.at[index, 'Parcelamento'] = parcelamento
            df.at[index, 'Consórcio'] = consorcio
            df.at[index, '1° Leilão'] = leilao_01
            df.at[index, '2° Leilão'] = leilao_02

            # Estimativa de tempo restante
            if index > 0:  # Evitar divisão por zero
                estimated_total_time = elapsed_time / (index + 1) * numero_de_linhas
                remaining_time = estimated_total_time - elapsed_time
            else:
                remaining_time = None  # Sem estimativa no primeiro loop

            if (now - ultimo_salvamento) >= timedelta(minutes=30):
                df.to_excel(nome_excel)    # Chama a função para salvar o Excel
                ultimo_salvamento = now

            # Chama a função para imprimir os dados
            imprimir_consulta(index, formatted_date, faltam, elapsed_time, remaining_time)
        except Exception as e:
            continue
    nome_excel = name_file.replace('csv', 'xlsx')
    df.to_excel(nome_excel)       

def imprimir_consulta(index, formatted_date, faltam, elapsed_time, remaining_time):
    """Imprime as informações de consulta em uma linha."""
    output = (f'Consulta: {index} | Data e hora: {formatted_date} | '
              f'Faltam: {faltam} consultas | '
              f'Tempo decorrido: {elapsed_time} | '
              f'Tempo estimado para terminar: {remaining_time}' if remaining_time is not None 
              else f'Tempo decorrido: {elapsed_time}')
    
    print(output)  
def main():
    playwright, browser, page, name_file = configurar_navegador()
    try:
        df = download_file(page, name_file)
        busca_site_caixa(page, name_file, df)
    except Exception as e:
        print(f"Erro durante a execução: {e}")
    finally:
        browser.close()
        playwright.stop()

if __name__ == "__main__":
    main()
