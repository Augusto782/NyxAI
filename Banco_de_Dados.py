import sqlite3
import base64
from PIL import Image
import io

# Esta classe encapsula toda a lógica de interação com o banco de dados SQLite.
class banco_de_dados:
    """
    Gerencia as operações de banco de dados para o histórico de chat.
    Utiliza SQLite e armazena mensagens, imagens e o tipo MIME em um arquivo local.
    """
    def __init__(self, db_name='historico_chat.db'):
        """
        Inicializa o gerenciador de banco de dados e garante que a tabela
        'messages' com as colunas necessárias exista.
        """
        self.db_name = db_name
        self.init_db()

    def _get_connection(self):
        """
        Função auxiliar para obter uma nova conexão com o banco de dados.
        Retorna a conexão para uso com o 'with' (context manager).
        """
        return sqlite3.connect(self.db_name)

    def _check_and_add_column(self, conn, cursor, column_name, column_type):
        """Função auxiliar para verificar e adicionar uma coluna se ela não existir."""
        cursor.execute("PRAGMA table_info(messages)")
        columns = [column[1] for column in cursor.fetchall()]
        if column_name not in columns:
            cursor.execute(f"ALTER TABLE messages ADD COLUMN {column_name} {column_type}")
            conn.commit()
            print(f"Coluna '{column_name}' adicionada à tabela 'messages'.")

    def init_db(self):
        """
        Cria a tabela de mensagens se ela ainda não existir e garante que todas
        as colunas necessárias ('image_data' e 'image_mime_type') estejam presentes.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Cria a tabela de mensagens com as colunas essenciais
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        image_data BLOB NULL,
                        image_mime_type TEXT NULL
                    )
                ''')
                conn.commit()

                # Garante que colunas adicionais para a imagem estejam presentes
                self._check_and_add_column(conn, cursor, 'image_data', 'BLOB NULL')
                self._check_and_add_column(conn, cursor, 'image_mime_type', 'TEXT NULL')
            
            print(f"Banco de dados '{self.db_name}' inicializado com sucesso.")
        except sqlite3.Error as e:
            print(f"ERRO durante a inicialização do BD: {e}")

    def save_message(self, role, content, image_data=None, image_mime_type=None):
        """
        Salva uma nova mensagem no banco de dados.
        CORREÇÃO: Esta função AGORA DEVE SER CHAMADA com o 'content' como string, 
        e 'image_data' como bytes ou None.
        :param role: 'user' ou 'model'
        :param content: O conteúdo da mensagem (texto)
        :param image_data: Dados de imagem em bytes (opcional)
        :param image_mime_type: O tipo MIME da imagem (ex: 'image/png') (opcional)
        """
        if role == 'user' and not content and not image_data:
             print("AVISO: Tentativa de salvar mensagem de usuário sem texto e sem imagem. Ignorado.")
             return
        if role == 'model' and not content:
             print("AVISO: Tentativa de salvar resposta do modelo sem texto. Ignorado.")
             return
             
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO messages (role, content, image_data, image_mime_type) VALUES (?, ?, ?, ?)", 
                    (role, content, image_data, image_mime_type)
                )
                conn.commit()
        except sqlite3.Error as e:
            print(f"ERRO: Não foi possível salvar a mensagem. Detalhes: {e}")

    def get_last_messages(self, num_messages=100):
        """
        Recupera as últimas N mensagens do banco de dados para formar o histórico de chat.
        Formata os dados no formato de 'parts' esperado pelo modelo Gemini.
        :param num_messages: O número de mensagens a serem recuperadas.
        :return: Uma lista de dicionários formatada para o modelo Gemini.
        """
        history = []
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT role, content, image_data, image_mime_type FROM messages ORDER BY id DESC LIMIT ?", 
                    (num_messages,)
                )
                rows = cursor.fetchall()

                # As mensagens são recuperadas em ordem decrescente de ID, então invertemos
                # a lista para que fiquem em ordem cronológica para o modelo.
                for role, content, image_data, mime_type in reversed(rows):
                    parts = []
                    # 1. Adiciona a parte de texto
                    if content:
                        parts.append({'text': content})
                    
                    # 2. Adiciona a parte de imagem (codificada em base64)
                    if image_data and mime_type:
                        encoded_image_data = base64.b64encode(image_data).decode('utf-8') 
                        parts.append({'inline_data': {'mime_type': mime_type, 'data': encoded_image_data}}) 
                    
                    if parts: # Adiciona apenas se houver conteúdo (texto ou imagem)
                        # O ChatEngine precisa da lista de 'parts'
                        history.append({'role': role, 'parts': parts})

        except sqlite3.Error as e:
            print(f"ERRO: Não foi possível recuperar o histórico para o motor de IA. Detalhes: {e}")
            
        return history

    def get_all_messages(self):
        """
        Recupera TODAS as mensagens do banco de dados para exibição na GUI.
        Retorna os dados em um formato simples (texto + bytes de imagem) para o Tkinter.
        :return: Uma lista de dicionários com 'role', 'text' e 'image_data' (bytes).
        """
        history = []
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Seleciona as colunas necessárias, ordenadas cronologicamente
                cursor.execute(
                    "SELECT role, content, image_data FROM messages ORDER BY id ASC"
                )
                rows = cursor.fetchall()
                
                for role, content, image_data in rows:
                    history.append({
                        'role': role,
                        'text': content,
                        # Retorna a imagem como bytes para ser exibida na GUI
                        'image_data': image_data 
                    })

        except sqlite3.Error as e:
            print(f"ERRO: Não foi possível recuperar todo o histórico para a GUI. Detalhes: {e}")
            
        return history

    def clear_history(self):
        """
        Deleta todas as mensagens da tabela, limpando o histórico do chat.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM messages")
                conn.commit()
                print(f"Histórico do banco de dados '{self.db_name}' limpo.")
        except sqlite3.Error as e:
            print(f"ERRO: Não foi possível limpar o histórico. Detalhes: {e}")