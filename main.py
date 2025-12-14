import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw, ImageOps
from pathcreator import init_params, gen_dh, gen_dv, gen_db
import os
import sys
import io
import math
import platform

# impostazioni e costanti
A4_TOTAL_W, A4_TOTAL_H = 2646, 3742  # dimensioni A4 a 320 PPI
PREVIEW_WINDOW = False  # se True apre una finestra separata per le celle
GENERATE_MASK_IMAGES = False  # se True genera anche le immagini maschera

# variabili globali
current_pil_img_full = None      # immagine PIL in dimensione originale, usata per l'elaborazione
current_pil_img_display = None   # immagine PIL ridotta, usata solo per la visualizzazione
images_refs = []  # per evitare garbage collection delle PhotoImage

def export_multiple_contours_to_svg(contours, svg_path, canvas_size=(500, 500), stroke="black", fill="none", stroke_width=1):
    with open(svg_path, "w", encoding="utf-8") as f:
        w, h = canvas_size
        f.write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">\n')
        
        # aggiungo un poligono SVG che sia esattamente grosso come il canvas
        f.write(f'  <rect width="{w}" height="{h}" stroke="{stroke}" fill="{fill}" stroke-width="{stroke_width}" />\n')  
        
        for i, contour in enumerate(contours):
            points_str = " ".join(f"{x},{y}" for x, y in contour)
            f.write(f'  <polygon points="{points_str}" stroke="{stroke}" fill="{fill}" stroke-width="{stroke_width}" />\n')
        f.write('</svg>\n')

def mask_other_cells(pil_img, tot_rows, tot_cols, row, col, paths_h, paths_v):
    
    img_w, img_h = pil_img.size

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

    mask_draw.polygon(contour, fill=255)  # 255 = trasparente (è l'alpha)

    white_bg = Image.new("RGBA", (img_w, img_h), (255, 255, 255, 255))  # Sfondo bianco
    black_bg = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 255))  # Sfondo bianco

    # Incolla il background bianco + la maschera sulla immagine originale
    if var_onoff.get():
        white_bg.paste(pil_img, (0, 0), mask)  # creo i pezzi bianchi con sfondo bianco
    else:   
        white_bg.paste(pil_img, (0, 0))

    white_mask = None
    if GENERATE_MASK_IMAGES:
        white_mask = white_bg.copy()
        white_mask.paste(black_bg, (0, 0), mask) # creo i pezzi neri con sfondo bianco...credo

    # prima di tornare indietro il contour, lo shifto a 0.0
    return white_bg, white_mask, contour

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

def get_jpeg_bytes(grid_img, quality=100, subsampling=0, progressive=True, optimize=True, dpi=(320,320)):
     # crea buffer JPEG in memoria (con DPI)
    buf = io.BytesIO()
    grid_img.save(buf, "JPEG",
                  quality=quality,
                  subsampling=subsampling,
                  progressive=progressive,
                  optimize=optimize,
                  dpi=dpi)
    buf.seek(0)
    return buf.getvalue()

def get_base_dir():
    if getattr(sys, 'frozen', False):
        exe_path = os.path.abspath(sys.executable)
        if platform.system() == "Darwin":  # macOS
            # .../PuzzleMaker.app/Contents/MacOS → .../dist
            macos_dir = os.path.dirname(exe_path)         # .../Contents/MacOS
            contents_dir = os.path.dirname(macos_dir)     # .../Contents
            app_root = os.path.dirname(contents_dir)      # .../PuzzleMaker.app
            ext_dir = os.path.dirname(app_root)          # .../dist
            return ext_dir
        else:  # Windows (o Linux con --onefile)
            return os.path.dirname(exe_path)
    else:
        # in sviluppo: usa la cartella corrente
        return os.getcwd()

def save_final_images_for_cutting(grid_img, grid_img_mask, extra_w, extra_h, contours):

    padding_a4 = int(entry_padding.get())

    base_dir = get_base_dir()

    # JPEG save options: highest quality, no chroma subsampling, progressive, force 320 PPI
    quality = 100
    subsampling = 0
    progressive = True
    optimize = True
    dpi = (320, 320)

    jpeg_bytes = get_jpeg_bytes(grid_img, quality, subsampling, progressive, optimize, dpi)
    tutti_pezzi_a_320ppi = Image.open(io.BytesIO(jpeg_bytes)) 
    save_jpeg_bytes(base_dir, jpeg_bytes, "puzzle_full.jpg")

    if GENERATE_MASK_IMAGES:
        jpeg_bytes_mask = get_jpeg_bytes(grid_img_mask, quality, subsampling, progressive, optimize, dpi)
        img_320ppi_mask = Image.open(io.BytesIO(jpeg_bytes_mask)) 

    # sapendo quanto è grosso un pezzo di puzzle, suddividi l'immagine in fogli A4
    tutti_pezzi_w, tutti_pezzi_h = tutti_pezzi_a_320ppi.size

    canvas_w = A4_TOTAL_W - 2* padding_a4 
    canvas_h = A4_TOTAL_H - 2* padding_a4   # dimensioni A4 a 320 PPI    

    rows = int(entry_rows.get())
    cols = int(entry_cols.get())

    dim_x_casella_con_border = int(tutti_pezzi_w / cols)
    dim_y_casella_con_border = int(tutti_pezzi_h  / rows)

    # il numero di pagine dipende dal massimo valore di caselle che possono stare in una pagina A4
    max_x_caselle_per_pagina = canvas_w // dim_x_casella_con_border
    max_y_caselle_per_pagina = canvas_h // dim_y_casella_con_border

    num_fogli_A4_x = math.ceil(cols / max_x_caselle_per_pagina)
    num_fogli_A4_y = math.ceil(rows / max_y_caselle_per_pagina)

    # ora per ogni foglio A4 preparo una immagine Pillow con sfondo bianco
    for foglio_x in range(num_fogli_A4_x):
       for foglio_y in range(num_fogli_A4_y):
            page_img = Image.new("RGB", (A4_TOTAL_W, A4_TOTAL_H), (255, 255, 255))
            
            if GENERATE_MASK_IMAGES:
                page_img_mask = Image.new("RGB", (A4_TOTAL_W, A4_TOTAL_H), (255, 255, 255))
            
            contours_in_page = []
            for py in range(max_y_caselle_per_pagina):
                for px in range(max_x_caselle_per_pagina):

                    # posizione sorgente dall'immagine originale
                    src_x = (foglio_x * max_x_caselle_per_pagina * dim_x_casella_con_border) +  px * dim_x_casella_con_border
                    src_y = (foglio_y * max_y_caselle_per_pagina * dim_y_casella_con_border) +  py * dim_y_casella_con_border

                    if src_x + dim_x_casella_con_border > tutti_pezzi_w or src_y + dim_y_casella_con_border > tutti_pezzi_h:
                        continue
                    
                    # box nell'immagine di partenza. Le coordinate negative escono dall'immagine e creano uno sfondo nero!
                    box = (src_x, src_y, src_x + dim_x_casella_con_border, src_y + dim_y_casella_con_border)

                    # se esco dai limiti dell'immagine originale, il box compensa, spero!
                    tile = tutti_pezzi_a_320ppi.crop(box)

                    dest_x = padding_a4 + px * dim_x_casella_con_border
                    dest_y = padding_a4 + py * dim_y_casella_con_border

                    page_img.paste(tile, (dest_x, dest_y))

                    contour = contours[max_y_caselle_per_pagina * foglio_y + py][max_x_caselle_per_pagina * foglio_x + px]
                    contour = shift_contour(contour, dx= dest_x, dy= dest_y)
                    contours_in_page.append(contour)

                    if GENERATE_MASK_IMAGES:
                        tile_mask = img_320ppi_mask.crop(box)
                        page_img_mask.paste(tile_mask, (dest_x, dest_y))

            export_multiple_contours_to_svg(contours_in_page,
                                        os.path.join(base_dir, f"puzzle_contours_{foglio_x}-{foglio_y}.svg"),
                                        canvas_size=(A4_TOTAL_W, A4_TOTAL_H),
                                        stroke="red",
                                        #fill="rgba(255,0,0,0.2)",  # SVG non supporta rgba direttamente, ma puoi usare `fill-opacity`
                                        stroke_width=1)
            
            page_path = os.path.join(base_dir, f"puzzle_page_{foglio_x}-{foglio_y}.jpg")
            page_img.save(page_path, "JPEG",
                        quality=quality,
                        subsampling=subsampling,
                        progressive=progressive,
                        optimize=optimize,
                        dpi=dpi)
            
            if GENERATE_MASK_IMAGES:
                page_path = os.path.join(base_dir, f"mask_page_{foglio_x}-{foglio_y}.jpg")
                page_img_mask.save(page_path, "JPEG",
                            quality=quality,
                            subsampling=subsampling,
                            progressive=progressive,
                            optimize=optimize,
                            dpi=dpi)
  
    messagebox.showinfo("Saved", f"Images saved")   

def get_tile_with_borders(base_w, base_h, r, c, extra_w, extra_h, cell_w, cell_h, original_overlay, masked):
        
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

    overlay = original_overlay.copy()
    overlay.paste(masked, (extra_w, extra_h))
    
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

    return tile

def shift_contour(contour, dx=0, dy=0):
    return [(x + dx, y + dy) for x, y in contour]

def convert_and_paste_tile(tile_mask, x_off, y_off, grid_img):
    tile_mask_rgb = Image.new("RGB", tile_mask.size, (255,255,255))
    if tile_mask_rgb.mode == "RGBA":
        tile_mask_rgb.paste(tile_mask, mask=tile_mask.split()[3])
    else:
        tile_mask_rgb.paste(tile_mask)  

    grid_img.paste(tile_mask_rgb, (x_off, y_off))

def create_overlay_and_composite(pil_img, rows, cols, tab_pct, border_pct):
    # pil_img: PIL Image in modalità RGB o RGBA

    img_w, img_h = pil_img.size
    cell_w = img_w / cols
    cell_h = img_h / rows
    extra_w = int(cell_w * (border_pct / 100.0))
    extra_h = int(cell_h * (border_pct / 100.0))
    tabsize = tab_pct * border_pct / 100.0 

    # Inizializza i parametri per pathcreator
    init_params(cols, rows, img_w, img_h, tabsize=tabsize, jitter=border_pct/10.0)

    # Applica i percorsi del puzzle
    pil_img, paths_h, paths_v = add_jigsaw_path(pil_img)

    src = pil_img.convert("RGBA")

    #disegna i rettangoli di bordo
    original_overlay = Image.new("RGBA", (img_w + 2 * extra_w, img_h + 2 * extra_h), (0,0,0,0))
    
    overlay = original_overlay.copy()
 
    overlay.paste(src, (extra_w, extra_h))
    original_with_borders = overlay.convert("RGBA")
    
    base_w, base_h = original_with_borders.size

    if PREVIEW_WINDOW:
        # crea finestra e frame per le immagini
        top = tk.Toplevel(root)
        top.title("Tile Preview")
        frame = tk.Frame(top, bg='white')
        frame.pack(padx=10, pady=10)

    # raccolte per costruire l'immagine finale
    tiles_grid = [[None for _ in range(cols)] for _ in range(rows)]
    tiles_grid_for_mask = [[None for _ in range(cols)] for _ in range(rows)]
    contours = [[None for _ in range(cols)] for _ in range(rows)] # per salvare i contorni di tutte le celle in previsione di salvare l'svg

    col_widths = [0] * cols
    row_heights = [0] * rows

    for r in range(rows):
        for c in range(cols):

            src_masked, piece_with_contour, contour = mask_other_cells(src, rows, cols, r, c, paths_h, paths_v)
            
            contours[r][c] = shift_contour(contour, dx= extra_w + -c*cell_w, dy= extra_h + -r*cell_h)

            tile = get_tile_with_borders(base_w, base_h, r, c, extra_w, extra_h, cell_w, cell_h, original_overlay, src_masked)
            tiles_grid[r][c] = tile
            
            if GENERATE_MASK_IMAGES:
                mask_tile = get_tile_with_borders(base_w, base_h, r, c, extra_w, extra_h, cell_w, cell_h, original_overlay, piece_with_contour)
                tiles_grid_for_mask[r][c] = mask_tile

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

    grid_img_mask = None
    if GENERATE_MASK_IMAGES:
        grid_img_mask = Image.new("RGB", (total_w, total_h), (255,255,255))

    y_off = 0
    for r in range(rows):
        x_off = 0
        for c in range(cols):

            convert_and_paste_tile(tiles_grid[r][c], x_off, y_off, grid_img)

            if GENERATE_MASK_IMAGES:
                convert_and_paste_tile(tiles_grid_for_mask[r][c], x_off, y_off, grid_img_mask)

            x_off += col_widths[c]
        y_off += row_heights[r]

    # salva l'immagine finale
    save_final_images_for_cutting(grid_img, grid_img_mask, extra_w, extra_h, contours)

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
 
    return composite, paths_h, paths_v

def display_image_with_overlay():

    # per prima cosa pulisco la cartella da eventuali file jpg e svg precedenti
    
    base_dir = get_base_dir()

    for nome_file in os.listdir(base_dir):
        if nome_file.startswith("puzzle_") and (nome_file.endswith(".svg") or nome_file.endswith(".jpg")):
            percorso_completo = os.path.join(base_dir, nome_file)
            os.remove(percorso_completo)
            # print(f"Cancellato: {percorso_completo}")

    global current_pil_img_full
    if current_pil_img_full is None:
        return
  
    rows = max(1, int(entry_rows.get()))
    cols = max(1, int(entry_cols.get()))
    border_pct = max(0.0, float(entry_border.get()))
    tab = max(10.0, float(entry_tab.get()))
    
    composite_full = create_overlay_and_composite(current_pil_img_full, rows, cols, tab, border_pct)
    
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

    # su mac non esiste il filtro per tipi di file, quindi lo escludo altrimenti tkinter crasha
    filetypes = "" if sys.platform == "darwin" else [("Image files", "*.png;*.jpg;*.jpeg;*.bmp;*.gif"), ("All files", "*.*")]

    path = filedialog.askopenfilename(
        title="Choose an image file",
        filetypes=filetypes
    )
    if not path:
        return
    try:
        img = Image.open(path)
    except Exception as e:
        messagebox.showerror("Error", f"Impossible to open:\n{e}")
        return

    img = ImageOps.exif_transpose(img)  # Corregge l'orientamento secondo EXIF

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

# Frame principale dei controlli
ctrl_frame = tk.Frame(root)
ctrl_frame.pack(padx=10, pady=10, anchor='w')

# --- Riga 1: Pulsante e controlli principali ---
btn = tk.Button(ctrl_frame, text="Open Image...", command=open_and_show_image)
btn.grid(row=0, column=0, padx=(0, 8), pady=4)

tk.Label(ctrl_frame, text="Rows:").grid(row=0, column=1, sticky='e')
entry_rows = tk.Entry(ctrl_frame, width=5)
entry_rows.insert(0, "15")
entry_rows.grid(row=0, column=2, padx=(4, 12))

tk.Label(ctrl_frame, text="Columns:").grid(row=0, column=3, sticky='e')
entry_cols = tk.Entry(ctrl_frame, width=5)
entry_cols.insert(0, "10")
entry_cols.grid(row=0, column=4, padx=(4, 12))

tk.Label(ctrl_frame, text="Border (%):").grid(row=0, column=5, sticky='e')
entry_border = tk.Entry(ctrl_frame, width=6)
entry_border.insert(0, "20")
entry_border.grid(row=0, column=6, padx=(4, 12))

# --- Riga 2: Altri parametri + Checkbox ---
tk.Label(ctrl_frame, text="Tab (%):").grid(row=1, column=1, sticky='e')
entry_tab = tk.Entry(ctrl_frame, width=6)
entry_tab.insert(0, "70")
entry_tab.grid(row=1, column=2, padx=(4, 12))

tk.Label(ctrl_frame, text="Padding (px):").grid(row=1, column=3, sticky='e')
entry_padding = tk.Entry(ctrl_frame, width=6)
entry_padding.insert(0, "150")
entry_padding.grid(row=1, column=4, padx=(4, 12))

# Checkbox ON/OFF
var_onoff = tk.BooleanVar(value=False)
chk_onoff = tk.Checkbutton(ctrl_frame, text="Jpeg Mask", variable=var_onoff)
chk_onoff.grid(row=1, column=5, columnspan=2, padx=(12, 0), sticky='w')

# bottone per aggiornare la sovrapposizione senza riaprire immagine
def update_grid():
    if hasattr(canvas, 'image') or current_pil_img_full is not None:
        display_image_with_overlay()

update_btn = tk.Button(ctrl_frame, text="Update", command=update_grid)
update_btn.grid(row=0, column=12, padx=(8,0))

# Canvas per mostrare l'immagine e l'overlay
canvas = tk.Canvas(root, bg='gray')
canvas.pack(padx=10, pady=(0,10))

root.mainloop()
