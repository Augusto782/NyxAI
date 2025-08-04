import google.generativeai as genai
import os
import sqlite3
import tkinter as tk
import io
import base64
import requests
import re
from datetime import datetime
from dotenv import load_dotenv
from googleapiclient.discovery import build
from bs4 import BeautifulSoup
from PIL import Image, ImageTk
from tkinter import filedialog 

load_dotenv() # Carrega as variáveis do arquivo .env

# --- Configuração da API ---
try:
    genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
    GOOGLE_SEARCH_API_KEY = os.getenv('GOOGLE_SEARCH_API_KEY')
    GOOGLE_SEARCH_CX_ID = os.getenv('GOOGLE_SEARCH_CX_ID')
    PROMPT_IA = os.getenv('PROMPT_IA')
    API_KEY_CLIMA = os.getenv('API_KEY_CLIMA')
    IPINFO_API_KEY = os.getenv('IPINFO_API_KEY')
    YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY') # Nova chave da API do YouTube

    if not GOOGLE_SEARCH_API_KEY or not GOOGLE_SEARCH_CX_ID:
        raise ValueError("Variáveis de ambiente 'GOOGLE_SEARCH_API_KEY' ou 'GOOGLE_SEARCH_CX_ID' não definidas.")
    
    if not API_KEY_CLIMA:
        print("Aviso: Variável de ambiente 'API_KEY_CLIMA' não definida. A funcionalidade de clima pode não funcionar.")
    
    if not IPINFO_API_KEY:
        print("Aviso: Variável de ambiente 'IPINFO_API_KEY' não definida. A funcionalidade de detecção automática de cidade por IP pode não funcionar.")

    if not YOUTUBE_API_KEY:
        print("Aviso: Variável de ambiente 'YOUTUBE_API_KEY' não definida. A funcionalidade do YouTube pode não funcionar.")

except Exception as e:
    print(f"Erro ao configurar a API: {e}")
    print("Verifique se as variáveis de ambiente 'GOOGLE_API_KEY', 'GOOGLE_SEARCH_API_KEY', 'GOOGLE_SEARCH_CX_ID', 'API_KEY_CLIMA', 'IPINFO_API_KEY' e 'YOUTUBE_API_KEY' estão definidas no seu arquivo .env.")
    import sys
    sys.exit(1)

system_instruction = PROMPT_IA

# --- Ferramenta de Busca na Internet ---
def google_search(query: str) -> str:
    """
    Executa uma pesquisa no Google e retorna os resultados como uma string formatada.
    """
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

# --- Funções para a API de Clima ---
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

# --- Função para obter detalhes de localização via IP ---
def obter_cidade_por_ip() -> dict | None:
    """
    Tenta obter detalhes de localização do usuário usando um serviço de geolocalização por IP.
    Retorna um dicionário com 'ip', 'city', 'region', 'country', 'org' ou None.
    Requer a chave IPINFO_API_KEY no .env
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

# --- Ferramenta de Navegação (Browsing Tool) ---
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
        max_chars = 4000 # Limite razoável para o contexto do LLM
        if len(text) > max_chars:
            text = text[:max_chars] + "\n... [Conteúdo truncado devido ao tamanho]"
            print(f"DEBUG: Conteúdo da URL truncado para {max_chars} caracteres.")

        return text
    except requests.exceptions.RequestException as e:
        return f"ERRO_FERRAMENTA: browse_url falhou. Detalhes: {e}"
    except Exception as e:
        return f"ERRO_FERRAMENTA: browse_url falhou inesperadamente. Detalhes: {e}"

# --- Ferramenta de Busca no YouTube ---
def youtube_search(video_id: str) -> str:
    """
    Busca informações sobre um vídeo do YouTube a partir de seu ID.
    Retorna um resumo do título, descrição e estatísticas do vídeo.
    """
    global YOUTUBE_API_KEY
    if not YOUTUBE_API_KEY:
        return "Erro: Chave da API do YouTube (YOUTUBE_API_KEY) não definida."

    try:
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

        request = youtube.videos().list(
            part='snippet,statistics',
            id=video_id
        )
        response = request.execute()

        if not response.get('items'):
            return "Nenhum vídeo encontrado com o ID fornecido."

        video_info = response['items'][0]
        snippet = video_info['snippet']
        statistics = video_info['statistics']

        title = snippet.get('title', 'Sem título')
        # Garante que 'description' é uma string para evitar erros de tipo
        description = str(snippet.get('description', 'Sem descrição')) 
        published_at = snippet.get('publishedAt', 'Não disponível')
        view_count = statistics.get('viewCount', '0')
        like_count = statistics.get('like_count', '0')
        comment_count = statistics.get('comment_count', '0')

        # Formata a descrição para evitar que seja muito longa
        short_description = description[:200] + '...' if len(description) > 200 else description

        return (
            f"Informações do vídeo do YouTube:\n"
            f"Título: {title}\n"
            f"Publicado em: {published_at}\n"
            f"Visualizações: {view_count}\n"
            f"Curtidas: {like_count}\n"
            f"Comentários: {comment_count}\n"
            f"Descrição (trecho): {short_description}"
        )

    except Exception as e:
        return f"ERRO_FERRAMENTA: youtube_search falhou. Detalhes: {e}"


# --- Model com Tools ---
# Definimos as ferramentas usando FunctionDeclaration
tools = [
    genai.protos.FunctionDeclaration(
        name='google_search',
        description='Executa uma pesquisa no Google e retorna os resultados como uma string formatada. Utilize para encontrar informações gerais ou links relevantes.',
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
        description='Navega até uma URL específica e extrai o texto visível da página. **Utilize esta ferramenta APENAS quando precisar ler o conteúdo COMPLETO de um artigo, documento ou página da web para obter detalhes aprofundados que não estão disponíveis nos resultados da pesquisa.**',
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
        name='youtube_search',
        description='Busca informações detalhadas sobre um vídeo do YouTube, como título, descrição e estatísticas, a partir de seu ID. Pode ser ativada com o ID do vídeo ou uma URL completa do YouTube.',
        parameters=genai.protos.Schema(
            type=genai.protos.Type.OBJECT,
            properties={
                'video_id': genai.protos.Schema(type=genai.protos.Type.STRING,
                                                 description='O ID do vídeo do YouTube.')
            },
            required=['video_id']
        )
    )
]

# Definimos a lista de modelos a serem tentados em ordem de preferência
MODEL_PRIORITY = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-flash']


# --- Funções para o Banco de Dados ---
DB_NAME = 'historico_chat.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            image_data BLOB NULL
        )
    ''')
    conn.commit()

    # Adiciona a coluna image_data se ela não existir (para compatibilidade com versões anteriores)
    cursor.execute("PRAGMA table_info(messages)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'image_data' not in columns:
        cursor.execute("ALTER TABLE messages ADD COLUMN image_data BLOB NULL")
        conn.commit()
        print("Coluna 'image_data' adicionada à tabela 'messages'.")
    
    conn.close()
    print(f"Banco de dados '{DB_NAME}' inicializado.")

def save_message(role, content, image_data=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO messages (role, content, image_data) VALUES (?, ?, ?)", (role, content, image_data))
    conn.commit()
    conn.close()

def get_last_messages(num_messages=1000):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT role, content, image_data FROM messages ORDER BY id DESC LIMIT ?", (num_messages,))
    rows = cursor.fetchall()
    conn.close()

    history = []
    for role, content, image_data in reversed(rows):
        parts = []
        if content:
            parts.append({'text': content})
        if image_data:
            # A API do Gemini espera a string base64 para inline_data
            encoded_image_data = base64.b64encode(image_data).decode('utf-8') 
            parts.append({'inline_data': {'mime_type': 'image/jpeg', 'data': encoded_image_data}}) # Assumindo JPEG
        history.append({'role': role, 'parts': parts})
    return history

def clear_history_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages")
    conn.commit()
    conn.close()
    print(f"Histórico do banco de dados '{DB_NAME}' limpo.")

# --- Variáveis globais para armazenar a imagem selecionada ---
selected_image_pil = None # Objeto PIL Image
selected_image_tk = None  # Objeto ImageTk.PhotoImage para exibição no Tkinter

def selecionar_imagem():
    """Abre uma janela para selecionar um arquivo de imagem e carrega os dados."""
    global selected_image_pil, selected_image_tk
    file_path = filedialog.askopenfilename(
        title="Selecione uma imagem",
        filetypes=[("Arquivos de Imagem", "*.jpg *.jpeg *.png *.gif *.bmp")]
    )
    if file_path:
        try:
            img = Image.open(file_path)
            
            # CONVERSÃO PARA RGB PARA EVITAR ERRO RGBA para JPEG ao salvar
            if img.mode == 'RGBA':
                img = img.convert('RGB')

            # Redimensiona para um tamanho razoável para exibição e para o modelo
            img.thumbnail((300, 300), Image.Resampling.LANCZOS) 
            
            selected_image_pil = img # Armazena o objeto PIL Image
            selected_image_tk = ImageTk.PhotoImage(img) # Cria PhotoImage para exibição

            # Armazena a referência em uma lista anexada ao chat_display para persistência
            chat_display.image_references.append(selected_image_tk) 

            chat_display.config(state=tk.NORMAL)
            chat_display.insert(tk.END, "Você enviou uma imagem:\n", "user_content_tag")
            chat_display.image_create(tk.END, image=selected_image_tk)
            chat_display.insert(tk.END, "\n\n")
            chat_display.config(state=tk.DISABLED)
            chat_display.see(tk.END)

            entry_message.delete(0, tk.END) # Limpa a caixa de texto
            print(f"DEBUG: Imagem carregada e exibida. Objeto PIL: {selected_image_pil}")

        except Exception as e:
            print(f"ERRO: Erro ao carregar imagem em selecionar_imagem: {e}")
            selected_image_pil = None
            selected_image_tk = None


# --- Função Principal de Geração de Resposta da IA com Banco de Dados ---
def gerar_resposta_ia(pergunta, image_pil=None): # Agora aceita o objeto PIL Image
    print(f"DEBUG: Início de gerar_resposta_ia. Pergunta: '{pergunta}', Imagem PIL presente: {image_pil is not None}")
    
    contexto_adicional = [] 

    # --- Lógica para o Horário ---
    palavras_chave_tempo = ["hora", "horas", "horário", "dia", "mês", "ano", "data"]
    if any(palavra in pergunta.lower() for palavra in palavras_chave_tempo):
        agora = datetime.now()
        data_hora_completa = agora.strftime("A data e hora atual é: %A, %d de %B de %Y, %H:%M.")
        contexto_adicional.append(data_hora_completa)
        print("DEBUG: Adicionando informação de data e horário ao contexto.")

    # --- Lógica para Localização por IP ---
    palavras_chave_localizacao = ["onde estou", "minha localização", "meu ip", "qual meu ip", "localização", "provedor", "internet", "cidade", "país", "estado"]
    if any(palavra in pergunta.lower() for palavra in palavras_chave_localizacao):
        ip_detalhes = obter_cidade_por_ip()
        if ip_detalhes:
            localizacao_info = (
                f"Sua localização detectada por IP é: "
                f"IP: {ip_detalhes['ip']}, "
                f"Cidade: {ip_detalhes['city']}, "
                f"Região: {ip_detalhes['region']}, "
                f"País: {ip_detalhes['country']}, "
                f"Provedor: {ip_detalhes['org']}."
            )
            contexto_adicional.append(localizacao_info)
            print("DEBUG: Adicionando informações de localização por IP ao contexto.")
        else:
            contexto_adicional.append("Não foi possível detectar sua localização por IP.")
            print("DEBUG: Não foi possível detectar localização por IP, adicionando aviso ao contexto.")

    # --- Lógica para o Clima ---
    palavras_chave_clima = ["clima", "tempo", "previsão"]
    if any(palavra in pergunta.lower() for palavra in palavras_chave_clima):
        cidade_para_clima = None
        ip_detalhes_clima = obter_cidade_por_ip()
        if ip_detalhes_clima and ip_detalhes_clima['city'] != 'Não disponível':
            cidade_para_clima = ip_detalhes_clima['city']
            print(f"DEBUG: Cidade obtida por IP para o clima: {cidade_para_clima}")
        
        if not cidade_para_clima:
            match = re.search(r'(?:em|na|de|para)\s+([A-Za-zÀ-ú\s]+)(?:\?|\.|$)', pergunta, re.IGNORECASE)
            if match:
                cidade_extraida = match.group(1).strip()
                if len(cidade_extraida) > 2 and not any(p in cidade_extraida.lower() for p in palavras_chave_clima):
                    cidade_para_clima = cidade_extraida
                    print(f"DEBUG: Cidade extraída da pergunta para o clima: {cidade_para_clima}")

        if not cidade_para_clima:
            cidade_para_clima = "Brasília" 
            print(f"DEBUG: Não foi possível detectar a cidade, usando fallback para clima: {cidade_para_clima}...")

        clima_info = obter_clima(cidade_para_clima)
        contexto_adicional.append(clima_info)
        print("DEBUG: Adicionando informação de clima ao contexto.")


    prompt_final_para_ia = pergunta
    if contexto_adicional:
        contexto_string = " ".join(contexto_adicional)
        prompt_final_para_ia = (
            f"As seguintes informações foram fornecidas: {contexto_string}. "
            f"Agora, responda à pergunta do usuário: {pergunta}"
        )
        print(f"DEBUG: Prompt final enviado para IA: {prompt_final_para_ia[:200]}...")
    else:
        print("DEBUG: Nenhum contexto adicional de tempo/clima/localização necessário.")

    # --- Prepara o conteúdo para o modelo (texto + imagem, se houver) ---
    model_content = []
    image_data_for_api = None
    if image_pil:
        try:
            # Converte o objeto PIL Image para bytes JPEG para enviar à API
            img_byte_arr = io.BytesIO()
            image_pil.save(img_byte_arr, format='JPEG')
            image_data_for_api = img_byte_arr.getvalue()
            print(f"DEBUG: Imagem PIL convertida para bytes JPEG. Tamanho: {len(image_data_for_api)} bytes.")

            # Codificando para Base64, pois é um requisito da API do Gemini.
            model_content.append({
                'inline_data': {
                    'mime_type': 'image/jpeg',
                    'data': base64.b64encode(image_data_for_api).decode('utf-8')
                }
            })
        except Exception as e:
            print(f"ERRO: Não foi possível converter a imagem PIL para bytes para a API: {e}")
            # Continua sem a imagem se houver erro na conversão
    
    if prompt_final_para_ia:
        model_content.append({'text': prompt_final_para_ia})

    # Verifica se o conteúdo a ser enviado está vazio
    if not model_content:
        print("ERRO: 'model_content' está vazio. Não há texto nem imagem para enviar.")
        return "Não consegui processar sua solicitação. Por favor, forneça texto ou uma imagem válida."

    # --- Inicializa a sessão de chat AQUI ---
    history_from_db = get_last_messages(num_messages=10)
    
    formatted_history = []
    for msg in history_from_db:
        parts_for_model = []
        for part in msg['parts']:
            if isinstance(part, dict) and 'inline_data' in part:
                parts_for_model.append(part)
            elif isinstance(part, dict) and 'text' in part:
                parts_for_model.append(part)
        formatted_history.append({'role': msg['role'], 'parts': parts_for_model})

    final_response_text = ""
    last_error = None

    # Tenta com os modelos em ordem de prioridade
    for model_name_to_try in MODEL_PRIORITY:
        print(f"DEBUG: Tentando gerar resposta com o modelo: '{model_name_to_try}'")
        try:
            current_model = genai.GenerativeModel(model_name_to_try, system_instruction=system_instruction, tools=tools)
            current_chat_session = current_model.start_chat(history=formatted_history)

            # Lógica para extrair ID do YouTube da URL (tratamento inicial)
            youtube_video_id = None
            youtube_pattern = r'(?:https?://)?(?:www\.)?(?:m\.)?(?:youtube\.com|youtu\.be)/(?:watch\?v=|embed/|v/|)([a-zA-Z0-9_-]{11})(?:\S+)?'
            match_youtube = re.search(youtube_pattern, pergunta)
            
            if match_youtube:
                youtube_video_id = match_youtube.group(1)
                print(f"DEBUG: ID do YouTube '{youtube_video_id}' extraído da pergunta.")
                try:
                    print(f"Nyx decidiu buscar informações do vídeo do YouTube com ID: '{youtube_video_id}' (extraído da URL)")
                    tool_output_youtube = youtube_search(youtube_video_id)
                    print(f"DEBUG: Resultados do YouTube (primeiros 200 chars): {tool_output_youtube[:200]}...")
                    
                    current_response = current_chat_session.send_message(
                        genai.protos.Part(
                            function_response=genai.protos.FunctionResponse(
                                name='youtube_search',
                                response={'result': tool_output_youtube}
                            )
                        )
                    )
                    if current_response.parts and not current_response.parts[0].function_call:
                        final_response_text = current_response.text
                        break # Sai do loop de modelos se a resposta for bem-sucedida
                    else:
                        print("DEBUG: Resposta após YouTube ainda é uma function_call, continuando para o loop principal.")
                except Exception as tool_e:
                    final_response_text = f"Erro ao executar a ferramenta youtube_search com a URL: {tool_e}"
                    print(f"DEBUG: {final_response_text}")
                    # Não quebra o loop, tenta o próximo modelo
                    last_error = tool_e 
                    continue # Tenta o próximo modelo se a ferramenta YouTube falhar

            # Se não houve chamada inicial de YouTube ou se a resposta do YouTube ainda era uma function_call,
            # iniciamos ou continuamos com o loop principal de processamento de ferramentas.
            if 'current_response' not in locals() or (current_response.parts and current_response.parts[0].function_call):
                current_response = current_chat_session.send_message(model_content)

            # Loop para processar múltiplas chamadas de ferramenta
            MAX_TOOL_CALLS = 5 # Limite para evitar loops infinitos
            tool_call_count = 0

            while tool_call_count < MAX_TOOL_CALLS:
                if current_response.parts and current_response.parts[0].function_call:
                    tool_call = current_response.parts[0].function_call
                    print(f"\n--- DEBUG: Modelo solicitou chamada de função: {tool_call.name} ---")
                    print(f"--- DEBUG: Argumentos: {tool_call.args} ---\n")
                    
                    tool_output = ""
                    if tool_call.name == "google_search":
                        try:
                            search_query = tool_call.args.get('query')
                            if not search_query:
                                tool_output = "ERRO_FERRAMENTA: Consulta de pesquisa vazia ou inválida fornecida pela IA."
                                print(f"DEBUG: {tool_output}")
                            else:
                                print(f"Nyx decidiu pesquisar: '{search_query}'")
                                tool_output = google_search(search_query)
                                print(f"DEBUG: Resultados da pesquisa (primeiros 200 chars): {tool_output[:200]}...")
                            
                            # Lógica para "pesquisa profunda" com browse_url
                            if "ERRO_FERRAMENTA" not in tool_output and ("pesquisa" in pergunta.lower() or "profunda" in pergunta.lower()):
                                first_link = None
                                url_match = re.search(r'Link: (https?://[^\s]+)', tool_output)
                                if url_match:
                                    first_link = url_match.group(1)
                                    print(f"DEBUG: Primeiro link encontrado nos resultados da pesquisa: {first_link}")

                                if first_link:
                                    print(f"--- DEBUG: Ativando browse_url com o primeiro link encontrado (condição 'pesquisa'/'profunda' atendida) ---")
                                    try:
                                        browse_output = browse_url(first_link)
                                        print(f"DEBUG: Conteúdo da página (primeiros 200 chars): {browse_output[:200]}...")
                                        tool_output = browse_output # Usa o output do browse como o resultado final da ferramenta
                                    except Exception as browse_e:
                                        tool_output = f"ERRO_FERRAMENTA: browse_url falhou durante pesquisa profunda. Detalhes: {browse_e}"
                                        print(f"DEBUG: {tool_output}")
                                        
                        except Exception as tool_e:
                            tool_output = f"ERRO_FERRAMENTA: google_search falhou. Detalhes: {tool_e}"
                            print(f"DEBUG: {tool_output}")
                    
                    elif tool_call.name == "browse_url": 
                        try:
                            url_to_browse = tool_call.args.get('url')
                            if not url_to_browse:
                                tool_output = "ERRO_FERRAMENTA: URL vazia ou inválida fornecida pela IA para navegação."
                                print(f"DEBUG: {tool_output}")
                            else:
                                print(f"Nyx decidiu navegar para a URL: '{url_to_browse}'")
                                tool_output = browse_url(url_to_browse)
                                print(f"DEBUG: Conteúdo da página (primeiros 200 chars): {tool_output[:200]}...")
                        except Exception as tool_e:
                            tool_output = f"ERRO_FERRAMENTA: browse_url falhou. Detalhes: {tool_e}"
                            print(f"DEBUG: {tool_output}")
                    
                    elif tool_call.name == "youtube_search": 
                        try:
                            video_id = tool_call.args.get('video_id')
                            if not video_id:
                                tool_output = "ERRO_FERRAMENTA: ID de vídeo do YouTube vazio ou inválido fornecido pela IA."
                                print(f"DEBUG: {tool_output}")
                            else:
                                print(f"Nyx decidiu buscar informações do vídeo do YouTube com ID: '{video_id}'")
                                tool_output = youtube_search(video_id)
                                print(f"DEBUG: Resultados do YouTube (primeiros 200 chars): {tool_output[:200]}...")
                        except Exception as tool_e:
                            tool_output = f"ERRO_FERRAMENTA: youtube_search falhou. Detalhes: {tool_e}"
                            print(f"DEBUG: {tool_output}")
                    else:
                        tool_output = f"DEBUG: Modelo tentou chamar uma função desconhecida: {tool_call.name}"
                        print(tool_output)

                    # Envia o resultado da ferramenta de volta para o modelo
                    current_response = current_chat_session.send_message(
                        genai.protos.Part(
                            function_response=genai.protos.FunctionResponse(
                                name=tool_call.name,
                                response={'result': tool_output}
                            )
                        )
                    )
                    tool_call_count += 1
                else:
                    # Se a resposta não for uma função, é texto, então saímos do loop
                    break 

            # Verifica se o loop terminou porque atingiu MAX_TOOL_CALLS e ainda é uma function_call
            if current_response.parts and current_response.parts[0].function_call:
                final_response_text = "Não consegui concluir a tarefa após várias tentativas com ferramentas. Por favor, tente reformular sua pergunta ou tente novamente mais tarde."
                print("DEBUG: Loop de ferramenta atingiu o limite e a última resposta ainda era uma chamada de função.")
            else:
                final_response_text = current_response.text

            if not final_response_text:
                final_response_text = "Não consegui gerar uma resposta clara. Tente novamente."
                print("DEBUG: Resposta final vazia, usando fallback.")

            # Se chegamos aqui, a resposta foi gerada com sucesso por este modelo ou houve um erro final
            break # Sai do loop de modelos se a resposta foi processada

        except Exception as e:
            print(f"Erro ao gerar resposta com o modelo '{model_name_to_try}': {e}. Tentando o próximo modelo na lista.")
            last_error = e # Armazena o último erro para exibir se todos falharem
            continue # Tenta o próximo modelo na lista

    # Se o loop de modelos terminou e não obtivemos uma resposta final
    if not final_response_text:
        error_message = f"Desculpe, ocorreu um erro ao processar sua solicitação com todos os modelos disponíveis. Sua pergunta foi cancelada. Detalhes do último erro: {last_error}. Por favor, tente novamente mais tarde."
        save_message("user", pergunta, image_data_for_api) 
        save_message("model", error_message) 
        return error_message
    else:
        save_message("user", pergunta, image_data_for_api) # Salva a imagem no histórico
        save_message("model", final_response_text)
        return final_response_text


# --- Funções da Interface Gráfica ---
def process_ai_response(user_message, image_pil=None): # Agora aceita o objeto PIL Image
    print(f"DEBUG: process_ai_response - image_pil recebida: {image_pil is not None}") 
    ai_response = gerar_resposta_ia(user_message, image_pil) # Passa o objeto PIL Image

    chat_display.config(state=tk.NORMAL)
    
    tag_indices = chat_display.tag_ranges("nyx_thinking_tag")
    if tag_indices:
        start, end = tag_indices
        chat_display.delete(start, end)
    chat_display.insert(tk.END, "Nyx:\n", "nyx_tag")
    parts = re.split(r'(\*\*.*?\*\*)', ai_response)
    
    for part in parts:
        if part.startswith('**') and part.endswith('**'):
            text_to_bold = part[2:-2]
            chat_display.insert(tk.END, text_to_bold, "nyx_content_bold_tag")
        else:
            chat_display.insert(tk.END, part, "nyx_content_tag")
            
    chat_display.insert(tk.END, "\n\n")

    chat_display.config(state=tk.DISABLED)
    chat_display.see(tk.END)
    
    global dummy_button, button_send, button_image, selected_image_pil, selected_image_tk
    if 'dummy_button' in globals() and dummy_button.winfo_exists():
        dummy_button.destroy()
    button_send = create_send_button()
    button_image = create_image_button() # Recria o botão de imagem

    entry_message.focus_set()
    selected_image_pil = None # Limpa o objeto PIL Image
    selected_image_tk = None  # Limpa a referência PhotoImage

def create_send_button():
    """Cria o botão de envio ativo."""
    btn = tk.Button(janela, text="Enviar", command=send_message, font=("Inter", 10, "bold"),
                    bg="#FF6CC2", fg="white", activebackground="#a0456f", relief=tk.RAISED, bd=3, cursor="hand2")
    btn.grid(row=1, column=2, padx=5, pady=5, sticky="e")
    return btn

def create_dummy_button():
    """Cria um botão de placeholder desativado."""
    global dummy_button
    btn = tk.Button(janela, text="Enviar", font=("Inter", 10, "bold"),
                    bg="#66334F", fg="#AAAAAA", relief=tk.RAISED, bd=3, cursor="arrow", state=tk.DISABLED)
    btn.grid(row=1, column=2, padx=5, pady=5, sticky="e")
    return btn

def create_image_button():
    """Cria o botão de envio de imagem."""
    btn = tk.Button(janela, text="+", command=selecionar_imagem, font=("Inter", 14, "bold"),
                    bg="#FF6CC2", fg="white", activebackground="#a0456f", relief=tk.RAISED, bd=3, cursor="hand2",
                    width=2, height=1)
    btn.grid(row=1, column=0, padx=5, pady=5, sticky="w")
    return btn

def send_message():
    global selected_image_pil
    user_message = entry_message.get()
    
    # Captura o valor atual de selected_image_pil para a lambda
    current_image_pil_for_lambda = selected_image_pil 

    # Se não há mensagem de texto e nem imagem, não faz nada
    if not user_message.strip() and current_image_pil_for_lambda is None:
        print("DEBUG: Nenhuma mensagem de texto ou imagem selecionada para enviar.")
        return

    chat_display.config(state=tk.NORMAL)
    if user_message.strip():
        chat_display.insert(tk.END, user_message + "\n\n", "user_content_tag")
    chat_display.config(state=tk.DISABLED)
    chat_display.see(tk.END)

    chat_display.config(state=tk.NORMAL)
    chat_display.insert(tk.END, "Nyx está pensando...\n\n", "nyx_thinking_tag") 
    chat_display.config(state=tk.DISABLED)
    chat_display.see(tk.END)
    
    entry_message.delete(0, tk.END)
    
    global button_send, dummy_button, button_image
    if 'button_send' in globals() and button_send.winfo_exists():
        button_send.destroy()
    if 'button_image' in globals() and button_image.winfo_exists():
        button_image.destroy() # Destrói o botão de imagem também
    dummy_button = create_dummy_button()

    print(f"DEBUG: Chamando process_ai_response com mensagem: '{user_message}' e imagem (presente: {current_image_pil_for_lambda is not None}).")
    # Passa o objeto PIL Image para process_ai_response
    janela.after(100, lambda: process_ai_response(user_message, current_image_pil_for_lambda))

def load_initial_history():
    initial_history = get_last_messages(num_messages=100)
    chat_display.config(state=tk.NORMAL)
    
    for msg in initial_history:
        if msg['role'] == 'user':
            for part in msg['parts']:
                if isinstance(part, dict) and 'text' in part:
                    chat_display.insert(tk.END, f"{part['text']}\n\n", "user_content_tag")
                elif isinstance(part, dict) and 'inline_data' in part:
                    try:
                        img_data_base64 = part['inline_data']['data']
                        img_data_bytes = base64.b64decode(img_data_base64) # Decodifica de base64
                        
                        img = Image.open(io.BytesIO(img_data_bytes))
                        img.thumbnail((150, 150), Image.Resampling.LANCZOS) # Redimensiona para histórico
                        img_tk = ImageTk.PhotoImage(img)
                        chat_display.image_references.append(img_tk) 
                        chat_display.insert(tk.END, "Você enviou uma imagem:\n", "user_content_tag")
                        chat_display.image_create(tk.END, image=img_tk)
                        chat_display.insert(tk.END, "\n\n")
                    except Exception as e:
                        print(f"ERRO: Erro ao carregar imagem do histórico: {e}")
                        chat_display.insert(tk.END, "[Erro ao carregar imagem]\n\n", "user_content_tag")
        else:
            chat_display.insert(tk.END, "Nyx:\n", "nyx_tag")
            
            response_text = msg['parts'][0]['text'] if msg['parts'] and 'text' in msg['parts'][0] else ""
            parts = re.split(r'(\*\*.*?\*\*)', response_text)
            for part in parts:
                if part.startswith('**') and part.endswith('**'):
                    text_to_bold = part[2:-2]
                    chat_display.insert(tk.END, text_to_bold, "nyx_content_bold_tag")
                else:
                    chat_display.insert(tk.END, part, "nyx_content_tag")
            chat_display.insert(tk.END, "\n\n")

    chat_display.config(state=tk.DISABLED)
    chat_display.see(tk.END)

# --- Configuração da Janela Principal ---
janela = tk.Tk()
janela.title("Chat IA - Nyx")
janela.geometry("500x600")
janela.configure(bg="#242424")


# --- Widgets da Interface ---
chat_display = tk.Text(janela, wrap=tk.WORD, state=tk.DISABLED, width=70, height=25, font=("Inter", 10),
                        bg="#242424", fg="#CFCFCF", insertbackground="#CFCFCF")
chat_display.grid(row=0, column=0, columnspan=3, padx=10, pady=10, sticky="nsew") # Aumenta columnspan
chat_display.image_references = [] # Lista para manter referências de imagens

chat_display.tag_config("nyx_tag", font=("Inter", 12, "bold"), foreground="#FF6CC2")
chat_display.tag_config("nyx_thinking_tag", font=("Inter", 10, "italic"), foreground="#FF6CC2") 
chat_display.tag_config("user_content_tag",
                            lmargin1=100, lmargin2=100, rmargin=20,
                            background="#1F1F1F",
                            foreground="#CFCFCF",
                            wrap="word", justify='right')
chat_display.tag_config("nyx_content_tag",
                            lmargin1=20, lmargin2=20, rmargin=100,
                            background="#242424", foreground="#CFCFCF",
                            wrap="word", justify='left')
chat_display.tag_config("nyx_content_bold_tag",
                            lmargin1=20, lmargin2=20, rmargin=100,
                            background="#242424", foreground="#CFCFCF",
                            wrap="word", justify='left', font=("Inter", 10, "bold"))


button_send = None
dummy_button = None
button_image = None 

button_send = create_send_button()
button_image = create_image_button() 

entry_message = tk.Entry(janela, width=60, font=("Inter", 10),
                            bg="#242424", fg="#CFCFCF", insertbackground="#FF6CC2")
entry_message.grid(row=1, column=1, padx=10, pady=5, sticky="ew") 
entry_message.bind("<Return>", lambda event=None: send_message())


janela.grid_rowconfigure(0, weight=1)
janela.grid_columnconfigure(0, weight=0) 
janela.grid_columnconfigure(1, weight=1) 
janela.grid_columnconfigure(2, weight=0) 

# --- Inicialização e Loop Principal ---
if __name__ == "__main__":
    init_db()
    load_initial_history()
    janela.mainloop()
