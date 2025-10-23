import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw
from pathcreator import init_params, gen_dh, gen_dv, gen_db
import os
import sys
import io

current_pil_img_full = None      # immagine PIL in dimensione originale, usata per l'elaborazione
current_pil_img_display = None   # immagine PIL ridotta, usata solo per la visualizzazione
images_refs = []  # per evitare garbage collection delle PhotoImage
PREVIEW_WINDOW = False  # se True apre una finestra separata per le celle

def mask_other_cells(pil_img, tot_rows, tot_cols, row, col, paths_h, paths_v):
    
    img_w, img_h = pil_img.size

      # Crea immagine finale oscurata
    darkened = Image.new("RGBA", (img_w, img_h), (255, 255, 255, 255))  # Sfondo bianco
    mask = Image.new("L", (img_w, img_h), 0)  # Maschera nera (opaca)
    mask_draw = ImageDraw.Draw(mask)

    # Crea un poligono che copre l'area a destra del percorso
    contour = []

    # bisogna ricordarsi di girare in senso orario. 
    # Ricordarsi inoltre che i path_v sono in un array monodimensionale di colonne
    # e i path_h sono in un array monodimensionale di righe
    
    # Aggiungi i punti del percorso. Il percorso 0 verticale è a destra in alto della riga 0 e così via
    
    # tratto verticale a destra verso il basso
    if col < tot_cols - 1:
        contour.extend(paths_v[row + col * tot_rows])  # Seguo il percorso verticale destro scendendo
    else: 
        # caso ultima colonna
        if row == 0:
            contour.append((img_w, 0))  # Angolo in alto a destra dell'immagine
        elif row < tot_rows - 1:
            contour.append(paths_h[col + (row - 1) * tot_cols][::-1][0])  # Angolo in alto a destra della riga superiore
        else:
            contour.append((img_w, img_h))  # Angolo in basso a destra dell'immagine

    # tratto orizzontale inferiore all'indietro
    if row < tot_rows - 1:
        contour.extend(paths_h[col + row * tot_cols][::-1])  # Seguo il percorso orizzontale inferiore
    else:  # caso ultima riga
        if col == 0:
            contour.append((0, img_h))  # Angolo in basso a sinistra dell'immagine
        else:        
            contour.append(paths_v[row + (col -1) * tot_rows][::-1][0])  

    # tratto verticale a sinistra verso l'alto
    if col > 0:
        contour.extend(paths_v[row + (col -1) * tot_rows][::-1])  # Seguo il percorso verticale sinistro risalendo
    else:
        if row == 0:
            contour.append((0, 0))  # Angolo in alto a sinistra dell'immagine
        else:
            contour.append(paths_h[(row -1) * tot_cols][0])  # Angolo in alto a sinistra della riga superiore
    
    # tratto orizzontale superiore in avanti
    if row > 0:
        contour.extend(paths_h[col + (row -1) * tot_cols])  # Seguo il percorso orizzontale superiore
    else:   
        contour.append(contour[0])
    
    # Aggiungi il primo punto del percorso per chiudere di sicuro il poligono
    contour.append(contour[0])
    
    # print(f"Contour points for {col} {row}:")
    # print(contour)

    mask_draw.polygon(contour, fill=255)  # Bianco = trasparente

    # Incolla l'immagine composita usando la maschera
    darkened.paste(pil_img, (0, 0), mask)

    return darkened

def save_jpeg_bytes(base_dir, jpeg_bytes, name="puzzle.jpg"):
    out_path = os.path.join(base_dir, name)

    # try to save; on permission error, fallback to user's Pictures (or home) and retry
    try:
        with open(out_path, "wb") as f:
            f.write(jpeg_bytes)
    except Exception:
        fallback_dir = os.path.join(os.path.expanduser("~"), "Pictures")
        try:
            os.makedirs(fallback_dir, exist_ok=True)
        except Exception:
            fallback_dir = os.path.expanduser("~")
        out_path = os.path.join(fallback_dir, name)
        with open(out_path, "wb") as f:
            f.write(jpeg_bytes)

def save_final_image_for_cutting(grid_img):

    # determina cartella di uscita robusta per eseguibile e per script
    if getattr(sys, "frozen", False):
        # quando PyInstaller crea l'exe, sys.executable punta all'eseguibile
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    # JPEG save options: highest quality, no chroma subsampling, progressive, force 320 PPI
    quality = 100
    subsampling = 0
    progressive = True
    optimize = True
    dpi = (320, 320)

    # crea buffer JPEG in memoria (con DPI)
    buf = io.BytesIO()
    grid_img.save(buf, "JPEG",
                  quality=quality,
                  subsampling=subsampling,
                  progressive=progressive,
                  optimize=optimize,
                  dpi=dpi)
    buf.seek(0)
    jpeg_bytes = buf.getvalue()

    save_jpeg_bytes(base_dir, jpeg_bytes, "puzzle_full.jpg")
    img_320ppi = Image.open(io.BytesIO(jpeg_bytes)) 

    # sapendo quanto è grosso un pezzo di puzzle, suddividi l'immagine in fogli A4
    img_w, img_h = img_320ppi.size
    a4_w, a4_h = 2480, 3508  # dimensioni A4 a 320 PPI    

    rows = int(entry_rows.get())
    cols = int(entry_cols.get())

    dim_x_casella = img_w // cols
    dim_y_casella = img_h // rows

    # il numero di pagine dipende dal massimo valore di caselle che possono stare in una pagina A4
    max_x_caselle_per_pagina = a4_w // dim_x_casella
    max_y_caselle_per_pagina = a4_h // dim_y_casella

    num_fogli_A4_x = 1 + img_w // (max_x_caselle_per_pagina * dim_x_casella)
    num_fogli_A4_y = 1 + img_h // (max_y_caselle_per_pagina * dim_y_casella)

    # ora per ogni foglio A4 preparo una immagine Pillow con sfondo bianco
    for foglio_x in range(num_fogli_A4_x):
       for foglio_y in range(num_fogli_A4_y):
            page_img = Image.new("RGB", (a4_w, a4_h), (255, 255, 255))
            for py in range(max_y_caselle_per_pagina):
                for px in range(max_x_caselle_per_pagina):
                    src_x = (foglio_x * max_x_caselle_per_pagina * dim_x_casella) +  px * dim_x_casella
                    src_y = (foglio_y * max_y_caselle_per_pagina * dim_y_casella) +  py * dim_y_casella

                    # se esco dai limiti dell'immagine originale, esco
                    if src_x + dim_x_casella > img_w or src_y + dim_y_casella > img_h:
                        continue

                    box = (src_x, src_y, src_x + dim_x_casella, src_y + dim_y_casella)
                    tile = img_320ppi.crop(box)
                    dest_x = px * dim_x_casella
                    dest_y = py * dim_y_casella
                    page_img.paste(tile, (dest_x, dest_y))

            page_path = os.path.join(base_dir, f"puzzle_page_{foglio_x}-{foglio_y}.jpg")
            page_img.save(page_path, "JPEG",
                        quality=quality,
                        subsampling=subsampling,
                        progressive=progressive,
                        optimize=optimize,
                        dpi=dpi)

    messagebox.showinfo("Saved", f"Images saved")   

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

    # Inizializza i parametri per pathcreator
    init_params(cols, rows, img_w, img_h, tabsize=0.7*border_pct, jitter=border_pct/10.0)

    # Applica i percorsi del puzzle
    pil_img, paths_h, paths_v = add_jigsaw_path(pil_img)

    src = pil_img.convert("RGBA")

    #disegna i rettangoli di bordo
    original_overlay = Image.new("RGBA", (img_w + 2 * extra_w, img_h + 2 * extra_h), (0,0,0,0))
    
    overlay = original_overlay.copy()
 
    draw = ImageDraw.Draw(overlay)

    overlay.paste(src, (extra_w, extra_h))
    original_with_borders = overlay.convert("RGBA")
    
    base_w, base_h = original_with_borders.size

    inline = (255, 0, 0, 255)  # colore bordo con alpha maggiore
    outline = (0, 0, 255, 255)  # colore bordo con alpha maggiore

    if PREVIEW_WINDOW:
        # crea finestra e frame per le immagini
        top = tk.Toplevel(root)
        top.title("Tile Preview")
        frame = tk.Frame(top, bg='white')
        frame.pack(padx=10, pady=10)

    # raccolte per costruire l'immagine finale
    tiles_grid = [[None for _ in range(cols)] for _ in range(rows)]
    col_widths = [0] * cols
    row_heights = [0] * rows

    for r in range(rows):
        for c in range(cols):
            left = extra_w + int(c * cell_w)
            top = extra_h + int(r * cell_h)
            right = extra_w + int((c + 1) * cell_w)
            bottom = extra_h + int((r + 1) * cell_h)
            # disegna rettangolo interno
            # draw.rectangle([left, top, right, bottom], outline=inline)
            
            left_ext = left - extra_w
            top_ext = top - extra_h
            right_ext = right + extra_w
            bottom_ext = bottom + extra_h
            # disegna rettangolo esterno
            # draw.rectangle([left_ext, top_ext, right_ext, bottom_ext], outline=outline)          

            # dimensione desiderata per la cella BLU
            w = right_ext - left_ext
            h = bottom_ext - top_ext

            src_masked = mask_other_cells(src, rows, cols, r, c, paths_h, paths_v)

            overlay = original_overlay.copy()

            overlay.paste(src_masked, (extra_w, extra_h))
            base = overlay.convert("RGBA")
            
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

            # salva tile nella griglia e aggiorna dimensioni colonne/righe
            tiles_grid[r][c] = tile
            col_widths[c] = max(col_widths[c], tile.width)
            row_heights[r] = max(row_heights[r], tile.height)
           
            if PREVIEW_WINDOW:
                tk_tile = ImageTk.PhotoImage(tile)
                lbl = tk.Label(frame, image=tk_tile, bd=1, relief='solid')
                lbl.grid(row=r, column=c)
                images_refs.append(tk_tile)

    # costruisci immagine composita della griglia (come appare nella finestra)
    total_w = sum(col_widths)
    total_h = sum(row_heights)
    grid_img = Image.new("RGB", (total_w, total_h), (255,255,255))

    y_off = 0
    for r in range(rows):
        x_off = 0
        for c in range(cols):
            tile = tiles_grid[r][c]
            # converti tile RGBA in RGB su sfondo bianco
            tile_rgb = Image.new("RGB", tile.size, (255,255,255))
            if tile.mode == "RGBA":
                tile_rgb.paste(tile, mask=tile.split()[3])
            else:
                tile_rgb.paste(tile)
            grid_img.paste(tile_rgb, (x_off, y_off))
            x_off += col_widths[c]
        y_off += row_heights[r]

    # salva l'immagine finale
    save_final_image_for_cutting(grid_img)

    return original_with_borders

def add_jigsaw_path(pil_img, draw=False):
    # Crea un'immagine trasparente per l'overlay
    overlay = Image.new('RGBA', (pil_img.width, pil_img.height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    paths_h = gen_dh()
    paths_v = gen_dv()

    # Disegna percorsi orizzontali (nero) e percorsi verticali (rosso)
    if draw:
        for path in paths_h:
            draw.line(path, fill=(0, 0, 0, 255), width=1) 

        for path in paths_v:
            draw.line(path, fill=(0, 0, 0, 255), width=1)

        # Disegna il bordo (nero)
        border_segments = gen_db()
        for segment_type, *args in border_segments:
            if segment_type == "line":
                start, end = args
                draw.line([start, end], fill=(0, 0, 0, 255), width=1)
            elif segment_type == "arc":
                (x0, y0, x1, y1), radius, start_angle, end_angle = args
                draw.arc([x0, y0, x1, y1], start=start_angle, end=end_angle, fill=(0, 0, 0, 255), width=2)

    # Sovrappone l'overlay all'immagine originale
    composite = pil_img.copy()
    composite.paste(overlay, (0, 0), overlay.split()[3])  # Usa il canale alpha
    return composite, paths_h, paths_v

def display_image_with_overlay():
    global current_pil_img_full
    if current_pil_img_full is None:
        return
    rows = entry_rows.get()
    cols = entry_cols.get()
    border_pct = entry_border.get()

    composite_full = create_overlay_and_composite(current_pil_img_full, rows, cols, border_pct)
    
      # scala il composito per la visualizzazione (non modifica l'immagine full)
    max_w, max_h = 800, 600  # dimensione massima visibile (regolabile)
    composite_display = composite_full.copy()
    composite_display.thumbnail((max_w, max_h), Image.LANCZOS)
    current_pil_img_display = composite_display
    
    tk_img = ImageTk.PhotoImage(current_pil_img_display)
    canvas.config(width=tk_img.width(), height=tk_img.height())
    canvas.delete('all')
    canvas.create_image(0, 0, anchor='nw', image=tk_img, tags='img')
    canvas.image = tk_img  # mantieni riferimento

def open_and_show_image():
    global current_pil_img_full, current_pil_img_display
    path = filedialog.askopenfilename(
        title="Choose an image file",
        filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.bmp;*.gif"), ("All files", "*.*")]
    )
    if not path:
        return
    try:
        img = Image.open(path)
    except Exception as e:
        messagebox.showerror("Error", f"Impossible to open:\n{e}")
        return

   # conserva la versione full (converti in RGBA per operazioni con alpha se serve)
    current_pil_img_full = img.convert("RGBA")

    # crea una copia ridotta SOLO per la visualizzazione immediata (opzionale)
    max_w, max_h = 800, 600
    disp = current_pil_img_full.copy()
    disp.thumbnail((max_w, max_h), Image.LANCZOS)
    current_pil_img_display = disp

    display_image_with_overlay()

root = tk.Tk()
root.title("Image Preview with Jigsaw Overlay")
root.resizable(False, False)

# Controlli: pulsante + campi N (righe), M (colonne) e bordo (%)
ctrl_frame = tk.Frame(root)
ctrl_frame.pack(padx=10, pady=10, anchor='w')

btn = tk.Button(ctrl_frame, text="Open Image...", command=open_and_show_image)
btn.grid(row=0, column=0, padx=(0,8))

tk.Label(ctrl_frame, text="Rows:").grid(row=0, column=1, sticky='e')
entry_rows = tk.Entry(ctrl_frame, width=5)
entry_rows.insert(0, "3")
entry_rows.grid(row=0, column=2, padx=(4,12))

tk.Label(ctrl_frame, text="Columns:").grid(row=0, column=3, sticky='e')
entry_cols = tk.Entry(ctrl_frame, width=5)
entry_cols.insert(0, "3")
entry_cols.grid(row=0, column=4, padx=(4,8))

tk.Label(ctrl_frame, text="Border (%):").grid(row=0, column=5, sticky='e')
entry_border = tk.Entry(ctrl_frame, width=6)
entry_border.insert(0, "20")
entry_border.grid(row=0, column=6, padx=(4,8))

# bottone per aggiornare la sovrapposizione senza riaprire immagine
def update_grid():
    if hasattr(canvas, 'image') or current_pil_img_full is not None:
        display_image_with_overlay()

update_btn = tk.Button(ctrl_frame, text="Update", command=update_grid)
update_btn.grid(row=0, column=7, padx=(8,0))

# Canvas per mostrare l'immagine e l'overlay
canvas = tk.Canvas(root, bg='gray')
canvas.pack(padx=10, pady=(0,10))

root.mainloop()
