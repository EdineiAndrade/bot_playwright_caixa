import requests
from lxml import html

# URL do site que você quer acessar
url = "https://venda-imoveis.caixa.gov.br/sistema/detalhe-imovel.asp?hdnOrigem=index&hdnimovel=1555507803005"

# Fazer a requisição GET
response = requests.get(url)

# Verificar se a requisição foi bem-sucedida
if response.status_code == 200:
    # Parsear o conteúdo da página HTML
    tree = html.fromstring(response.content)
    
    # Usar XPath para extrair um elemento (exemplo: todos os títulos <h1>)
    titulos = tree.xpath('//*[@id="dadosImovel"]/div/div[2]/p/b')  # Seleciona o texto de todos os <h1> na página
    
    # Exibir os títulos encontrados
    for titulo in titulos:
        print(f"Título encontrado: {titulo}")
else:
    print(f"Erro ao acessar o site. Código de status: {response.status_code}")
