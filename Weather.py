import requests
import os

API_KEY_CLIMA = os.getenv('API_KEY_CLIMA')

def obter_clima(cidade: str) -> str:
    """
    Obtém informações de clima de uma cidade usando a API OpenWeatherMap.
    """
    global API_KEY_CLIMA 
    if not API_KEY_CLIMA:
        return "Erro: Chave da API de clima (API_KEY_CLIMA) não definida."

    url = f"https://api.openweathermap.org/data/2.5/weather?q={cidade}&appid={API_KEY_CLIMA}&lang=pt_br&units=metric"
    try:
        resposta = requests.get(url).json()
        
        if resposta.get('cod') == 200:
            temperatura = resposta['main']['temp']
            descricao = resposta['weather'][0]['description']
            return f"A temperatura em {cidade} é de {temperatura:.1f}°C, com {descricao}."
        else:
            return f"Não foi possível obter o clima para a cidade informada: {resposta.get('message', 'Erro desconhecido')}"
    except requests.exceptions.RequestException as e:
        return f"Erro ao conectar com a API de clima: {e}. Verifique sua conexão ou a chave da API."
    except Exception as e:
        return f"Erro inesperado ao processar dados do clima: {e}"
