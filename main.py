import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw

current_pil_img = None  # immagine PIL (ridimensionata) mantenuta in memoria
images_refs = []  # per evitare garbage collection delle PhotoImage

def create_overlay_and_composite(pil_img, rows, cols, border_pct):
    # pil_img: PIL Image in modalità RGB o RGBA
    try:
        rows = max(1, int(rows))
        cols = max(1, int(cols))
        border_pct = max(0.0, float(border_pct))
    except Exception:
        return pil_img

    img_w, img_h = pil_img.size
    cell_w = img_w / cols
    cell_h = img_h / rows
    extra_w = int(cell_w * (border_pct / 100.0))
    extra_h = int(cell_h * (border_pct / 100.0))

    overlay = Image.new("RGBA", (img_w + 2 * extra_w, img_h + 2 * extra_h), (0,0,0,0))
    draw = ImageDraw.Draw(overlay)

    src = pil_img.convert("RGBA")
    overlay.paste(src, (extra_w, extra_h))
    pil_img = overlay
    
    base = pil_img.convert("RGBA")
    base_w, base_h = base.size

    inline = (255, 0, 0, 255)  # colore bordo con alpha maggiore
    outline = (0, 0, 255, 255)  # colore bordo con alpha maggiore

    # crea finestra e frame per le immagini
    top = tk.Toplevel(root)
    top.title("Celle ricomposte")
    frame = tk.Frame(top, bg='white')
    frame.pack(padx=10, pady=10)


    for r in range(rows):
        for c in range(cols):
            left = extra_w + int(c * cell_w)
            top = extra_h + int(r * cell_h)
            right = extra_w + int((c + 1) * cell_w)
            bottom = extra_h + int((r + 1) * cell_h)
            # disegna rettangolo interno
            draw.rectangle([left, top, right, bottom], outline=inline)
            
            left_ext = left - extra_w
            top_ext = top - extra_h
            right_ext = right + extra_w
            bottom_ext = bottom + extra_h
            # disegna rettangolo esterno
            draw.rectangle([left_ext, top_ext, right_ext, bottom_ext], outline=outline)          

            # dimensione desiderata per la cella BLU
            w = right_ext - left_ext
            h = bottom_ext - top_ext
   
            # calcola area effettivamente presente nell'immagine
            crop_l = max(0, left_ext)
            crop_t = max(0, top_ext)
            crop_r = min(base_w, right_ext)
            crop_b = min(base_h, bottom_ext)

            # ritaglio della porzione disponibile
            cropped = base.crop((crop_l, crop_t, crop_r, crop_b))

            # crea sempre una tile delle dimensioni richieste con sfondo bianco
            tile = Image.new("RGBA", (w, h), (255, 255, 255, 255))
             # usa il canale alpha come mask se presente
            if cropped.mode == "RGBA":
                tile.paste(cropped, (0, 0), cropped)
            else:
                tile.paste(cropped, (0, 0))

            tk_tile = ImageTk.PhotoImage(tile)
            lbl = tk.Label(frame, image=tk_tile, bd=1, relief='solid')
            lbl.grid(row=r, column=c)
            images_refs.append(tk_tile)

    composite = Image.alpha_composite(base, overlay)
    return composite

def display_image_with_overlay():
    global current_pil_img
    if current_pil_img is None:
        return
    rows = entry_rows.get()
    cols = entry_cols.get()
    border_pct = entry_border.get()
    composite = create_overlay_and_composite(current_pil_img, rows, cols, border_pct)
    tk_img = ImageTk.PhotoImage(composite)
    canvas.config(width=tk_img.width(), height=tk_img.height())
    canvas.delete('all')
    canvas.create_image(0, 0, anchor='nw', image=tk_img, tags='img')
    canvas.image = tk_img  # mantieni riferimento

def open_and_show_image():
    global current_pil_img
    path = filedialog.askopenfilename(
        title="Scegli un'immagine",
        filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.bmp;*.gif"), ("All files", "*.*")]
    )
    if not path:
        return
    try:
        img = Image.open(path)
    except Exception as e:
        messagebox.showerror("Errore", f"Impossibile aprire l'immagine:\n{e}")
        return

    # ridimensiona per adattare alla finestra (max 800x600)
    max_w, max_h = 800, 600
    img.thumbnail((max_w, max_h), Image.LANCZOS)
    current_pil_img = img.copy()
    display_image_with_overlay()

root = tk.Tk()
root.title("Visualizzatore immagine")
root.resizable(False, False)

# Controlli: pulsante + campi N (righe), M (colonne) e bordo (%)
ctrl_frame = tk.Frame(root)
ctrl_frame.pack(padx=10, pady=10, anchor='w')

btn = tk.Button(ctrl_frame, text="Apri immagine...", command=open_and_show_image)
btn.grid(row=0, column=0, padx=(0,8))

tk.Label(ctrl_frame, text="Righe (N):").grid(row=0, column=1, sticky='e')
entry_rows = tk.Entry(ctrl_frame, width=5)
entry_rows.insert(0, "2")
entry_rows.grid(row=0, column=2, padx=(4,12))

tk.Label(ctrl_frame, text="Colonne (M):").grid(row=0, column=3, sticky='e')
entry_cols = tk.Entry(ctrl_frame, width=5)
entry_cols.insert(0, "2")
entry_cols.grid(row=0, column=4, padx=(4,8))

tk.Label(ctrl_frame, text="Bordo (%):").grid(row=0, column=5, sticky='e')
entry_border = tk.Entry(ctrl_frame, width=6)
entry_border.insert(0, "20")
entry_border.grid(row=0, column=6, padx=(4,8))

# bottone per aggiornare la sovrapposizione senza riaprire immagine
def update_grid():
    if hasattr(canvas, 'image') or current_pil_img is not None:
        display_image_with_overlay()

update_btn = tk.Button(ctrl_frame, text="Aggiorna", command=update_grid)
update_btn.grid(row=0, column=7, padx=(8,0))


# --- nuova funzione: ricomponi le celle in una nuova finestra ---
def compose_cells_window():
    # crea finestra solo se abbiamo immagine corrente
    if current_pil_img is None:
        messagebox.showinfo("Info", "Apri prima un'immagine.")
        return

    try:
        rows = max(1, int(entry_rows.get()))
        cols = max(1, int(entry_cols.get()))
        border_pct = max(0.0, float(entry_border.get()))
    except Exception:
        messagebox.showerror("Errore", "Valori N, M o Bordo non validi.")
        return

    img = current_pil_img.convert("RGBA")
    img_w, img_h = img.size
    cell_w = img_w / cols
    cell_h = img_h / rows
    extra_w = cell_w * (border_pct / 100.0)
    extra_h = cell_h * (border_pct / 100.0)

    # crea finestra e frame per le immagini
    top = tk.Toplevel(root)
    top.title("Celle ricomposte")
    frame = tk.Frame(top, bg='white')
    frame.pack(padx=10, pady=10)

    images_refs = []  # per evitare garbage collection delle PhotoImage

    outline = (0, 0, 255, 255)  # colore bordo con alpha maggiore

    for r in range(rows):
        for c in range(cols):
            left = int(c * cell_w)
            top = int(r * cell_h)
            right =  int((c + 1) * cell_w)
            bottom = int((r + 1) * cell_h)
            
            # disegna bordo esterno
            draw.rectangle([left - extra_w, top - extra_h, right + extra_w, bottom + extra_h], outline=outline)

    for r in range(rows):
        for c in range(cols):
            # coordinate float -> int
            left = int(round(c * cell_w - extra_w))
            top = int(round(r * cell_h - extra_h))
            right = int(round((c + 1) * cell_w + extra_w))
            bottom = int(round((r + 1) * cell_h + extra_h))

            # dimensione desiderata per la cella
            w = right - left
            h = bottom - top
            if w <= 0 or h <= 0:
                tile = Image.new("RGBA", (1,1), (255,255,255,255))
            else:
                # calcola area effettivamente presente nell'immagine
                crop_l = max(0, left)
                crop_t = max(0, top)
                crop_r = min(img_w, right)
                crop_b = min(img_h, bottom)

                # ritaglio della porzione disponibile
                cropped = img.crop((crop_l, crop_t, crop_r, crop_b))

                # crea sempre una tile delle dimensioni richieste con sfondo bianco
                tile = Image.new("RGBA", (w, h), (255, 255, 255, 255))
                paste_x = crop_l - left
                paste_y = crop_t - top
                # usa il canale alpha come mask se presente
                if cropped.mode == "RGBA":
                    tile.paste(cropped, (paste_x, paste_y), cropped)
                else:
                    tile.paste(cropped, (paste_x, paste_y))

            # disegna bordo blu attorno alla tile per evidenziare l'outline
            draw = ImageDraw.Draw(tile)
            draw.rectangle([0, 0, tile.width, tile.height], outline=(0, 0, 255, 255))

            tk_tile = ImageTk.PhotoImage(tile)
            lbl = tk.Label(frame, image=tk_tile, bd=1, relief='solid')
            lbl.grid(row=r, column=c)
            images_refs.append(tk_tile)

    # tieni i riferimenti sull'oggetto finestra per evitare GC
    top.images = images_refs

# Canvas per mostrare l'immagine e l'overlay
canvas = tk.Canvas(root, bg='gray')
canvas.pack(padx=10, pady=(0,10))

# Apri dialog all'avvio (opzionale)
root.after(100, open_and_show_image)

root.mainloop()
# ...existing code...