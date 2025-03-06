import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.font import Font
import PyPDF2
import fitz  # PyMuPDF
from PIL import Image, ImageTk
import io
import threading
import time

class PDFSplitterApp:
    """Aplicativo para dividir arquivos PDF em múltiplos documentos."""
    
    def __init__(self, root):
        """Inicializa a aplicação com a interface gráfica."""
        self.root = root
        self.setup_window()
        self.setup_variables()
        self.create_widgets()
        self.setup_layout()
        self.bind_events()
        
    def setup_window(self):
        """Configura a janela principal."""
        self.root.title("PDF Splitter Pro")
        self.root.geometry("900x600")
        self.root.minsize(800, 500)
        
        # Defina o estilo
        self.style = ttk.Style()
        self.style.theme_use('clam')  # Tema mais moderno
        
        # Configure cores e estilos
        self.bg_color = "#f5f5f5"
        self.highlight_color = "#4a86e8"
        # Cor para thumbnail selecionada
        self.selected_color = "#2e5a8a"
        self.accent_color = "#e63946"
        
        self.root.configure(bg=self.bg_color)
        
        self.style.configure('TFrame', background=self.bg_color)
        self.style.configure('TButton', font=('Segoe UI', 10))
        self.style.configure('TLabel', background=self.bg_color, font=('Segoe UI', 10))
        self.style.configure('Header.TLabel', font=('Segoe UI', 14, 'bold'))
        self.style.configure('Status.TLabel', background='#e8e8e8', padding=5)
        
    def setup_variables(self):
        """Inicializa as variáveis da aplicação."""
        self.pdf_path = ""
        self.pdf_reader = None
        self.page_images = []
        self.ranges = []  # Lista de faixas definidas (tuplas: (página_inicial, página_final))
        self.current_range_start = None  # Armazena o primeiro clique para formar a faixa
        self.last_clicked_page = None  # Armazena o índice do último PDF clicado
        self.thumbnails = []
        # self.labels armazenará os widgets (labels) de cada thumbnail; se um thumbnail for removido, o valor ficará como None
        self.labels = []
        self.status_var = tk.StringVar()
        self.status_var.set("Pronto para começar. Selecione um arquivo PDF.")
        self.output_dir = os.path.dirname(os.path.abspath(__file__))
        self.columns = 3  # Número de colunas na grade de exibição
        
    def create_widgets(self):
        """Cria todos os widgets da interface."""
        # Frame principal - divisão em duas partes
        self.main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        
        # Frame para exibição das páginas
        self.display_frame = ttk.Frame(self.main_paned)
        
        # Frame de controle (lado direito)
        self.control_frame = ttk.Frame(self.main_paned)
        
        # Barra de ferramentas superior
        self.toolbar = ttk.Frame(self.root)
        
        # Status bar
        self.status_bar = ttk.Label(
            self.root, 
            textvariable=self.status_var, 
            relief=tk.SUNKEN, 
            anchor=tk.W,
            style='Status.TLabel'
        )
        
        # Conteúdo da toolbar
        self.title_label = ttk.Label(
            self.toolbar, 
            text="PDF Splitter Pro", 
            style="Header.TLabel"
        )
        
        self.btn_select_pdf = ttk.Button(
            self.toolbar, 
            text="Selecionar PDF", 
            command=self.select_pdf
        )
        
        self.btn_output_dir = ttk.Button(
            self.toolbar, 
            text="Pasta de Saída", 
            command=self.select_output_dir
        )
        
        # Conteúdo do frame de controle
        self.control_header = ttk.Label(
            self.control_frame, 
            text="Faixas de Páginas", 
            style="Header.TLabel"
        )
        
        self.ranges_frame = ttk.LabelFrame(
            self.control_frame, 
            text="Faixas Selecionadas"
        )
        
        self.listbox_ranges = tk.Listbox(
            self.ranges_frame, 
            width=20, 
            height=15,
            borderwidth=1,
            font=('Segoe UI', 10),
            selectbackground=self.highlight_color
        )
        
        self.ranges_scrollbar = ttk.Scrollbar(
            self.ranges_frame, 
            orient="vertical", 
            command=self.listbox_ranges.yview
        )
        
        self.listbox_ranges.configure(yscrollcommand=self.ranges_scrollbar.set)
        
        self.actions_frame = ttk.Frame(self.control_frame)
        
        self.btn_remove_range = ttk.Button(
            self.actions_frame, 
            text="Remover Faixa", 
            command=self.remove_range
        )
        
        self.btn_clear_ranges = ttk.Button(
            self.actions_frame, 
            text="Limpar Tudo", 
            command=self.clear_ranges
        )
        
        self.btn_generate = ttk.Button(
            self.control_frame, 
            text="Gerar PDFs",
            command=self.generate_pdfs_with_progress
        )
        
        # Frame para exibição das páginas
        self.pages_container = ttk.Frame(self.display_frame)
        
        self.canvas = tk.Canvas(
            self.pages_container, 
            bg=self.bg_color,
            highlightthickness=0
        )
        
        self.scrollbar = ttk.Scrollbar(
            self.pages_container, 
            orient="vertical", 
            command=self.canvas.yview
        )
        
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        # Progress bar (inicialmente oculta)
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(
            self.root, 
            orient="horizontal", 
            length=100, 
            mode="determinate",
            variable=self.progress_var
        )
        
        # Adiciona controles de navegação
        self.navigation_frame = ttk.Frame(self.display_frame)
        self.btn_prev = ttk.Button(self.navigation_frame, text="←", command=self.prev_page)
        self.btn_next = ttk.Button(self.navigation_frame, text="→", command=self.next_page)
        self.page_nav_var = tk.StringVar(value="Página 1 de 1")
        self.lbl_page_nav = ttk.Label(self.navigation_frame, textvariable=self.page_nav_var)
        
    def setup_layout(self):
        """Organiza os widgets na interface."""
        # Toolbar e status bar
        self.toolbar.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
        self.title_label.pack(side=tk.LEFT, padx=10)
        self.btn_select_pdf.pack(side=tk.LEFT, padx=5)
        self.btn_output_dir.pack(side=tk.LEFT, padx=5)
        
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.main_paned.add(self.display_frame, weight=3)
        self.main_paned.add(self.control_frame, weight=1)
        
        self.control_header.pack(pady=(0, 10), anchor="w")
        self.ranges_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        self.listbox_ranges.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.ranges_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.actions_frame.pack(fill=tk.X, pady=10)
        self.btn_remove_range.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.btn_clear_ranges.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.btn_generate.pack(fill=tk.X, pady=20, padx=5)
        
        self.pages_container.pack(fill=tk.BOTH, expand=True)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Adiciona a navegação na parte superior do display_frame
        self.navigation_frame.pack(side=tk.TOP, fill=tk.X, pady=5)
        self.btn_prev.pack(side=tk.LEFT, padx=5)
        self.lbl_page_nav.pack(side=tk.LEFT, padx=5)
        self.btn_next.pack(side=tk.LEFT, padx=5)
        
    def bind_events(self):
        """Adiciona eventos de interação."""
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)  # Linux
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)  # Linux
        self.root.bind("<Control-o>", lambda e: self.select_pdf())
        self.root.bind("<Delete>", lambda e: self.remove_range())
        
    def _on_mousewheel(self, event):
        """Gerencia o scroll do mouse na visualização de páginas."""
        if event.delta:
            self.canvas.yview_scroll(-int(event.delta/120), "units")
        elif event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")
            
    def select_pdf(self):
        """Abre um diálogo para selecionar um arquivo PDF."""
        self.pdf_path = filedialog.askopenfilename(
            title="Selecione o arquivo PDF", 
            filetypes=[("Arquivos PDF", "*.pdf")]
        )
        if not self.pdf_path:
            self.status_var.set("Nenhum arquivo selecionado.")
            return

        self.status_var.set("Carregando PDF, por favor aguarde...")
        self.clear_ranges()  # Limpa dados antigos
        threading.Thread(target=self._load_pdf, daemon=True).start()
            
    def _load_pdf(self):
        """Carrega o PDF em uma thread separada."""
        try:
            with open(self.pdf_path, "rb") as f:
                pdf_data = f.read()
            self.pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_data))
            self.total_pages = len(self.pdf_reader.pages)
            
            doc = fitz.open(self.pdf_path)
            self.page_images = []
            
            for i, page in enumerate(doc):
                if i % 5 == 0:
                    # Atualiza o status indicando a página atual
                    self.root.after(0, lambda i=i: self.status_var.set(
                        f"Carregando página {i+1} de {len(doc)}..."
                    ))
                try:
                    # Para páginas a partir da 400, utiliza um fator de redução mais agressivo
                    scale_factor = 0.3 if i >= 400 else 0.5
                    matrix = fitz.Matrix(scale_factor, scale_factor)
                    # Desabilita o canal alpha para reduzir uso de memória
                    pix = page.get_pixmap(matrix=matrix, alpha=False)
                    img_data = pix.tobytes("png")
                    img = Image.open(io.BytesIO(img_data))
                    self.page_images.append(img)
                except Exception as e:
                    print(f"Erro ao carregar a página {i+1}: {e}")
                    # Se ocorrer um erro, cria uma imagem placeholder
                    placeholder = Image.new("RGB", (150, 200), color="grey")
                    self.page_images.append(placeholder)
                    
            self.root.after(0, self._finalize_pdf_loading)
            
        except Exception as e:
            self.root.after(0, lambda: self.status_var.set(f"Erro: {str(e)}"))
            self.root.after(0, lambda: messagebox.showerror("Erro", f"Erro ao carregar o PDF: {e}"))

    def _finalize_pdf_loading(self):
        """Finaliza o processo de carregamento do PDF."""
        filename = os.path.basename(self.pdf_path)
        self.status_var.set(f"PDF carregado: {filename} ({self.total_pages} páginas)")
        self.display_pages()

    def display_pages(self):
        """Exibe as miniaturas das páginas do PDF."""
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        self.thumbnails = []
        # Inicializa self.labels com None para cada página
        self.labels = [None] * len(self.page_images)
        
        self.current_page = 0
        self.pages_per_view = 30
        self._update_page_view()
        
    def _create_thumbnail(self, i):
        """Cria e exibe o thumbnail para a página de índice i."""
        img = self.page_images[i]
        img_copy = img.copy()
        img_copy.thumbnail((150, 200))
        tk_img = ImageTk.PhotoImage(img_copy)
        if len(self.thumbnails) > i:
            self.thumbnails[i] = tk_img
        else:
            self.thumbnails.append(tk_img)
            
        page_frame = ttk.Frame(self.scrollable_frame)
        row = i // self.columns
        col = i % self.columns
        page_frame.grid(row=row, column=col, padx=10, pady=10)
        
        lbl = tk.Label(
            page_frame, 
            image=tk_img, 
            borderwidth=2, 
            relief="solid",
            cursor="hand2",
            bg=self.bg_color
        )
        lbl.pack()
        lbl.bind("<Button-1>", lambda event, page=i: self.on_page_click(page))
        self.labels[i] = lbl
        
        lbl_page = ttk.Label(
            page_frame, 
            text=f"Página {i+1}",
            background="#f0f0f0",
            relief="flat",
            padding=(5, 2)
        )
        lbl_page.pack(fill=tk.X)
        
    def _update_page_view(self):
        """Atualiza a visualização atual das páginas."""
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        start_idx = self.current_page * self.pages_per_view
        end_idx = min(start_idx + self.pages_per_view, len(self.page_images))
        
        for i in range(start_idx, end_idx):
            self._create_thumbnail(i)
            
        self.page_nav_var.set(f"Páginas {start_idx+1}-{end_idx} de {len(self.page_images)}")
        
    def prev_page(self):
        """Navega para o conjunto anterior de páginas."""
        if self.current_page > 0:
            self.current_page -= 1
            self._update_page_view()
            
    def next_page(self):
        """Navega para o próximo conjunto de páginas."""
        if (self.current_page + 1) * self.pages_per_view < len(self.page_images):
            self.current_page += 1
            self._update_page_view()
        
    def update_range_listbox(self):
        """Atualiza a listbox com a numeração das faixas e a quantidade de páginas em cada faixa."""
        self.listbox_ranges.delete(0, tk.END)
        for idx, (start, end) in enumerate(self.ranges, start=1):
            num_pages = end - start
            entry_text = f"Faixa {idx}: Páginas {start+1} - {end} ({num_pages} página{'s' if num_pages > 1 else ''})"
            self.listbox_ranges.insert(tk.END, entry_text)
        
    def restore_pages(self, start, end):
        """Recria os thumbnails das páginas do intervalo [start, end) e rola para o início."""
        for i in range(start, end):
            if self.labels[i] is None:
                self._create_thumbnail(i)
                if self.last_clicked_page == i:
                    if self.labels[i] is not None and self.labels[i].winfo_exists():
                        self.labels[i].config(bg=self.selected_color)
        self.canvas.yview_moveto(0)
                    
    def on_page_click(self, page):
        """Gerencia o clique em uma página para definir faixas."""
        self.last_clicked_page = page
        if self.current_range_start is None:
            self.current_range_start = page
            self.status_var.set(f"Página {page+1} selecionada como início. Selecione a página final.")
            if self.labels[page] is not None and self.labels[page].winfo_exists():
                self.labels[page].config(bg=self.selected_color)
        else:
            start = min(self.current_range_start, page)
            end = max(self.current_range_start, page) + 1  # +1 para incluir a página final
            self.ranges.append((start, end))
            self.update_range_listbox()
            self.status_var.set(f"Faixa adicionada: Páginas {start+1} - {end} ({end - start} páginas).")
            if self.current_range_start is not None and self.labels[self.current_range_start] is not None and self.labels[self.current_range_start].winfo_exists():
                self.labels[self.current_range_start].config(bg="SystemButtonFace")
            self.current_range_start = None

            for p in range(start, end):
                if self.labels[p] is not None and self.labels[p].winfo_exists():
                    self.labels[p].master.destroy()
                    self.labels[p] = None
            self.canvas.yview_moveto(0)

    def remove_range(self):
        """Remove a faixa selecionada e restaura os thumbnails correspondentes."""
        selected = self.listbox_ranges.curselection()
        if not selected:
            self.status_var.set("Nenhuma faixa selecionada para remover.")
            return
        
        index = selected[0]
        removed_range = self.ranges[index]
        del self.ranges[index]
        self.update_range_listbox()
        self.status_var.set("Faixa removida.")
        self.restore_pages(removed_range[0], removed_range[1])

    def clear_ranges(self):
        """Remove todas as faixas e restaura todos os thumbnails."""
        self.listbox_ranges.delete(0, tk.END)
        self.ranges = []
        if self.current_range_start is not None and self.labels[self.current_range_start] is not None and self.labels[self.current_range_start].winfo_exists():
            self.labels[self.current_range_start].config(bg="SystemButtonFace")
        self.current_range_start = None
        self.status_var.set("Todas as faixas foram removidas.")
        for i in range(len(self.page_images)):
            if self.labels[i] is None:
                self._create_thumbnail(i)
        self.canvas.yview_moveto(0)
                
    def select_output_dir(self):
        """Permite selecionar o diretório de saída para os PDFs gerados."""
        dir_path = filedialog.askdirectory(
            title="Selecione a pasta para salvar os PDFs"
        )
        if dir_path:
            self.output_dir = dir_path
            self.status_var.set(f"Pasta de saída: {self.output_dir}")

    def generate_pdfs_with_progress(self):
        """Prepara a geração de PDFs com barra de progresso."""
        if not self.ranges:
            messagebox.showwarning("Aviso", "Nenhuma faixa de páginas foi definida.")
            return

        self.progress.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 10))
        self.progress_var.set(0)
        threading.Thread(target=self._generate_pdfs_thread, daemon=True).start()
            
    def _generate_pdfs_thread(self):
        """Executa a geração dos PDFs em uma thread separada."""
        self.root.after(0, lambda: self.status_var.set("Gerando PDFs..."))
        total_ranges = len(self.ranges)
        generated_files = []
        original_filename = os.path.basename(self.pdf_path)
        base, ext = os.path.splitext(original_filename)
        
        try:
            with open(self.pdf_path, "rb") as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for idx, (start, end) in enumerate(self.ranges):
                    progress = (idx / total_ranges) * 100
                    self.root.after(0, lambda p=progress: self.progress_var.set(p))
                    self.root.after(0, lambda i=idx, t=total_ranges: 
                                    self.status_var.set(f"Gerando parte {i+1} de {t}..."))
                    writer = PyPDF2.PdfWriter()
                    for page_num in range(start, end):
                        writer.add_page(pdf_reader.pages[page_num])
                    
                    # Monta o nome de saída usando "Parte_{número}_<nome_original>.pdf"
                    # Se o arquivo já existir, adiciona um número incremental
                    proposed_name = f"Parte_{idx+1}_{base}{ext}"
                    output_filename = os.path.join(self.output_dir, proposed_name)
                    counter = 1
                    while os.path.exists(output_filename):
                        proposed_name = f"Parte_{idx+1}_{counter}_{base}{ext}"
                        output_filename = os.path.join(self.output_dir, proposed_name)
                        counter += 1
                        
                    with open(output_filename, "wb") as out_f:
                        writer.write(out_f)
                    generated_files.append(output_filename)
                    time.sleep(0.1)
                    
            self.root.after(0, lambda: self.progress_var.set(100))
            self.root.after(0, lambda: self._show_completion_message(generated_files))
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Erro", f"Erro ao gerar PDFs: {e}"))
            self.root.after(0, lambda: self.status_var.set("Erro na geração dos PDFs."))
            
        self.root.after(3000, lambda: self.progress.pack_forget())
    
    def _show_completion_message(self, files):
        """Mostra mensagem de conclusão."""
        self.status_var.set(f"{len(files)} PDFs gerados com sucesso.")
        message = "PDFs gerados com sucesso:\n\n"
        for file in files:
            message += f"• {os.path.basename(file)}\n"
        message += f"\nSalvos em: {self.output_dir}"
        messagebox.showinfo("Processamento Concluído", message)

if __name__ == "__main__":
    root = tk.Tk()
    app = PDFSplitterApp(root)
    root.mainloop()
