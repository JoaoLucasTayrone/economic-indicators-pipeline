import requests
from datetime import date, timedelta

data_inicial = (date.today() - timedelta(date.today().day - 1))
data_final = date.today() - timedelta(days=1)
url = 'https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoDolarPeriodo(dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)'

parametros = {
    '@dataInicial': f"'{data_inicial.strftime('%m-%d-%Y')}'",
    '@dataFinalCotacao': f"'{data_final.strftime('%m-%d-%Y')}'",
    '$format': 'json'
}

cotacao_mensal = (requests.get(url, params=parametros)).json()
valores = [cotacao['cotacaoVenda'] for cotacao in cotacao_mensal['value']]
media = sum(valores) / len(valores)

