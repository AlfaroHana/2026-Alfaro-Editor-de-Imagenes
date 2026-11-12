import os
import smtplib
import re
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from PIL import Image, ImageEnhance, ImageFilter, ImageOps, ImageTk
from email.message import EmailMessage


class VisorEditorApp:

  def __init__(self, root):
    self.root = root
    self.root.title("Procesador de Imágenes - Trabajo Práctico")
    self.root.geometry("1050x750")

    self.imagen_original = None
    self.imagen_procesada = None
    self.ruta_actual = None

    # Historial (Deshacer / Rehacer)
    self.historial = []
    self.indice_historial = -1

    # Variables para recorte con mouse
    self.recortando = False
    self.inicio_x = 0
    self.inicio_y = 0
    self.rect_id = None

    self._crear_menu()
    self._crear_interfaz()

  def _crear_menu(self):
    menubar = tk.Menu(self.root)
    self.root.config(menu=menubar)

    # 1. Menú Archivo
    menu_archivo = tk.Menu(menubar, tearoff=0)
    menu_archivo.add_command(
        label="Abrir imagen...", command=self.abrir_imagen
    )
    menu_archivo.add_command(
        label="Guardar como...", command=self.guardar_como
    )
    menu_archivo.add_separator()
    menu_archivo.add_command(
        label="Enviar por Correo...", command=self.abrir_ventana_correo
    )
    menu_archivo.add_separator()
    menu_archivo.add_command(label="Salir", command=self.root.quit)
    menubar.add_cascade(label="Archivo", menu=menu_archivo)

    # 2. Menú Editar (Transformaciones, Recorte y Deshacer/Rehacer)
    self.menu_editar = tk.Menu(menubar, tearoff=0)
    self.menu_editar.add_command(
        label="Deshacer", command=self.deshacer, state=tk.DISABLED
    )
    self.menu_editar.add_command(
        label="Rehacer", command=self.rehacer, state=tk.DISABLED
    )
    self.menu_editar.add_separator()
    self.menu_editar.add_command(
        label="Recortar por Coordenadas...", command=self.recortar_por_coordenadas
    )
    self.menu_editar.add_command(
        label="Voltear Horizontal",
        command=lambda: self.previsualizar_accion(
            "Voltear Horizontal",
            self.imagen_procesada.transpose(Image.FLIP_LEFT_RIGHT),
        ),
    )
    self.menu_editar.add_command(
        label="Voltear Vertical",
        command=lambda: self.previsualizar_accion(
            "Voltear Vertical",
            self.imagen_procesada.transpose(Image.FLIP_TOP_BOTTOM),
        ),
    )
    self.menu_editar.add_separator()
    self.menu_editar.add_command(
        label="Rotar 90° Izquierda",
        command=lambda: self.previsualizar_accion(
            "Rotar 90° Izquierda",
            self.imagen_procesada.rotate(90, expand=True),
        ),
    )
    self.menu_editar.add_command(
        label="Rotar 90° Derecha",
        command=lambda: self.previsualizar_accion(
            "Rotar 90° Derecha",
            self.imagen_procesada.rotate(-90, expand=True),
        ),
    )
    self.menu_editar.add_command(
        label="Rotar 180°",
        command=lambda: self.previsualizar_accion(
            "Rotar 180°", self.imagen_procesada.rotate(180, expand=True)
        ),
    )
    menubar.add_cascade(label="Editar", menu=self.menu_editar)

    # 3. Menú Imagen
    menu_imagen = tk.Menu(menubar, tearoff=0)
    menu_imagen.add_command(
        label="Convertir a Escala de Grises",
        command=lambda: self.previsualizar_accion(
            "Escala de Grises", self.imagen_procesada.convert("L")
        ),
    )
    menubar.add_cascade(label="Imagen", menu=menu_imagen)

    # 4. Menú Filtros
    menu_filtros = tk.Menu(menubar, tearoff=0)
    menu_filtros.add_command(
        label="Desenfoque",
        command=lambda: self.previsualizar_accion(
            "Desenfoque", self.imagen_procesada.filter(ImageFilter.BLUR)
        ),
    )
    menu_filtros.add_command(
        label="Nitidez",
        command=lambda: self.previsualizar_accion(
            "Nitidez",
            ImageEnhance.Sharpness(self.imagen_procesada).enhance(2.0),
        ),
    )
    menu_filtros.add_command(
        label="Detección de Bordes",
        command=lambda: self.previsualizar_accion(
            "Detección de Bordes",
            self.imagen_procesada.filter(ImageFilter.FIND_EDGES),
        ),
    )
    menu_filtros.add_command(
        label="Negativo", command=self.aplicar_negativo_con_preview
    )
    menubar.add_cascade(label="Filtros", menu=menu_filtros)

    # 5. Menú Ayuda
    menu_ayuda = tk.Menu(menubar, tearoff=0)
    menu_ayuda.add_command(
        label="Acerca de...",
        command=lambda: messagebox.showinfo(
            "Ayuda", "Aplicación de Procesamiento de Imágenes en Python y Tkinter"
        ),
    )
    menubar.add_cascade(label="Ayuda", menu=menu_ayuda)

  def _crear_interfaz(self):
    barra_herramientas = ttk.Frame(self.root, padding=5)
    barra_herramientas.pack(side=tk.TOP, fill=tk.X)

    self.btn_deshacer = ttk.Button(
        barra_herramientas,
        text="↩ Deshacer",
        command=self.deshacer,
        state=tk.DISABLED,
    )
    self.btn_deshacer.pack(side=tk.LEFT, padx=5)

    self.btn_rehacer = ttk.Button(
        barra_herramientas,
        text="↪ Rehacer",
        command=self.rehacer,
        state=tk.DISABLED,
    )
    self.btn_rehacer.pack(side=tk.LEFT, padx=5)

    self.btn_modo_recorte = ttk.Button(
        barra_herramientas,
        text="✂ Activar Modo Recorte (Mouse)",
        command=self.alternar_modo_recorte,
        state=tk.DISABLED,
    )
    self.btn_modo_recorte.pack(side=tk.LEFT, padx=15)

    self.lbl_modo = ttk.Label(
        barra_herramientas, text="", foreground="blue", font=("Arial", 10, "bold")
    )
    self.lbl_modo.pack(side=tk.LEFT, padx=5)

    # Botón directo para enviar por correo
    self.btn_enviar_menu = ttk.Button(
        barra_herramientas,
        text="✉ Enviar Correo",
        command=self.abrir_ventana_correo,
        state=tk.DISABLED,
    )
    self.btn_enviar_menu.pack(side=tk.RIGHT, padx=5)

    contenedor = ttk.Frame(self.root)
    contenedor.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    self.canvas_imagen = tk.Canvas(contenedor, background="#2e2e2e")
    self.canvas_imagen.pack(
        side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10)
    )

    self.canvas_imagen.bind("<ButtonPress-1>", self.on_mouse_press)
    self.canvas_imagen.bind("<B1-Motion>", self.on_mouse_drag)
    self.canvas_imagen.bind("<ButtonRelease-1>", self.on_mouse_release)

    panel_ajustes = ttk.LabelFrame(
        contenedor, text=" Ajustes (Brillo, Contraste, Saturación) ", padding=15
    )
    panel_ajustes.pack(side=tk.RIGHT, fill=tk.Y)

    ttk.Label(panel_ajustes, text="Brillo:").pack(anchor="w", pady=(5, 0))
    self.slider_brillo = ttk.Scale(
        panel_ajustes, from_=0.1, to=2.0, value=1.0, command=self.en_cambio_slider
    )
    self.slider_brillo.pack(fill=tk.X, pady=5)

    ttk.Label(panel_ajustes, text="Contraste:").pack(anchor="w", pady=(10, 0))
    self.slider_contraste = ttk.Scale(
        panel_ajustes,
        from_=0.1,
        to=2.0,
        value=1.0,
        command=self.en_cambio_slider,
    )
    self.slider_contraste.pack(fill=tk.X, pady=5)

    ttk.Label(panel_ajustes, text="Saturación:").pack(anchor="w", pady=(10, 0))
    self.slider_saturacion = ttk.Scale(
        panel_ajustes,
        from_=0.0,
        to=3.0,
        value=1.0,
        command=self.en_cambio_slider,
    )
    self.slider_saturacion.pack(fill=tk.X, pady=5)

    btn_frame = ttk.Frame(panel_ajustes)
    btn_frame.pack(fill=tk.X, pady=20)

    self.btn_confirmar_ajustes = ttk.Button(
        btn_frame,
        text="Confirmar Ajustes",
        command=self.confirmar_ajustes,
        state=tk.DISABLED,
    )
    self.btn_confirmar_ajustes.pack(fill=tk.X, pady=5)

    self.btn_cancelar_ajustes = ttk.Button(
        btn_frame,
        text="Cancelar Ajustes",
        command=self.cancelar_ajustes,
        state=tk.DISABLED,
    )
    self.btn_cancelar_ajustes.pack(fill=tk.X, pady=5)

  def actualizar_vista(self):
    if self.imagen_procesada:
      self.canvas_imagen.delete("all")
      canvas_width = self.canvas_imagen.winfo_width()
      canvas_height = self.canvas_imagen.winfo_height()

      if canvas_width < 10:
        canvas_width = 700
      if canvas_height < 10:
        canvas_height = 550

      img_temp = self.imagen_procesada.copy()
      img_temp.thumbnail((canvas_width - 20, canvas_height - 20))

      self.tk_image = ImageTk.PhotoImage(img_temp)
      self.img_width, self.img_height = img_temp.size

      self.pos_x = (canvas_width - self.img_width) // 2
      self.pos_y = (canvas_height - self.img_height) // 2

      self.canvas_imagen.create_image(
          self.pos_x, self.pos_y, anchor=tk.NW, image=self.tk_image
      )
    else:
      self.canvas_imagen.delete("all")
      self.canvas_imagen.create_text(
          350,
          250,
          text="No hay imagen cargada.\nVaya a Archivo > Abrir imagen",
          fill="white",
          font=("Arial", 12),
          justify="center",
      )

  def registrar_cambio(self, nueva_imagen):
    self.historial = self.historial[: self.indice_historial + 1]
    self.historial.append(nueva_imagen.copy())
    self.indice_historial += 1
    self.imagen_procesada = nueva_imagen
    self.actualizar_vista()
    self.actualizar_estado_botones()

  def actualizar_estado_botones(self):
    activo = self.imagen_procesada is not None
    if activo:
      self.btn_modo_recorte.config(state=tk.NORMAL)
      self.btn_enviar_menu.config(state=tk.NORMAL)
    else:
      self.btn_modo_recorte.config(state=tk.DISABLED)
      self.btn_enviar_menu.config(state=tk.DISABLED)

    if self.indice_historial > 0:
      self.btn_deshacer.config(state=tk.NORMAL)
      self.menu_editar.entryconfig("Deshacer", state=tk.NORMAL)
    else:
      self.btn_deshacer.config(state=tk.DISABLED)
      self.menu_editar.entryconfig("Deshacer", state=tk.DISABLED)

    if self.indice_historial < len(self.historial) - 1:
      self.btn_rehacer.config(state=tk.NORMAL)
      self.menu_editar.entryconfig("Rehacer", state=tk.NORMAL)
    else:
      self.btn_rehacer.config(state=tk.DISABLED)
      self.menu_editar.entryconfig("Rehacer", state=tk.DISABLED)

  def deshacer(self):
    if self.indice_historial > 0:
      self.indice_historial -= 1
      self.imagen_procesada = self.historial[self.indice_historial].copy()
      self.resetear_sliders_silencioso()
      self.actualizar_vista()
      self.actualizar_estado_botones()

  def rehacer(self):
    if self.indice_historial < len(self.historial) - 1:
      self.indice_historial += 1
      self.imagen_procesada = self.historial[self.indice_historial].copy()
      self.resetear_sliders_silencioso()
      self.actualizar_vista()
      self.actualizar_estado_botones()

  def resetear_sliders_silencioso(self):
    self.slider_brillo.set(1.0)
    self.slider_contraste.set(1.0)
    self.slider_saturacion.set(1.0)
    self.btn_confirmar_ajustes.config(state=tk.DISABLED)
    self.btn_cancelar_ajustes.config(state=tk.DISABLED)

  def previsualizar_accion(self, nombre_accion, imagen_resultado):
    if self.imagen_procesada is None:
      return

    ventana_preview = tk.Toplevel(self.root)
    ventana_preview.title(f"Vista Previa - {nombre_accion}")
    ventana_preview.geometry("850x500")
    ventana_preview.grab_set()

    frame_imgs = ttk.Frame(ventana_preview)
    frame_imgs.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    frame_antes = ttk.LabelFrame(frame_imgs, text="Antes (Original actual)")
    frame_antes.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
    lbl_antes = ttk.Label(frame_antes)
    lbl_antes.pack(fill=tk.BOTH, expand=True)

    frame_despues = ttk.LabelFrame(
        frame_imgs, text=f"Después ({nombre_accion})"
    )
    frame_despues.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
    lbl_despues = ttk.Label(frame_despues)
    lbl_despues.pack(fill=tk.BOTH, expand=True)

    img_a = self.imagen_procesada.copy()
    img_a.thumbnail((380, 380))
    tk_a = ImageTk.PhotoImage(img_a)
    lbl_antes.config(image=tk_a)
    lbl_antes.image = tk_a

    img_d = imagen_resultado.copy()
    img_d.thumbnail((380, 380))
    tk_d = ImageTk.PhotoImage(img_d)
    lbl_despues.config(image=tk_d)
    lbl_despues.image = tk_d

    frame_botones = ttk.Frame(ventana_preview, padding=10)
    frame_botones.pack(fill=tk.X)

    def confirmar():
      self.registrar_cambio(imagen_resultado)
      ventana_preview.destroy()

    ttk.Button(frame_botones, text="✔ Confirmar", command=confirmar).pack(
        side=tk.LEFT, expand=True, fill=tk.X, padx=10
    )
    ttk.Button(
        frame_botones,
        text="✖ Cancelar",
        command=ventana_preview.destroy,
    ).pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=10)

  def aplicar_negativo_con_preview(self):
    if self.imagen_procesada is None:
      return
    modo_original = self.imagen_procesada.mode
    if modo_original == "RGBA":
      r, g, b, a = self.imagen_procesada.split()
      rgb_inv = ImageOps.invert(Image.merge("RGB", (r, g, b)))
      r_i, g_i, b_i = rgb_inv.split()
      img_neg = Image.merge("RGBA", (r_i, g_i, b_i, a))
    else:
      img_rgb = self.imagen_procesada.convert("RGB")
      img_neg = ImageOps.invert(img_rgb)
      if modo_original == "L":
        img_neg = img_neg.convert("L")
    self.previsualizar_accion("Negativo", img_neg)

  def en_cambio_slider(self, val):
    if self.imagen_procesada is None:
      return

    brillo = self.slider_brillo.get()
    contraste = self.slider_contraste.get()
    saturacion = self.slider_saturacion.get()

    self.btn_confirmar_ajustes.config(state=tk.NORMAL)
    self.btn_cancelar_ajustes.config(state=tk.NORMAL)

    base = self.historial[self.indice_historial]
    img_temp = ImageEnhance.Brightness(base).enhance(brillo)
    img_temp = ImageEnhance.Contrast(img_temp).enhance(contraste)
    img_temp = ImageEnhance.Color(img_temp).enhance(saturacion)

    self.imagen_procesada = img_temp
    self.actualizar_vista()

  def confirmar_ajustes(self):
    if self.imagen_procesada:
      self.registrar_cambio(self.imagen_procesada)
      self.resetear_sliders_silencioso()
      messagebox.showinfo(
          "Éxito", "Ajustes de brillo, contraste y saturación aplicados."
      )

  def cancelar_ajustes(self):
    self.imagen_procesada = self.historial[self.indice_historial].copy()
    self.resetear_sliders_silencioso()
    self.actualizar_vista()

  def alternar_modo_recorte(self):
    self.recortando = not self.recortando
    if self.recortando:
      self.lbl_modo.config(
          text="[Modo Recorte Activo: Arrastre el mouse sobre la imagen]"
      )
      messagebox.showinfo(
          "Modo Recorte",
          "Haga clic y arrastre el mouse sobre la imagen para seleccionar el"
          " área a recortar.",
      )
    else:
      self.lbl_modo.config(text="")
      if self.rect_id:
        self.canvas_imagen.delete(self.rect_id)
        self.rect_id = None

  def on_mouse_press(self, event):
    if not self.recortando or self.imagen_procesada is None:
      return
    self.inicio_x = event.x
    self.inicio_y = event.y
    if self.rect_id:
      self.canvas_imagen.delete(self.rect_id)
    self.rect_id = self.canvas_imagen.create_rectangle(
        self.inicio_x,
        self.inicio_y,
        self.inicio_x,
        self.inicio_y,
        outline="red",
        width=2,
        dash=(4, 4),
    )

  def on_mouse_drag(self, event):
    if not self.recortando or not self.rect_id:
      return
    self.canvas_imagen.coords(
        self.rect_id, self.inicio_x, self.inicio_y, event.x, event.y
    )

  def on_mouse_release(self, event):
    if not self.recortando or not self.rect_id:
      return
    fin_x, fin_y = event.x, event.y

    x1 = min(self.inicio_x, fin_x) - self.pos_x
    y1 = min(self.inicio_y, fin_y) - self.pos_y
    x2 = max(self.inicio_x, fin_x) - self.pos_x
    y2 = max(self.inicio_y, fin_y) - self.pos_y

    self.canvas_imagen.delete(self.rect_id)
    self.rect_id = None
    self.recortando = False
    self.lbl_modo.config(text="")

    w_orig, h_orig = self.imagen_procesada.size
    factor_escala = w_orig / self.img_width
    rx1 = int(max(0, x1 * factor_escala))
    ry1 = int(max(0, y1 * factor_escala))
    rx2 = int(min(w_orig, x2 * factor_escala))
    ry2 = int(min(h_orig, y2 * factor_escala))

    if rx2 - rx1 > 10 and ry2 - ry1 > 10:
      img_recortada = self.imagen_procesada.crop((rx1, ry1, rx2, ry2))
      self.previsualizar_accion("Recortar Imagen", img_recortada)
    else:
      messagebox.showwarning(
          "Advertencia", "El área seleccionada es demasiado pequeña."
      )

  def recortar_por_coordenadas(self):
    if self.imagen_procesada is None:
      messagebox.showwarning("Advertencia", "No hay imagen cargada.")
      return

    w, h = self.imagen_procesada.size
    coords = simpledialog.askstring(
        "Recortar por coordenadas",
        f"Ingrese las coordenadas (x1,y1,x2,y2)\nTamaño actual: {w}x{h}:",
        initialvalue=f"0,0,{w},{h}",
    )
    if not coords:
      return

    try:
      partes = [int(p.strip()) for p in coords.split(",")]
      if len(partes) != 4:
        raise ValueError("Deben ser 4 valores.")
      x1, y1, x2, y2 = partes
      if x1 >= x2 or y1 >= y2 or x1 < 0 or y1 < 0 or x2 > w or y2 > h:
        raise ValueError("Coordenadas fuera de rango o inválidas.")

      img_recortada = self.imagen_procesada.crop((x1, y1, x2, y2))
      self.previsualizar_accion("Recortar por Coordenadas", img_recortada)
    except Exception as e:
      messagebox.showerror(
          "Error",
          (
              "Formato de coordenadas inválido.\nUse números enteros separados"
              f" por comas.\nDetalle: {e}"
          ),
      )

  def abrir_imagen(self):
    tipos_archivo = [
        ("Archivos de Imagen", "*.jpg *.jpeg *.png *.bmp"),
        ("Todos los archivos", "*.*"),
    ]
    ruta = filedialog.askopenfilename(
        title="Seleccionar imagen", filetypes=tipos_archivo
    )

    if not ruta:
      return

    try:
      img = Image.open(ruta)
      img.verify()

      self.imagen_original = Image.open(ruta)
      self.imagen_procesada = self.imagen_original.copy()
      self.ruta_actual = ruta

      self.historial = [self.imagen_procesada.copy()]
      self.indice_historial = 0
      self.resetear_sliders_silencioso()

      self.actualizar_vista()
      self.actualizar_estado_botones()
    except Exception as e:
      messagebox.showerror(
          "Error al abrir",
          (
              "El archivo seleccionado no es una imagen válida o está"
              f" corrupto.\nDetalle: {e}"
          ),
      )

  def guardar_como(self):
    if self.imagen_procesada is None:
      messagebox.showwarning(
          "Advertencia", "No hay ninguna imagen procesada para guardar."
      )
      return

    ruta = filedialog.asksaveasfilename(
        defaultextension=".png",
        filetypes=[
            ("PNG", "*.png"),
            ("JPEG", "*.jpg"),
            ("BMP", "*.bmp"),
            ("Todos los archivos", "*.*"),
        ],
    )

    if not ruta:
      return

    try:
      extension = os.path.splitext(ruta)[1].lower()
      if extension in [".jpg", ".jpeg"] and self.imagen_procesada.mode in (
          "RGBA",
          "LA",
      ):
        imagen_a_guardar = Image.new(
            "RGB", self.imagen_procesada.size, (255, 255, 255)
        )
        imagen_a_guardar.paste(
            self.imagen_procesada,
            mask=self.imagen_procesada.split()[3]
            if self.imagen_procesada.mode == "RGBA"
            else None,
        )
      else:
        imagen_a_guardar = self.imagen_procesada

      imagen_a_guardar.save(ruta)
      messagebox.showinfo("Éxito", "Imagen guardada correctamente.")
    except Exception as e:
      messagebox.showerror(
          "Error", f"No se pudo guardar la imagen.\nDetalle: {e}"
      )

  # --- 3.9 / ENVÍO DE CORREO ESTÉTICO CON VALIDACIÓN Y LÍMITE DE 25 MB ---
  def abrir_ventana_correo(self):
    if self.imagen_procesada is None:
      messagebox.showwarning(
          "Advertencia", "No hay ninguna imagen para enviar por correo."
      )
      return

    # Ventana con diseño estético Coquette provisto
    ventana_mail = tk.Toplevel(self.root)
    ventana_mail.title("✨ APLICACIÓN DE MENSAJERIA ✨")
    ventana_mail.geometry("390x610")
    ventana_mail.resizable(0, 0)

    BG_COLOR = "#fff0f3"
    ACCENT_PINK = "#ffb3c6"
    TEXT_COLOR = "#785964"
    WHITE = "#ffffff"
    INPUT_BG = "#fff9fb"

    ventana_mail.config(bd=12, bg=BG_COLOR)

    MI_CORREO = "cuentaotradeotra@gmail.com"
    MI_CLAVE = "ljzs vndb hxar rizm"

    tk.Label(
        ventana_mail,
        text="💌 ENVIAR CORREO 💌",
        fg=TEXT_COLOR,
        bg=BG_COLOR,
        font=("Helvetica", 14, "bold"),
        padx=5,
        pady=2,
    ).grid(row=0, column=0, columnspan=2)

    # Imagen / Logo decorativo
    try:
      imagen_gmail = Image.open("logo_uwu.jpg")
      nueva_imagen = imagen_gmail.resize((110, 80))
      render = ImageTk.PhotoImage(nueva_imagen)
      label_imagen = tk.Label(ventana_mail, image=render, bg=BG_COLOR)
      label_imagen.image = render
      label_imagen.grid(row=1, column=0, columnspan=2, pady=10)
    except Exception:
      tk.Label(
          ventana_mail,
          text="୨ৎ",
          fg=ACCENT_PINK,
          bg=BG_COLOR,
          font=("Helvetica", 20),
      ).grid(row=1, column=0, columnspan=2, pady=10)

    # Tarjeta de correo remitente
    correo_frame = tk.Frame(ventana_mail, bg=ACCENT_PINK, bd=0)
    correo_frame.grid(row=2, column=0, columnspan=2, pady=5, sticky="ew")
    tk.Label(
        correo_frame,
        text=f"♡ Mi correo: {MI_CORREO} ♡",
        fg=WHITE,
        bg=ACCENT_PINK,
        font=("Helvetica", 9, "bold"),
        padx=10,
        pady=6,
    ).pack()

    destinatario = tk.StringVar(ventana_mail)
    asunto = tk.StringVar(ventana_mail, value="Imagen Procesada - Trabajo Práctico")
    opcion_seleccionada = tk.StringVar(ventana_mail)

    lista_correos = [
        "Seleccionar contacto...",
        "fjcoronati@gmail.com",
        "mfedullo@gmail.com",
        "lafortaleza246@gmail.com",
        "Katsukibakugouteamo20@gmail.com",
    ]
    opcion_seleccionada.set(lista_correos[0])

    def actualizar_destinatario(*args):
      seleccion = opcion_seleccionada.get()
      if seleccion != "Seleccionar contacto...":
        destinatario.set(seleccion)

    opcion_seleccionada.trace("w", actualizar_destinatario)

    label_font = ("Helvetica", 9, "bold")
    entry_font = ("Helvetica", 10)

    tk.Label(
        ventana_mail,
        text="Contactos:",
        fg=TEXT_COLOR,
        bg=BG_COLOR,
        font=label_font,
    ).grid(row=3, column=0, sticky="e", pady=8, padx=5)

    opt_menu = tk.OptionMenu(
        ventana_mail, opcion_seleccionada, *lista_correos
    )
    opt_menu.config(
        bg=WHITE,
        fg=TEXT_COLOR,
        activebackground=ACCENT_PINK,
        activeforeground=WHITE,
        font=("Helvetica", 9),
        highlightthickness=0,
        bd=1,
        relief="solid",
    )
    opt_menu["menu"].config(bg=WHITE, fg=TEXT_COLOR, font=("Helvetica", 9))
    opt_menu.grid(row=3, column=1, sticky="ew", pady=8)

    tk.Label(
        ventana_mail,
        text="Destinatario:",
        fg=TEXT_COLOR,
        bg=BG_COLOR,
        font=label_font,
    ).grid(row=4, column=0, sticky="e", pady=8, padx=5)
    entry_dest = tk.Entry(
        ventana_mail,
        textvariable=destinatario,
        width=28,
        bg=INPUT_BG,
        fg=TEXT_COLOR,
        font=entry_font,
        bd=1,
        relief="solid",
        highlightcolor=ACCENT_PINK,
    )
    entry_dest.grid(row=4, column=1, pady=8, ipady=3, sticky="w")

    tk.Label(
        ventana_mail, text="Asunto:", fg=TEXT_COLOR, bg=BG_COLOR, font=label_font
    ).grid(row=5, column=0, sticky="e", pady=8, padx=5)
    entry_asunto = tk.Entry(
        ventana_mail,
        textvariable=asunto,
        width=28,
        bg=INPUT_BG,
        fg=TEXT_COLOR,
        font=entry_font,
        bd=1,
        relief="solid",
        highlightcolor=ACCENT_PINK,
    )
    entry_asunto.grid(row=5, column=1, pady=8, ipady=3, sticky="w")

    tk.Label(
        ventana_mail,
        text="Mensaje:",
        fg=TEXT_COLOR,
        bg=BG_COLOR,
        font=label_font,
    ).grid(row=6, column=0, sticky="ne", pady=8, padx=5)
    mensaje_txt = tk.Text(
        ventana_mail,
        height=5,
        width=26,
        padx=8,
        pady=8,
        bg=INPUT_BG,
        fg=TEXT_COLOR,
        font=("Helvetica", 9),
        bd=1,
        relief="solid",
    )
    mensaje_txt.insert(
        "1.0", "Hola, adjunto la imagen procesada en la aplicación."
    )
    mensaje_txt.grid(row=6, column=1, pady=8, sticky="w")

    def validar_email(email_str):
      # Expresión regular estándar para formato de correo válido
      patron = r"^[\w\.-]+@[\w\.-]+\.\w+$"
      return re.match(patron, email_str) is not None

    def enviar_email():
      dest_val = destinatario.get().strip()

      # Validación obligatoria de selección o formato de email
      if dest_val == "" or dest_val == "Seleccionar contacto...":
        messagebox.showwarning(
            "Atención 💌", "Por favor, ingresa o selecciona un destinatario."
        )
        return

      if not validar_email(dest_val):
        messagebox.showerror(
            "Error de formato ❌",
            "La dirección de correo electrónico no tiene un formato válido.",
        )
        return

      try:
        # Guardar imagen temporalmente para evaluación de peso
        temp_filename = "temp_envio_imagen.jpg"
        
        # Manejar transparencia si la hay al guardar en JPEG
        img_a_enviar = self.imagen_procesada
        if img_a_enviar.mode in ("RGBA", "LA"):
          background = Image.new("RGB", img_a_enviar.size, (255, 255, 255))
          background.paste(
              img_a_enviar,
              mask=img_a_enviar.split()[3]
              if img_a_enviar.mode == "RGBA"
              else None,
          )
          img_a_enviar = background
        else:
          img_a_enviar = img_a_enviar.convert("RGB")

        # Guardar con calidad inicial alta (95)
        calidad = 95
        img_a_enviar.save(temp_filename, "JPEG", quality=calidad)

        # Criterio de los 25 MB considerando la codificación Base64 (~33% más de tamaño en bytes)
        LIMITE_BYTES = 25 * 1024 * 1024  # 25 MB
        
        # Bucle de compresión si el tamaño codificado supera los 25 MB
        while os.path.getsize(temp_filename) * 1.35 > LIMITE_BYTES and calidad > 10:
          calidad -= 10
          img_a_enviar.save(temp_filename, "JPEG", quality=calidad)

        # Si aún es muy pesado, reducir dimensiones de la imagen
        while os.path.getsize(temp_filename) * 1.35 > LIMITE_BYTES:
          w, h = img_a_enviar.size
          img_a_enviar = img_a_enviar.resize((int(w * 0.8), int(h * 0.8)), Image.Resampling.LANCZOS)
          img_a_enviar.save(temp_filename, "JPEG", quality=calidad)

        peso_final_mb = (os.path.getsize(temp_filename) * 1.35) / (1024 * 1024)
        if peso_final_mb > 24:
          messagebox.showwarning(
              "Aviso de Compresión 📦",
              "La imagen fue comprimida automáticamente para no superar el límite de 25 MB de los servidores de correo.",
          )

        # Armar mensaje MIME
        email = EmailMessage()
        email["From"] = MI_CORREO
        email["To"] = dest_val
        email["Subject"] = asunto.get()
        email.set_content(str(mensaje_txt.get("1.0", "end").strip()))

        with open(temp_filename, "rb") as f:
          file_data = f.read()
          file_name = "imagen_procesada.jpg"
        
        email.add_attachment(
            file_data,
            maintype="image",
            subtype="jpeg",
            filename=file_name,
        )

        # Envío seguro mediante smtplib
        smtp = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        smtp.login(MI_CORREO, MI_CLAVE)
        smtp.sendmail(MI_CORREO, dest_val, email.as_string())
        smtp.quit()

        # Limpiar archivo temporal
        if os.path.exists(temp_filename):
          os.remove(temp_filename)

        messagebox.showinfo(
            "¡Éxito! 🎀", "Mensaje con imagen adjunta enviado correctamente ✨"
        )
        ventana_mail.destroy()

      except smtplib.SMTPAuthenticationError:
        messagebox.showerror(
            "Error de Inicio",
            "Fallo de autenticación. Verifica tu contraseña de aplicación de Gmail.",
        )
      except Exception as e:
        messagebox.showerror("Error", f"Ocurrió un error al enviar: {e}")

    btn_enviar = tk.Button(
        ventana_mail,
        text="ENVIAR 🎀",
        command=enviar_email,
        height=1,
        width=14,
        bg=ACCENT_PINK,
        fg=WHITE,
        font=("Helvetica", 10, "bold"),
        bd=0,
        activebackground="#ff8fab",
        activeforeground=WHITE,
        cursor="hand2",
    )
    btn_enviar.grid(row=7, column=0, columnspan=2, padx=5, pady=12)


if __name__ == "__main__":
  root = tk.Tk()
  app = VisorEditorApp(root)
  root.mainloop()