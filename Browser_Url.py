import requests
import re
from bs4 import BeautifulSoup

def browse_url(url: str) -> str:
    """
    Navega até uma URL, extrai e retorna o texto visível da página.
    Limita o texto retornado para evitar sobrecarga do modelo.
    """
    print(f"DEBUG: Tentando navegar para a URL: {url}")
    try:
        # Adiciona um User-Agent para simular um navegador real e evitar bloqueios
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10) # Timeout para evitar travamentos
        response.raise_for_status() # Levanta um erro para respostas HTTP ruins (4xx ou 5xx)

        soup = BeautifulSoup(response.text, 'html.parser')

        # Remove elementos de script, estilo, cabeçalhos, rodapés e navegação
        for element in soup(['script', 'style', 'header', 'footer', 'nav', 'aside']):
            element.decompose()

        # Obtém o texto limpo
        text = soup.get_text()

        # Quebra em linhas, remove linhas vazias/apenas espaços e múltiplos espaços
        lines = (line.strip() for line in text.splitlines())
        chunks = (re.sub(r'\s+', ' ', phrase).strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)

        # Limita o tamanho do texto para não sobrecarregar o LLM
        max_chars = 8000 # Limite razoável para o contexto do LLM
        if len(text) > max_chars:
            text = text[:max_chars] + "\n... [Conteúdo truncado devido ao tamanho]"
            print(f"DEBUG: Conteúdo da URL truncado para {max_chars} caracteres.")

        return text
    except requests.exceptions.RequestException as e:
        return f"ERRO_FERRAMENTA: browse_url falhou. Detalhes: {e}"
    except Exception as e:
        return f"ERRO_FERRAMENTA: browse_url falhou inesperadamente. Detalhes: {e}"