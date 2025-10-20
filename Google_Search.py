import os
from googleapiclient.discovery import build

def google_search(query: str) -> str:
    """
    Executa uma pesquisa no Google e retorna os resultados como uma string formatada.
    """
    GOOGLE_SEARCH_API_KEY = os.getenv('GOOGLE_SEARCH_API_KEY')
    GOOGLE_SEARCH_CX_ID = os.getenv('GOOGLE_SEARCH_CX_ID')

    if not GOOGLE_SEARCH_API_KEY or not GOOGLE_SEARCH_CX_ID:
        return "ERRO_FERRAMENTA: As variáveis de ambiente 'GOOGLE_SEARCH_API_KEY' ou 'GOOGLE_SEARCH_CX_ID' não estão definidas."

    try:
        service = build("customsearch", "v1", developerKey=GOOGLE_SEARCH_API_KEY)
        res = service.cse().list(q=query, cx=GOOGLE_SEARCH_CX_ID).execute()
        
        results = []
        if 'items' in res:
            for item in res['items'][:5]: # Limita a 5 resultados para não sobrecarregar
                title = item.get('title', 'Sem título')
                link = item.get('link', 'Sem link')
                snippet = item.get('snippet', 'Sem descrição')
                results.append(f"Título: {title}\nLink: {link}\nTrecho: {snippet}\n---")
        
        if not results:
            return "Nenhum resultado encontrado para a pesquisa."
        
        return "\n".join(results)
    except Exception as e:
        # Retorna uma mensagem de erro detalhada se a pesquisa falhar
        return f"ERRO_FERRAMENTA: google_search falhou. Detalhes: {e}"
