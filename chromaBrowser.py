import tkinter as tk
from tkinter import ttk, messagebox
import json
import chromadb
import tkinter.font as tkfont
from chromadb.config import Settings

class ChromaBrowserApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ChromaDB Collection Browser")
        self.root.geometry("800x600")

        self.collection_map = {}
        self.server_host = tk.StringVar(value="127.0.0.1")
        self.server_port = tk.IntVar(value=8000)
        self.client = None
        self.text_font_family = tk.StringVar(value="Consolas")
        self.text_font_size = tk.IntVar(value=15)

        self.build_gui()

    def display_chunk(self, event):
        selected = self.chunk_tree.selection()
        if not selected:
            return
        index = int(selected[0])
        content = self.chunk_data[index]
        self.meta_tab.delete(1.0, tk.END)
        self.content_tab.delete(1.0, tk.END)
        self.meta_tab.insert(tk.END, json.dumps(self.chunk_meta[index], indent=2))
        self.content_tab.insert(tk.END, content)

    def build_gui(self):
        left_frame = tk.Frame(self.root, width=250)
        left_frame.grid(row=1, column=0, sticky="nsw", padx=10, pady=5)
        left_frame.grid_propagate(False)

        list_frame = tk.Frame(left_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        collection_scrollbar = tk.Scrollbar(list_frame)
        collection_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 1), pady=(2, 2))
        self.collection_list = tk.Listbox(list_frame, height=10, yscrollcommand=collection_scrollbar.set)
        self.collection_list.pack(fill=tk.BOTH, expand=True)
        collection_scrollbar.config(command=self.collection_list.yview)
        self.collection_list.bind("<<ListboxSelect>>", self.load_chunks_from_selection)
        self.collection_list.bind("<Button-3>", self.show_collection_context_menu)

        tree_frame = tk.Frame(left_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        tree_scrollbar = tk.Scrollbar(tree_frame)
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 1), pady=(22, 5))
        self.chunk_tree = ttk.Treeview(tree_frame, yscrollcommand=tree_scrollbar.set)
        self.chunk_tree.pack(fill=tk.BOTH, expand=True, pady=5)
        tree_scrollbar.config(command=self.chunk_tree.yview)
        self.chunk_tree.bind("<<TreeviewSelect>>", self.display_chunk)

        chunk_frame = tk.Frame(self.root)
        chunk_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=5)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

        text_font = tkfont.Font(family=self.text_font_family.get(), size=self.text_font_size.get())
        self.tab_control = ttk.Notebook(chunk_frame)
        self.tab_control.pack(fill=tk.BOTH, expand=True)

        self.meta_tab = tk.Text(self.tab_control, wrap=tk.WORD, bg="#f0f0f0", font=text_font)
        self.meta_tab.bind("<Button-3>", lambda e: self.show_context_menu(e, self.meta_tab))
        content_frame = tk.Frame(self.tab_control)
        content_scrollbar = tk.Scrollbar(content_frame)
        content_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.content_tab = tk.Text(content_frame, wrap=tk.WORD, bg="#fdfdfd", yscrollcommand=content_scrollbar.set, font=text_font)
        self.content_tab.bind("<Button-3>", lambda e: self.show_context_menu(e, self.content_tab))
        self.content_tab.pack(fill=tk.BOTH, expand=True)
        content_scrollbar.config(command=self.content_tab.yview)

        self.tab_control.add(self.meta_tab, text="Metadaten")
        self.tab_control.add(content_frame, text="Inhalt")

        top_frame = tk.Frame(self.root)
        top_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=5)

        tk.Label(top_frame, text="Chroma Host:").pack(side=tk.LEFT)
        tk.Entry(top_frame, textvariable=self.server_host, width=20).pack(side=tk.LEFT, padx=5)
        tk.Label(top_frame, text="Port:").pack(side=tk.LEFT)
        tk.Entry(top_frame, textvariable=self.server_port, width=6).pack(side=tk.LEFT, padx=5)
        tk.Button(top_frame, text="Verbinden", command=self.connect_to_server).pack(side=tk.LEFT, padx=10)

    def load_chunks_from_selection(self, event):
        selected = self.collection_list.curselection()
        if not selected:
            return
        collection_name = self.collection_list.get(selected[0])
        self.load_chunks(collection_name)

    def load_chunks(self, collection_name):
        try:
            collections = self.client.list_collections()

            self.meta_tab.delete(1.0, tk.END)
            self.content_tab.delete(1.0, tk.END)
            self.chunk_tree.delete(*self.chunk_tree.get_children())
            self.chunk_data = []
            self.chunk_meta = []
            collection = self.client.get_collection(collection_name)
            result = collection.get(include=["documents", "metadatas"])
            docs = result.get("documents", [])
            metas = result.get("metadatas", [])
            for i, doc in enumerate(docs):
                content = doc[0] if isinstance(doc, list) else doc
                meta = metas[i] if i < len(metas) else {}
                self.chunk_data.append(content)
                self.chunk_meta.append(meta)
                self.chunk_tree.insert("", "end", iid=str(i), text=f"Chunk {i+1}")

        except Exception as e:
            messagebox.showerror("Fehler beim Laden der Chunks", str(e))
            print("Fehler beim Laden der Chunks", str(e))

    def show_context_menu(self, event, widget):
        if event.num == 3:
            menu = tk.Menu(self.root, tearoff=0)
            menu.add_command(label="Alles auswählen", command=lambda: widget.tag_add(tk.SEL, "1.0", tk.END))
            menu.add_command(label="Kopieren", command=lambda: widget.event_generate("<<Copy>>"))
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()

    def show_collection_context_menu(self, event):
        widget = event.widget
        index = widget.nearest(event.y)
        if index < 0:
            return
        widget.selection_clear(0, tk.END)
        widget.selection_set(index)
        collection_name = widget.get(index)
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label=f"Collection '{collection_name}' löschen", command=lambda: self.delete_collection(collection_name))
        menu.add_command(label=f"Details zu '{collection_name}' anzeigen", command=lambda: self.show_collection_info(collection_name))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def delete_collection(self, name):
        confirm = messagebox.askyesno("Collection löschen", f"Möchtest du die Collection '{name}' wirklich dauerhaft vom Server löschen?")
        if confirm:
            try:
                self.client.delete_collection(name)
                self.connect_to_server()
            except Exception as e:
                messagebox.showerror("Fehler beim Löschen", str(e))
                print("Fehler beim Löschen der Collection:", str(e))

    def show_collection_info(self, name):
        try:
            collection = self.client.get_collection(name)
            count = collection.count()
            info = f"Name: {collection.name} Chunks: {count} \n"
            if collection.metadata:
                info += f"Metadaten: {json.dumps(collection.metadata, indent=2)} "
            info += "Embedding: unbekannt (nicht verfügbar im HTTP-Client) "
            messagebox.showinfo(f"Details zu '{name}'", info)
        except Exception as e:
            messagebox.showerror("Fehler beim Anzeigen der Details", str(e))
            print("Fehler beim Anzeigen der Collection-Details:", str(e))

    def connect_to_server(self):
        try:
            self.client = chromadb.HttpClient(host=self.server_host.get(), port=self.server_port.get())
            self.collection_list.delete(0, tk.END)
            self.collection_map.clear()
            self.chunk_tree.delete(*self.chunk_tree.get_children())
            self.meta_tab.delete(1.0, tk.END)
            self.content_tab.delete(1.0, tk.END)
            collections = self.client.list_collections()
            for name in collections:
                self.collection_list.insert(tk.END, name)
                self.collection_map[name] = name

        except Exception as e:
            messagebox.showerror("Verbindungsfehler", str(e))
            print("Verbindungsfehler:", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = ChromaBrowserApp(root)
    root.mainloop()
