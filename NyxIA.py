import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog
from PIL import Image, ImageTk, ImageEnhance
import threading
import io

# Importa a classe do motor de chat que contém toda a lógica de API e ferramentas.
try:
    # Renomeando o import para evitar conflito de nomenclatura, embora nyx_teste seja o nome
    from Nyx_Core import ChatEngine 
except ImportError:
    messagebox.showerror("Erro de Importação", "O arquivo 'nyx_core.py' (Motor de Chat) não foi encontrado. Certifique-se de que está no mesmo diretório.")
    exit()

class ChatApplication(tk.Tk):
    """
    Interface gráfica (GUI) para interagir com o ChatEngine.
    Usa Tkinter para a interface e threading para chamadas assíncronas ao motor.
    """
    def __init__(self):
        super().__init__()
        self.title("Assistente Gemini (Chat Engine)")
        self.geometry("800x600")
        self.configure(bg="#f0f2f5")

        # Configuração do motor de chat (pode levar um tempo para inicializar)
        self.engine = None
        self.selected_image = None
        self.history_area = None
        
        # --- Elementos da Interface ---
        self._setup_ui()
        
        # Inicialização do motor em uma thread para não travar a GUI
        threading.Thread(target=self._initialize_engine, daemon=True).start()

    def _setup_ui(self):
        """Configura todos os widgets da interface."""
        
        # 1. Área de Histórico (ScrolledText)
        self.history_area = scrolledtext.ScrolledText(
            self, 
            state='disabled', 
            wrap='word', 
            font=('Inter', 10),
            bg="#ffffff",
            fg="#333333",
            padx=10,
            pady=10
        )
        self.history_area.pack(padx=15, pady=(15, 5), fill="both", expand=True)

        # CORREÇÃO CRÍTICA: Inicializa a lista de referências de imagem. 
        # Isso previne que o garbage collector do Tkinter apague as imagens do histórico.
        if not hasattr(self.history_area, 'image_refs'):
            self.history_area.image_refs = []

        # Configura as tags de estilo
        self.history_area.tag_config('user', foreground='#007BFF', font=('Inter', 10, 'bold'), lmargin1=20, lmargin2=20)
        self.history_area.tag_config('model', foreground='#495057', font=('Inter', 10), lmargin1=20, lmargin2=20)
        self.history_area.tag_config('system', foreground='#FF5733', font=('Inter', 10, 'italic'), justify='center')
        
        # 2. Frame de Entrada (Input Frame)
        input_frame = tk.Frame(self, bg="#f0f2f5")
        input_frame.pack(padx=15, pady=(0, 15), fill="x")

        # 3. Campo de Entrada de Texto
        self.input_entry = tk.Entry(
            input_frame, 
            font=('Inter', 11), 
            bd=1, 
            relief=tk.FLAT,
            bg="#ffffff",
            fg="#333333"
        )
        self.input_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 5))
        self.input_entry.bind("<Return>", lambda event: self._send_message_button_click())

        # 4. Botão de Anexo de Imagem
        self.image_button = tk.Button(
            input_frame,
            text="🖼️ Imagem",
            command=self._select_image,
            font=('Inter', 9, 'bold'),
            bg="#f0f0f0",
            fg="#333333",
            activebackground="#e0e0e0",
            relief=tk.GROOVE,
            padx=10,
            pady=5
        )
        self.image_button.pack(side="left", padx=5)

        # 5. Botão de Envio
        self.send_button = tk.Button(
            input_frame,
            text="Enviar",
            command=self._send_message_button_click,
            font=('Inter', 10, 'bold'),
            bg="#007BFF",
            fg="#FFFFFF",
            activebackground="#0056b3",
            relief=tk.FLAT,
            padx=15,
            pady=5,
            state=tk.DISABLED # Desabilitado até o motor inicializar
        )
        self.send_button.pack(side="right")
        
        # 6. Rótulo do Nome da Imagem Selecionada
        self.image_label = tk.Label(input_frame, text="", bg="#f0f2f5", fg="#FF5733", font=('Inter', 8))
        self.image_label.pack(side="top", fill="x", padx=5)

    def _initialize_engine(self):
        """Inicializa o ChatEngine na thread secundária."""
        self._display_system_message("Inicializando motor de IA e carregando histórico...")
        try:
            self.engine = ChatEngine()
            
            # Garante que as chamadas de GUI sejam feitas na thread principal
            self.after(0, self._on_engine_ready)
            
        except Exception as e:
            error_msg = f"Falha ao inicializar o ChatEngine. Verifique variáveis de ambiente e imports. Erro: {e}"
            self._display_system_message(f"ERRO DE INICIALIZAÇÃO: {error_msg}")
            self.after(0, lambda: messagebox.showerror("Erro Crítico", error_msg))

    def _on_engine_ready(self):
        """Chamado na thread principal após a inicialização do motor."""
        self.send_button.config(state=tk.NORMAL)
        self._display_system_message("Motor de IA pronto. Digite sua mensagem!")
        self._load_history()

    def _load_history(self):
        """Carrega e exibe o histórico de mensagens do banco de dados."""
        if not self.engine:
            return

        try:
            history = self.engine.get_history()
            
            if history:
                self._display_system_message(f"Carregando {len(history)} mensagens anteriores.")
                
                for msg in history:
                    role = msg.get('role', 'system')
                    text = msg.get('text', '')
                    # O banco de dados retorna a imagem como bytes (image_data).
                    image_bytes = msg.get('image_data') 

                    if text or image_bytes:
                        self._display_message(role, text, image_bytes)
                
                self._display_system_message("Histórico carregado.")

        except Exception as e:
            self._display_system_message(f"ERRO: Não foi possível carregar o histórico: {e}")

    def _select_image(self):
        """Abre a caixa de diálogo para selecionar uma imagem."""
        file_path = filedialog.askopenfilename(
            title="Selecione uma Imagem",
            filetypes=[("Arquivos de Imagem", "*.jpg *.jpeg *.png")]
        )
        if file_path:
            try:
                self.selected_image = Image.open(file_path).convert("RGB")
                
                file_name = file_path.split('/')[-1]
                self.image_label.config(text=f"Imagem: {file_name} (Anexada)")
                
                self._display_system_message(f"IMAGEM SELECIONADA: {file_name}")

            except Exception as e:
                self.selected_image = None
                self.image_label.config(text="")
                messagebox.showerror("Erro de Imagem", f"Não foi possível carregar a imagem: {e}")

    def _display_message(self, role, text, image_bytes=None):
        """Adiciona uma mensagem ao histórico na thread principal."""
        self.history_area.config(state='normal')
        
        sender = "Você" if role == 'user' else "Gemini"
        tag = role

        # Insere um separador e o remetente
        self.history_area.insert(tk.END, f"\n{sender}:\n", tag)
        
        # 2. Imagem (se houver)
        if image_bytes:
            try:
                # Converte os bytes de volta para Image
                image_stream = io.BytesIO(image_bytes)
                img = Image.open(image_stream)
                
                # Redimensiona para exibição (max 250px de largura)
                width, height = img.size
                MAX_WIDTH = 250
                if width > MAX_WIDTH:
                    ratio = MAX_WIDTH / width
                    img = img.resize((MAX_WIDTH, int(height * ratio)), Image.LANCZOS)
                
                # Converte para formato Tkinter
                tk_img = ImageTk.PhotoImage(img)

                # Mantém a referência na lista inicializada no _setup_ui
                self.history_area.image_refs.append(tk_img)

                # Insere a imagem
                self.history_area.insert(tk.END, " ")
                self.history_area.image_create(tk.END, image=tk_img)
                self.history_area.insert(tk.END, "\n")
            except Exception as e:
                # Mostra o erro de imagem no histórico, mas não quebra a aplicação
                self.history_area.insert(tk.END, f"[ERRO: Falha ao carregar imagem: {e}]\n")
                print(f"ERRO DE EXIBIÇÃO DE IMAGEM: {e}")
                
        # 3. Texto
        self.history_area.insert(tk.END, f"{text}\n\n", tag)
        
        self.history_area.config(state='disabled')
        self.history_area.see(tk.END) # Rola para o final

    def _display_system_message(self, text):
        """Exibe mensagens do sistema (logs, status) no histórico."""
        # Garante que a área de histórico está inicializada
        if self.history_area:
            self.history_area.config(state='normal')
            self.history_area.insert(tk.END, f"\n[SISTEMA] {text}\n", 'system')
            self.history_area.config(state='disabled')
            self.history_area.see(tk.END)

    def _send_message_button_click(self):
        """Gerencia o clique do botão de envio."""
        user_text = self.input_entry.get().strip()
        
        if not user_text and not self.selected_image:
            return

        # Desabilita o envio e mostra o estado de carregamento
        self.send_button.config(state=tk.DISABLED, text="Aguarde...")
        self.input_entry.config(state=tk.DISABLED)
        self.image_button.config(state=tk.DISABLED)
        
        # AQUI: A exibição do lado do usuário é feita APÓS o thread. O motor salva.
        # Vamos manter o thread para processar a mensagem.
        threading.Thread(
            target=self._process_message, 
            args=(user_text, self.selected_image), 
            daemon=True
        ).start()

    def _process_message(self, text, image_pil):
        """Chama a lógica principal do motor (executado em thread secundária)."""
        try:
            # Exibir a mensagem do usuário (incluindo imagem) imediatamente no UI thread
            # O motor salva a mensagem no DB, mas precisamos exibir no UI
            image_bytes_for_display = self._pil_to_bytes(image_pil)
            self.after(0, lambda: self._display_message("user", text, image_bytes_for_display))
            
            # Chama o método central do motor de chat (onde a chamada API ocorre)
            model_response = self.engine.send_message(text, image_pil)
            
            # Chama a exibição da resposta do modelo na thread principal (GUI)
            self.after(0, lambda: self._display_message("model", model_response))

        except Exception as e:
            error_msg = f"ERRO ao comunicar com o motor de chat: {e}"
            self.after(0, lambda: self._display_system_message(error_msg))
            print(error_msg)

        finally:
            # Reseta o estado da GUI na thread principal
            self.after(0, self._reset_ui_state)

    def _reset_ui_state(self):
        """Reseta o campo de entrada e botões após o envio (na thread principal)."""
        self.input_entry.delete(0, tk.END)
        self.send_button.config(state=tk.NORMAL, text="Enviar")
        self.input_entry.config(state=tk.NORMAL)
        self.image_button.config(state=tk.NORMAL)
        
        # Limpa o estado da imagem
        self.selected_image = None
        self.image_label.config(text="")

    def _pil_to_bytes(self, image_pil):
        """Converte um objeto PIL Image para bytes JPEG (para exibição de referência)."""
        if not image_pil:
            return None
        img_byte_arr = io.BytesIO()
        # Garante que a imagem é salva como JPEG para ser exibida e armazenada
        image_pil.save(img_byte_arr, format='JPEG') 
        return img_byte_arr.getvalue()


if __name__ == '__main__':
    # Verifica a dependência da PIL antes de iniciar
    if 'Image' not in globals():
         messagebox.showerror("Erro de Dependência", "A biblioteca 'Pillow' (PIL) deve ser instalada para rodar a aplicação.")
         exit()

    app = ChatApplication()
    app.mainloop()