import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw
from pathcreator import init_params, gen_dh, gen_dv, gen_db
import io

current_pil_img = None  # immagine PIL (ridimensionata) mantenuta in memoria
images_refs = []  # per evitare garbage collection delle PhotoImage

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
    init_params(cols, rows, img_w, img_h, tabsize=0.6*border_pct, jitter=border_pct/10.0)

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

            tk_tile = ImageTk.PhotoImage(tile)
            lbl = tk.Label(frame, image=tk_tile, bd=1, relief='solid')
            lbl.grid(row=r, column=c)
            images_refs.append(tk_tile)

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
entry_rows.insert(0, "3")
entry_rows.grid(row=0, column=2, padx=(4,12))

tk.Label(ctrl_frame, text="Colonne (M):").grid(row=0, column=3, sticky='e')
entry_cols = tk.Entry(ctrl_frame, width=5)
entry_cols.insert(0, "3")
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

# Canvas per mostrare l'immagine e l'overlay
canvas = tk.Canvas(root, bg='gray')
canvas.pack(padx=10, pady=(0,10))

# Apri dialog all'avvio (opzionale)
root.after(100, open_and_show_image)

root.mainloop()
