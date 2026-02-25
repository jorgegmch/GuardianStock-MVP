import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3

# --- CAPA DE DATOS (BACKEND) - LÓGICA DE RE-INDEXACIÓN ALFABÉTICA ---
class GestorBaseDatos:
    def __init__(self, db_name="inventario.db"):
        self.db_name = db_name
        self.conexion_inicial()

    def ejecutar_consulta(self, query, parametros=()):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute(query, parametros)
            conn.commit()
            return cursor

    def conexion_inicial(self):
        # Se elimina AUTOINCREMENT para permitir la re-indexación manual controlada
        query = """
            CREATE TABLE IF NOT EXISTS productos (
                id INTEGER PRIMARY KEY,
                nombre TEXT NOT NULL,
                precio REAL NOT NULL,
                cantidad INTEGER NOT NULL,
                stock_minimo INTEGER NOT NULL
            )
        """
        self.ejecutar_consulta(query)

    def reindexar_alfabeticamente(self):
        """Reasigna los IDs de todos los productos basándose en el orden alfabético"""
        # 1. Obtener todos los productos actuales ordenados por nombre
        query_obtener = "SELECT nombre, precio, cantidad, stock_minimo FROM productos ORDER BY nombre COLLATE NOCASE ASC"
        cursor = self.ejecutar_consulta(query_obtener)
        productos = cursor.fetchall()

        # 2. Limpiar la tabla por completo
        self.ejecutar_consulta("DELETE FROM productos")

        # 3. Insertar nuevamente con nuevos IDs secuenciales
        for indice, (nom, pre, cant, st_min) in enumerate(productos, start=1):
            query_insertar = "INSERT INTO productos (id, nombre, precio, cantidad, stock_minimo) VALUES (?, ?, ?, ?, ?)"
            self.ejecutar_consulta(query_insertar, (indice, nom, pre, cant, st_min))

    def obtener_resumen_financiero(self):
        query = "SELECT SUM(cantidad), SUM(precio * cantidad) FROM productos"
        cursor = self.ejecutar_consulta(query)
        resumen = cursor.fetchone()
        return (resumen[0] or 0, resumen[1] or 0)

    def agregar_producto(self, nombre, precio, cantidad, stock_minimo):
        # Insertamos y luego reordenamos todo para que el ID sea correcto alfabéticamente
        query = "INSERT INTO productos (nombre, precio, cantidad, stock_minimo) VALUES (?, ?, ?, ?)"
        self.ejecutar_consulta(query, (nombre, precio, cantidad, stock_minimo))
        self.reindexar_alfabeticamente()

    def eliminar_producto(self, id_producto):
        query = "DELETE FROM productos WHERE id = ?"
        self.ejecutar_consulta(query, (id_producto,))
        self.reindexar_alfabeticamente()

    def actualizar_producto(self, id_producto, nombre, precio, cantidad, stock_minimo):
        # Al actualizar el nombre, la posición alfabética podría cambiar
        query = """
            UPDATE productos 
            SET nombre = ?, precio = ?, cantidad = ?, stock_minimo = ? 
            WHERE id = ?
        """
        self.ejecutar_consulta(query, (nombre, precio, cantidad, stock_minimo, id_producto))
        self.reindexar_alfabeticamente()

    def obtener_todos(self):
        query = "SELECT * FROM productos ORDER BY id ASC"
        cursor = self.ejecutar_consulta(query)
        return cursor.fetchall()

    def obtener_urgentes(self):
        query = "SELECT * FROM productos WHERE cantidad <= stock_minimo ORDER BY nombre ASC"
        cursor = self.ejecutar_consulta(query)
        return cursor.fetchall()


# --- CAPA DE PRESENTACIÓN (FRONTEND) ---
class GuardianInventarioApp:
    
    COL_FONDO = "#FFFFFF"       
    COL_DARK = "#2C3E50"        
    COL_AQUA = "#16A085"        
    COL_ORANGE = "#E67E22"      
    COL_LIGHT_GRAY = "#ECF0F1"  
    COL_TEXT = "#34495E"        

    def __init__(self, root):
        self.db = GestorBaseDatos()
        self.root = root
        self.root.title("El Guardián del Inventario")
        self.root.geometry("1100x750")
        self.root.configure(bg=self.COL_FONDO)
        
        self.nombre_var = tk.StringVar()
        self.precio_var = tk.StringVar()
        self.cantidad_var = tk.StringVar()
        self.minimo_var = tk.StringVar()
        self.total_productos_var = tk.StringVar(value="0 Units")
        self.valor_inventario_var = tk.StringVar(value="$ 0")
        self.producto_seleccionado_id = None

        self._configurar_estilos()
        self._construir_layout()
        self.actualizar_vistas()

    def _configurar_estilos(self):
        style = ttk.Style()
        style.theme_use('clam') 
        style.configure("Treeview", background=self.COL_FONDO, foreground=self.COL_TEXT, rowheight=30, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", background=self.COL_DARK, foreground="white", font=("Segoe UI", 10, "bold"), relief="flat")
        style.map("Treeview", background=[('selected', self.COL_AQUA)])

    def _construir_layout(self):
        header_frame = tk.Frame(self.root, bg=self.COL_DARK, height=60)
        header_frame.pack(fill="x")
        tk.Label(header_frame, text="EL GUARDIÁN DEL INVENTARIO", bg=self.COL_DARK, fg="white", font=("Segoe UI", 16, "bold"), pady=15).pack()

        main_container = tk.Frame(self.root, bg=self.COL_FONDO)
        main_container.pack(fill="both", expand=True, padx=40, pady=10)

        stats_frame = tk.Frame(main_container, bg=self.COL_FONDO)
        stats_frame.pack(fill="x", pady=(0, 20))

        card_unidades = tk.Frame(stats_frame, bg=self.COL_LIGHT_GRAY, bd=0, padx=20, pady=10)
        card_unidades.pack(side="left", expand=True, fill="x", padx=(0, 10))
        tk.Label(card_unidades, text="TOTAL PRODUCTOS EN STOCK", bg=self.COL_LIGHT_GRAY, fg=self.COL_TEXT, font=("Segoe UI", 9, "bold")).pack()
        tk.Label(card_unidades, textvariable=self.total_productos_var, bg=self.COL_LIGHT_GRAY, fg=self.COL_AQUA, font=("Segoe UI", 18, "bold")).pack()

        card_valor = tk.Frame(stats_frame, bg=self.COL_LIGHT_GRAY, bd=0, padx=20, pady=10)
        card_valor.pack(side="left", expand=True, fill="x", padx=(10, 0))
        tk.Label(card_valor, text="VALOR TOTAL DEL INVENTARIO", bg=self.COL_LIGHT_GRAY, fg=self.COL_TEXT, font=("Segoe UI", 9, "bold")).pack()
        tk.Label(card_valor, textvariable=self.valor_inventario_var, bg=self.COL_LIGHT_GRAY, fg=self.COL_ORANGE, font=("Segoe UI", 18, "bold")).pack()

        control_frame = tk.LabelFrame(main_container, text=" Registro y Edición ", bg=self.COL_FONDO, fg=self.COL_AQUA, font=("Segoe UI", 11, "bold"), bd=1, relief="solid")
        control_frame.pack(fill="x", pady=(0, 20), ipady=10)

        tk.Label(control_frame, text="Nombre del Producto", font=("Segoe UI", 9, "bold"), bg=self.COL_FONDO).grid(row=0, column=0, padx=20, pady=(10,5), sticky="w")
        tk.Entry(control_frame, textvariable=self.nombre_var, font=("Segoe UI", 10), bg=self.COL_LIGHT_GRAY, relief="flat", highlightthickness=1, highlightbackground="#BDC3C7").grid(row=1, column=0, padx=20, pady=(0,10), sticky="ew", columnspan=3)

        tk.Label(control_frame, text="Precio Venta (COP)", font=("Segoe UI", 9, "bold"), bg=self.COL_FONDO).grid(row=2, column=0, padx=20, pady=(0,5), sticky="w")
        tk.Label(control_frame, text="Cantidad actual", font=("Segoe UI", 9, "bold"), bg=self.COL_FONDO).grid(row=2, column=1, padx=20, pady=(0,5), sticky="w")
        tk.Label(control_frame, text="Mínimo Seguridad", font=("Segoe UI", 9, "bold"), bg=self.COL_FONDO).grid(row=2, column=2, padx=20, pady=(0,5), sticky="w")

        tk.Entry(control_frame, textvariable=self.precio_var, font=("Segoe UI", 10), bg=self.COL_LIGHT_GRAY, justify="center", relief="flat", highlightthickness=1, highlightbackground="#BDC3C7").grid(row=3, column=0, padx=20, pady=(0,10), sticky="ew")
        tk.Entry(control_frame, textvariable=self.cantidad_var, font=("Segoe UI", 10), bg=self.COL_LIGHT_GRAY, justify="center", relief="flat", highlightthickness=1, highlightbackground="#BDC3C7").grid(row=3, column=1, padx=20, pady=(0,10), sticky="ew")
        tk.Entry(control_frame, textvariable=self.minimo_var, font=("Segoe UI", 10), bg=self.COL_LIGHT_GRAY, justify="center", relief="flat", highlightthickness=1, highlightbackground="#BDC3C7").grid(row=3, column=2, padx=20, pady=(0,10), sticky="ew")
        
        control_frame.columnconfigure(0, weight=2)
        control_frame.columnconfigure(1, weight=1)
        control_frame.columnconfigure(2, weight=1)

        action_frame = tk.Frame(main_container, bg=self.COL_FONDO)
        action_frame.pack(fill="x", pady=(0, 20))

        def btn_style(bg_color):
            return {"bg": bg_color, "fg": "white", "font": ("Segoe UI", 9, "bold"), "relief": "flat", "padx": 15, "pady": 8, "cursor": "hand2"}

        tk.Button(action_frame, text="GUARDAR", command=self.agregar, **btn_style(self.COL_ORANGE)).pack(side="left", padx=(0, 5))
        tk.Button(action_frame, text="ACTUALIZAR", command=self.actualizar, **btn_style(self.COL_AQUA)).pack(side="left", padx=5)
        tk.Button(action_frame, text="ELIMINAR", command=self.eliminar, bg="#C0392B", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=15, pady=8, cursor="hand2").pack(side="left", padx=5)
        tk.Button(action_frame, text="LIMPIAR", command=self.limpiar_campos, bg="#7F8C8D", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=15, pady=8, cursor="hand2").pack(side="left", padx=5)

        tk.Button(action_frame, text="TODOS", command=self.listar_productos, **btn_style(self.COL_DARK)).pack(side="right", padx=(5, 0))
        tk.Button(action_frame, text="URGENCIAS ⚠", command=self.listar_urgentes, **btn_style("#D35400")).pack(side="right", padx=5)

        tree_frame = tk.Frame(main_container, bg="white", bd=1, relief="solid") 
        tree_frame.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(tree_frame, columns=("ID", "Nombre", "Precio", "Cantidad", "Min"), show="headings")
        self.tree.heading("ID", text="ID"); self.tree.column("ID", width=40, anchor="center")
        self.tree.heading("Nombre", text="Producto"); self.tree.column("Nombre", width=350)
        self.tree.heading("Precio", text="Precio Unitario"); self.tree.column("Precio", width=120, anchor="e")
        self.tree.heading("Cantidad", text="Stock"); self.tree.column("Cantidad", width=80, anchor="center")
        self.tree.heading("Min", text="Mínimo"); self.tree.column("Min", width=80, anchor="center")

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill="both", expand=True)
        scrollbar.pack(side=tk.RIGHT, fill="y")
        self.tree.bind("<<TreeviewSelect>>", self.seleccionar_item)

    def _formatear_cop(self, valor):
        return "$ {:,.0f}".format(float(valor or 0))

    def actualizar_vistas(self):
        self.listar_productos()
        cant_total, valor_total = self.db.obtener_resumen_financiero()
        self.total_productos_var.set(f"{int(cant_total)} Units")
        self.valor_inventario_var.set(self._formatear_cop(valor_total))

    def validar_entradas(self):
        try:
            if not self.nombre_var.get(): raise ValueError
            float(self.precio_var.get()); int(self.cantidad_var.get()); int(self.minimo_var.get())
            return True
        except:
            messagebox.showwarning("Error", "Datos inválidos. Verifique los campos numéricos.")
            return False

    def listar_productos(self):
        registros = self.db.obtener_todos()
        self._llenar_tabla(registros)

    def listar_urgentes(self):
        registros = self.db.obtener_urgentes()
        self._llenar_tabla(registros)

    def _llenar_tabla(self, registros):
        for row in self.tree.get_children(): self.tree.delete(row)
        for row in registros:
            item_id = self.tree.insert("", tk.END, values=(row[0], row[1], self._formatear_cop(row[2]), row[3], row[4]))
            if row[3] <= row[4]: self.tree.item(item_id, tags=('urgente',))
        self.tree.tag_configure('urgente', background='#FDEBD0') 

    def agregar(self):
        if self.validar_entradas():
            self.db.agregar_producto(self.nombre_var.get(), float(self.precio_var.get()), int(self.cantidad_var.get()), int(self.minimo_var.get()))
            self.limpiar_campos()
            self.actualizar_vistas()

    def actualizar(self):
        if self.producto_seleccionado_id and self.validar_entradas():
            self.db.actualizar_producto(self.producto_seleccionado_id, self.nombre_var.get(), float(self.precio_var.get()), int(self.cantidad_var.get()), int(self.minimo_var.get()))
            self.limpiar_campos()
            self.actualizar_vistas()

    def eliminar(self):
        if self.producto_seleccionado_id and messagebox.askyesno("Confirmar", "¿Eliminar producto?"):
            self.db.eliminar_producto(self.producto_seleccionado_id)
            self.limpiar_campos()
            self.actualizar_vistas()

    def seleccionar_item(self, event):
        seleccion = self.tree.selection()
        if seleccion:
            datos = self.tree.item(seleccion)['values']
            self.producto_seleccionado_id = datos[0]
            self.nombre_var.set(datos[1])
            self.precio_var.set(str(datos[2]).replace("$", "").replace(",", "").strip())
            self.cantidad_var.set(datos[3])
            self.minimo_var.set(datos[4])

    def limpiar_campos(self):
        self.nombre_var.set(""); self.precio_var.set(""); self.cantidad_var.set(""); self.minimo_var.set("")
        self.producto_seleccionado_id = None

if __name__ == "__main__":
    root = tk.Tk()
    app = GuardianInventarioApp(root)
    root.mainloop()