import google.generativeai as genai

# --- Mocks e Imports de Ferramentas (Simulando o ambiente real) ---
try:
    from Google_Search import google_search
    from Browser_Url import browse_url
    from IPInfo import ipinfo
    from Weather import obter_clima
    from Analise_de_Sentimentos import analisar_emocoes_local_bert
except ImportError:
    print("AVISO: Módulos de ferramentas (Google_Search, etc.) não encontrados. Usando Mocks.")
    def google_search(query): return f"Placeholder Search Result for: {query}"
    def browse_url(url): return f"Placeholder Browse Result for: {url}"
    def ipinfo(): return "Placeholder IP Info: Formosa"
    def obter_clima(cidade): return f"Placeholder Weather for: {cidade}"
    def analisar_emocoes_local_bert(text): return f"Placeholder Sentiment: Neutral for '{text}'"

# --- Definição das Tools para o Modelo Gemini ---

GEMINI_TOOLS = [
    genai.protos.FunctionDeclaration(
        name='google_search',
        description='Executa uma pesquisa no Google e retorna os resultados. Use para encontrar informações gerais ou links relevantes. Caso precise de mais informações ou informações mais robustas use em conjunto ao browse_url para receber um contexto maior.',
        parameters=genai.protos.Schema(
            type=genai.protos.Type.OBJECT,
            properties={
                'query': genai.protos.Schema(type=genai.protos.Type.STRING,
                                             description='A consulta de pesquisa.')
            },
            required=['query']
        )
    ),
    genai.protos.FunctionDeclaration(
        name='browse_url',
        description='Use para abrir links de páginas web para obter um contexto maior do conteúdo.',
        parameters=genai.protos.Schema(
            type=genai.protos.Type.OBJECT,
            properties={
                'url': genai.protos.Schema(type=genai.protos.Type.STRING,
                                             description='A URL da página a ser navegada.')
            },
            required=['url']
        )
    ),
    genai.protos.FunctionDeclaration(
        name='ipinfo',
        description='Busca informações de IP, Cidade, Estado, País, Org e Provedor do usuário. Use se precisar de contexto geográfico, como para o clima, sem que a cidade seja especificada. Se não souber a cidade para o clima, use essa ferramenta.',
        parameters=genai.protos.Schema(
            type=genai.protos.Type.OBJECT,
            properties={},
        )
    ),
    genai.protos.FunctionDeclaration(
        name='obter_clima',
        description='Busca informações de clima para uma cidade específica. Use quando o usuário perguntar sobre a previsão do tempo ou temperatura. Se não souber a cidade use o IP info para descobrir.',
        parameters=genai.protos.Schema(
            type=genai.protos.Type.OBJECT,
            properties={
                'cidade': genai.protos.Schema(type=genai.protos.Type.STRING,
                                             description='O nome da cidade.')
            },
            required=['cidade']
        )
    ),
    genai.protos.FunctionDeclaration(
        name='analisar_emocoes_local_bert',
        description='Analisa o sentimento de um texto e identifica emoções. Use SEMPRE QUE VC JULGAR MINIMAMENTE NESCESSÁRIO, é uma ferramenta nativa, ou seja, de uso ilimitado e claro NUNCA revele o resultado da análise na resposta, apenas use o resultado para responder o usuário.',
        parameters=genai.protos.Schema(
            type=genai.protos.Type.OBJECT,
            properties={
                'text': genai.protos.Schema(type=genai.protos.Type.STRING,
                                             description='O texto a ser analisado.')
            },
            required=['text']
        )
    )
]

# --- Lógica de Execução das Ferramentas ---

def execute_tool(tool_name: str, tool_args: dict) -> str:
    """Executa a função da ferramenta com base no nome e argumentos fornecidos pela IA."""
    tool_output = ""

    try:
        if tool_name == "google_search":
            search_query = tool_args.get('query')
            if not search_query:
                tool_output = "ERRO_FERRAMENTA: Consulta de pesquisa vazia ou inválida fornecida pela IA."
            else:
                tool_output = google_search(search_query)

        elif tool_name == "browse_url":
            url_to_browse = tool_args.get('url')
            if not url_to_browse:
                tool_output = "ERRO_FERRAMENTA: URL vazia ou inválida fornecida pela IA para navegação."
            else:
                tool_output = browse_url(url_to_browse)

        elif tool_name == "ipinfo":
            tool_output = ipinfo()
            tool_output = str(tool_output)

        elif tool_name == "obter_clima":
            cidade_do_clima = tool_args.get('cidade')
            if not cidade_do_clima:
                tool_output = "ERRO_FERRAMENTA: Nome da cidade vazio ou inválido fornecido pela IA para buscar o clima."
            else:
                tool_output = obter_clima(cidade_do_clima)

        elif tool_name == "analisar_emocoes_local_bert":
            text_to_analyze = tool_args.get('text')
            if not text_to_analyze:
                tool_output = "ERRO_FERRAMENTA: Texto vazio ou inválido fornecido pela IA para análise de sentimento."
            else:
                tool_output = analisar_emocoes_local_bert(text_to_analyze)
                
        else:
            tool_output = f"ERRO_FERRAMENTA: Ferramenta desconhecida solicitada: {tool_name}"

    except Exception as e:
        tool_output = f"ERRO_FERRAMENTA: Falha na execução da ferramenta {tool_name}: {str(e)}"
    
    return tool_output