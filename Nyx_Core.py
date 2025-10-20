import google.generativeai as genai
import os
from dotenv import load_dotenv
from PIL import Image
import io
import base64

# --- Importa as Definições e a Lógica de Execução das Ferramentas ---
from Gerenciador_de_Ferramentas import GEMINI_TOOLS, execute_tool
# -------------------------------------------------------------------

# Assume-se que 'Banco_de_Dados' é um módulo local
from Banco_de_Dados import banco_de_dados

# O Banco de Dados é inicializado globalmente e reusado pela classe
db_manager = banco_de_dados()

# --- Motor Principal da Nyx ---

class ChatEngine:
    MODEL_NAME = 'gemini-2.5-flash'
    MAX_TOOL_CALLS = 5
    # Define o limite de mensagens para o contexto da IA
    AI_CONTEXT_LIMIT = 100

    def __init__(self):
        load_dotenv()
        self.db_manager = db_manager 
        self._configure_api()
        self.system_instruction = os.getenv('PROMPT_IA') or "Você é um assistente prestativo e amigável. Responda a todas as perguntas de forma clara e concisa."
        
        # O modelo é inicializado com as ferramentas importadas do tools_handler
        self.model = genai.GenerativeModel(
            self.MODEL_NAME, 
            system_instruction=self.system_instruction,
            tools=GEMINI_TOOLS # Usa a lista importada
        )
        self.chat_session = self._initialize_chat_session()
        print(f"DEBUG: ChatEngine inicializado e pronto. Histórico carregado: {len(self.chat_session.history)} mensagens.")


    def _configure_api(self):
        """Configura a chave da API do Google."""
        try:
            # Verifica se a chave existe antes de configurar
            if not os.getenv('GOOGLE_API_KEY'):
                raise ValueError("GOOGLE_API_KEY não definida.")
                
            genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
            print(f"DEBUG: API configurada para o modelo: {self.MODEL_NAME}.")
        except Exception as e:
            print(f"ERRO: Falha ao configurar a API. Erro: {e}")

    def _pil_to_bytes_and_mime(self, image_pil: Image.Image):
        """
        Converte um objeto PIL Image para bytes e retorna o tipo MIME.
        Prioriza JPEG para eficiência e compatibilidade.
        """
        if not image_pil:
            return None, None
        
        # Garante que a imagem está em RGB, se necessário, para salvar em JPEG
        if image_pil.mode == 'RGBA':
            image_pil = image_pil.convert('RGB')
            
        img_byte_arr = io.BytesIO()
        try:
            image_pil.save(img_byte_arr, format='JPEG')
            return img_byte_arr.getvalue(), 'image/jpeg'
        except Exception as e:
            print(f"AVISO: Falha ao salvar imagem como JPEG, tentando PNG. Erro: {e}")
            img_byte_arr = io.BytesIO()
            # Tenta salvar como PNG como fallback
            try:
                image_pil.save(img_byte_arr, format='PNG')
                return img_byte_arr.getvalue(), 'image/png'
            except Exception as inner_e:
                print(f"ERRO: Falha ao salvar imagem como PNG. Erro: {inner_e}")
                return None, None

    def _initialize_chat_session(self):
        """
        Carrega o histórico formatado do banco de dados 
        e inicializa um novo genai.ChatSession.
        """
        print("DEBUG: Carregando o histórico do banco de dados para a sessão de chat...")
        
        # 1. Carregar histórico no formato de dicionários do DB
        history_from_db = self.db_manager.get_last_messages(num_messages=self.AI_CONTEXT_LIMIT)
        
        # 2. Formatar histórico para o genai.ChatSession
        formatted_history = []
        for msg in history_from_db:
            parts_data = msg.get('parts')
            
            parts_for_model = []
            for part_data in parts_data:
                
                # Caso seja uma parte de imagem (inline_data)
                if 'inline_data' in part_data and 'data' in part_data['inline_data']:
                    try:
                        # O 'data' no BD está como string base64, precisamos decodificar para bytes.
                        image_bytes = base64.b64decode(part_data['inline_data']['data'])
                        
                        # Usando a sintaxe direta de dicionário para inline_data, que o SDK aceita
                        parts_for_model.append(genai.protos.Part(
                            inline_data={
                                'mime_type': part_data['inline_data']['mime_type'],
                                'data': image_bytes
                            }
                        ))
                    except Exception as e:
                        print(f"AVISO: Falha ao decodificar imagem do histórico: {e}")
                        # Se falhar, pula esta parte
                        continue 
                        
                # Caso seja uma parte de texto
                elif 'text' in part_data:
                    parts_for_model.append(genai.protos.Part(text=part_data['text']))
                
                # Trata FunctionCall
                elif 'function_call' in part_data:
                    fc_data = part_data['function_call']
                    parts_for_model.append(genai.protos.Part(
                        function_call=genai.protos.FunctionCall(
                            name=fc_data['name'], 
                            args=fc_data['args']
                        )
                    ))
                
                # Trata FunctionResponse
                elif 'function_response' in part_data:
                    fr_data = part_data['function_response']
                    parts_for_model.append(genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=fr_data['name'], 
                            response=fr_data['response']
                        )
                    ))


            if parts_for_model:
                # Cria o objeto Content para a mensagem, com as partes formatadas
                formatted_history.append(genai.protos.Content(role=msg['role'], parts=parts_for_model))
        
        # 3. Criar a sessão de chat com o histórico carregado
        chat = self.model.start_chat(history=formatted_history)
        return chat

    def get_paginated_history(self, offset: int, limit: int):
        """
        Retorna um pedaço (página) do histórico para a GUI (texto + bytes).
        """
        print(f"DEBUG: Buscando histórico paginado: offset={offset}, limit={limit}")
        try:
            # Chama o método no gerenciador de BD 
            return self.db_manager.get_paginated_messages(offset=offset, limit=limit)
        except AttributeError:
            print("ERRO: 'get_paginated_messages' não está implementado. Retornando todo o histórico como fallback.")
            return self.db_manager.get_all_messages() 
            

    def get_history(self):
        """
        Retorna todo o histórico de mensagens no formato amigável para a GUI (texto + bytes).
        """
        return self.db_manager.get_all_messages() 

    def send_message(self, text: str, image_pil: Image.Image = None) -> str:
        """
        Envia a mensagem (e imagem opcional) para a IA usando a sessão de chat,
        gerenciando chamadas de função e persistência, delegando a execução das
        ferramentas para tools_handler.py.
        """
        if not os.getenv('GOOGLE_API_KEY'):
            return "ERRO: Chave GOOGLE_API_KEY não configurada no ambiente."

        pergunta = text.strip()
        if not pergunta and image_pil is None:
            return "Mensagem vazia ou sem imagem."

        # 1. Prepara dados para o banco de dados e para a API
        image_bytes, mime_type = self._pil_to_bytes_and_mime(image_pil)
        
        # Conteúdo a ser enviado pelo usuário para a API (lista de objetos PIL e/ou string):
        content_parts_initial = []
        if image_pil:
            content_parts_initial.append(image_pil)
        if pergunta:
            content_parts_initial.append(pergunta)

        if not content_parts_initial:
            return "ERRO: Conteúdo para envio vazio."

        try:
            # 2. Salva a mensagem do usuário no DB ANTES de enviar.
            self.db_manager.save_message("user", pergunta, image_bytes, mime_type) 
            
            # 3. Envia a requisição inicial para a sessão de chat
            current_response = self.chat_session.send_message(
                content=content_parts_initial, 
                tools=GEMINI_TOOLS # Usa a lista importada
            )

            # Loop para processar chamadas de ferramenta
            tool_call_count = 0
            final_response_text = ""

            while tool_call_count < self.MAX_TOOL_CALLS:
                
                tool_call = None
                
                # Extrai a chamada de função, se existir
                if (current_response.candidates and 
                    current_response.candidates[0].content.parts and
                    # Verifica se o primeiro 'part' tem o atributo 'function_call'
                    hasattr(current_response.candidates[0].content.parts[0], 'function_call') and 
                    current_response.candidates[0].content.parts[0].function_call):
                    
                    tool_call = current_response.candidates[0].content.parts[0].function_call
                    
                if tool_call:
                    tool_name = tool_call.name
                    # Converte os argumentos para um dicionário Python
                    tool_args = dict(tool_call.args.items()) if tool_call.args else {} 
                    
                    print(f"\n--- DEBUG: Modelo solicitou chamada de função: {tool_name} ---")
                    print(f"--- DEBUG: Argumentos: {tool_args} ---\n")
                    
                    # --------------------------------------------------------
                    # --- EXECUÇÃO DELEGADA PARA O tools_handler.py ---
                    tool_output = execute_tool(tool_name, tool_args)
                    # --------------------------------------------------------

                    # 4. Envia o resultado da ferramenta de volta para o modelo
                    function_response_part = genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=tool_name,
                            response={'result': tool_output}
                        )
                    )
                    
                    # Envia a resposta da ferramenta para o modelo para que ele gere a resposta de texto
                    current_response = self.chat_session.send_message(
                        content=[function_response_part] 
                    )
                    
                    tool_call_count += 1
                else:
                    # O modelo não solicitou mais chamadas de função, resposta final
                    
                    if (current_response.candidates and 
                        current_response.candidates[0].content.parts and 
                        current_response.candidates[0].content.parts[0].text):
                        
                        final_response_text = current_response.candidates[0].content.parts[0].text
                    else:
                        final_response_text = "Desculpe, a IA não conseguiu gerar uma resposta de texto válida."
                    break

            if not final_response_text:
                return "Desculpe, não foi possível gerar uma resposta clara após várias chamadas de ferramentas."
            
            # 5. Salva a resposta final do modelo (apenas texto) no DB
            self.db_manager.save_message("model", final_response_text)
            
            return final_response_text

        except Exception as e:
            print(f"ERRO: A requisição de geração falhou. Erro: {e}")
            return f"Desculpe, ocorreu um erro ao gerar a resposta. Detalhes técnicos: {e}"

if __name__ == '__main__':
    try:
        engine = ChatEngine()
    except Exception as e:
        print(f"ERRO ao inicializar ChatEngine: {e}")

    print("Módulo ChatEngine carregado.")
