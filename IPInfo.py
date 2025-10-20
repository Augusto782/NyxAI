import requests
import os

IPINFO_API_KEY = os.getenv('IPINFO_API_KEY')

def ipinfo() -> dict | None:
    """
    Use para obter detalhes de localização do usuário usando um serviço de geolocalização por IP.
    Além de vc poder usar isso com a ferramenta de clima para saber, onde o usúario mora e falar o clima Retorna um dicionário com 'ip', 'city', 'region', 'country', 'org' ou None.
    """
    global IPINFO_API_KEY
    if not IPINFO_API_KEY: 
        print("DEBUG: IPINFO_API_KEY não configurada. Não é possível obter a cidade por IP.")
        return None 

    try:
        response = requests.get(f"https://ipinfo.io/json?token={IPINFO_API_KEY}")
        response.raise_for_status() # Lança um erro para status de resposta HTTP ruins (4xx ou 5xx)
        data = response.json()

        ip_details = {
            'ip': data.get('ip', 'Não disponível'),
            'city': data.get('city', 'Não disponível'),
            'region': data.get('region', 'Não disponível'),
            'country': data.get('country', 'Não disponível'),
            'org': data.get('org', 'Não disponível') # Organização (ISP)
        }
        
        if ip_details['city'] != 'Não disponível':
            print(f"DEBUG: Detalhes de IP obtidos: {ip_details}")
            return ip_details
        else:
            print("DEBUG: Não foi possível obter detalhes de localização a partir do IP.")
            return None
    except requests.exceptions.RequestException as e:
        print(f"DEBUG: Erro ao obter cidade por IP: {e}")
        return None
    except Exception as e:
        print(f"DEBUG: Erro inesperado ao processar IPinfo: {e}")
        return None