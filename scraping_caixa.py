from playwright.async_api import async_playwright
import asyncio
import shutil
import pandas as pd
from datetime import datetime
import time
import os
import pandas as pd
import re

async def configurar_navegador():
    name_file = path_file()
    downloads_path = os.path.dirname(name_file)
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(args=["--window-position=0,0"],headless=False,downloads_path=downloads_path)
    page = await browser.new_page()
    return playwright, browser, page, name_file

async def download_file(page, name_file):        
    base_url = "https://venda-imoveis.caixa.gov.br/sistema/download-lista.asp"
    await page.goto(base_url)
    await page.locator('#cmb_estado').select_option('geral')
    
    async with page.expect_download() as download_info:
        await page.locator('#btn_next1').click()
    download = await download_info.value
    await download.save_as(name_file)              
    await download.delete()
    pd.options.display.max_columns = None
    df = pd.read_csv(name_file,skiprows=2,delimiter=';',encoding = 'latin-1')
    df = clean_dataframe(df)
    return df 
 
# Função para remover caracteres ilegais
async def remove_illegal_characters(value):
    if isinstance(value, str):
        return re.sub(r'[\x00-\x1F\x7F-\x9F]', '', value)
    return value

# Função para limpar o DataFrame
async def clean_dataframe(df):
    # Aplicar a função de limpeza a todas as colunas do DataFrame
    for col in df.columns:
        df[col] = df[col].apply(remove_illegal_characters)
    return df

async def path_file():

    now = datetime.now()
    formatted_date = now.strftime("%d-%m-%y_%H-%M-%S")

    user_path = os.environ.get('USERPROFILE')
    user_dw = os.path.join(user_path,'Downloads')
    path_file = os.path.join(user_dw,'imoveis')

    name_file = os.path.join(path_file,f'baixados_{formatted_date}.csv')
    if os.path.exists(path_file):
        shutil.rmtree(path_file)
    os.mkdir(path_file)

    return name_file

async def busca_site_caixa(page, name_file,df):
    contt = 0
    for index, row in df.iterrows():
        now = datetime.now()
        formatted_date = now.strftime("%d/%m/%y %H:%M:%S")
        time.sleep(1)
        link = row['Link de acesso']
        await page.goto(link)
        # Informações do leilão
        seletor_1 = '//*[@class="related-box"]/span/i'

        # Verificar se o elemento existe e pegar a contagem
        count = await page.locator(seletor_1).count()

        if count > 0:
            # Garantir que há pelo menos dois elementos para evitar IndexError
            if count >= 2:
                leilao_01 = await page.locator('//*[@class="related-box"]/span[4]').inner_text()
                leilao_02 = await page.locator('//*[@class="related-box"]/span[5]').inner_text()
            elif count == 1:
                leilao_01 = await page.locator('//*[@class="related-box"]/span[4]').inner_text()
                leilao_02 = 'sem informações'
        else:
            leilao_01 = 'sem informações'
            leilao_02 = 'sem informações'
    
        fgts_info = await page.locator('//*[@class="related-box"]/p[3]').inner_text()
        fgts_info = fgts_info.replace('\xa0','')
        fgts_info = fgts_info.split('\n')
               
       # Preencher cada coluna 
        df.at[index, 'Banco'] = 'Caixa'
        df.at[index, 'Acesso'] = formatted_date
        df.at[index, 'FGTS'] = 'Não'
        df.at[index, 'Financiamento'] = fgts_info[0]
        df.at[index, 'Parcelamento'] = fgts_info[1]
        df.at[index, 'Consórcio'] = fgts_info[2]
        df.at[index, '1° Leilão'] = leilao_01
        df.at[index, '2° Leilão'] = leilao_02
        print(f'Consulta: {index} data e hora:{formatted_date}')
        
        if contt > 1000:
            nome_excel = name_file.replace('csv','xlsx')
            df.to_excel(nome_excel)
            break
    
async def main():
    playwright, browser, page, name_file = await configurar_navegador()
    try:
        df = await download_file(page, name_file)
        await busca_site_caixa(page, name_file,df)
        
    finally:
        await browser.close()
        await playwright.stop()

if __name__ == "__main__":
    asyncio.run(main())
