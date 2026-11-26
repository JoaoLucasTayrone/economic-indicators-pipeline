import requests
from datetime import date, timedelta

data_inicial = (date.today() - timedelta(date.today().day - 1))
data_final = date.today() - timedelta(days=1)

# Extração das APIS

#Cotação do Dolar
url_dolar = 'https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoDolarPeriodo(dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)'

#Selic
url_selic = 'https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados'

#IPCA
url_ipca = 'https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados'

parametros = {
    '@dataInicial': f"'{data_inicial.strftime('%m-%d-%Y')}'",
    '@dataFinalCotacao': f"'{data_final.strftime('%m-%d-%Y')}'",
    '$format': 'json'
}

params = {
    'formato':'json',
    'dataInicial': f"{data_inicial.strftime('%d/%m/%Y')}",
    'dataFinal': f"{data_final.strftime('%d/%m/%Y')}",
}

ipca = (requests.get(url_ipca, params=params)).json()
meta_selic = (requests.get(url_selic, params=params)).json()
cotacao_mensal = (requests.get(url_dolar, params=parametros)).json()
valores = [cotacao['cotacaoVenda'] for cotacao in cotacao_mensal['value']]
media = sum(valores) / len(valores)