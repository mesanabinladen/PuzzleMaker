# PuzzleMaker — Image viewer & tile composer

Small Tkinter + Pillow utility to:
- open an image (processing is done on the full-resolution copy; GUI shows a scaled preview),
- overlay an NxM grid,
- expand each cell by a percentage "border" that overlaps neighbours,
- extract each expanded cell as a tile and compose a single output `puzzle_full.jpg`, plus an A4 `puzzle_page_x-y.jpg` (both A4 320ppi) to print every puzzle part, and `puzzle_contours_x-y.svg` with SVG contours for using with the laser engraver

Requirements
- Tested with Python 3.11
- Pillow
- tkinter (usually included with Python)
- project module `pathcreator.py` (included in the repo)

Installation

1. Install dependencies:
   ```bash
   python -m pip install --upgrade pip
   python -m pip install pillow
   ```
   
Run
- From the project folder:
  ```bash
  python main.py
  ```

Usage
1. Click "Open Image..." and choose an image file.
2. Set:
   - Rows (N)
   - Columns (M)
   - Border (%) — percent expansion per cell (e.g. 20 → each cell grows by 20%).
   - Tab (%) — percent dimension for the tabs referred to the border size (max 100%!)
   - Padding (pixel): number of pixel for padding around the A4 images

3. Click "Update" to redraw the overlay preview.
4. The app saves all the files (see details below).

Where output files are saved
- When running as a script: the app attempts to save next to `main.py`.
- When frozen with PyInstaller: primary save location is the executable folder. If that location is not writable (e.g. Program Files), the app falls back to the user's Pictures folder (or home folder if Pictures can't be created).
- You can change the save location in `main.py` if you prefer a specific path.

Preview vs processing
- The UI shows a scaled preview for performance, but all processing (grid, masks, extraction) runs on the full-resolution image to preserve quality.

Packaging with PyInstaller (Windows)
- Recommended command (run from project folder where `puzzle_icon.ico` is located): read the `Pyinstaller instruction.TXT`

Notes
- The final puzzle will mantain the original image's dimensions
- Large full-resolution images may require significant memory/time to process.
- The code already detects PyInstaller "frozen" mode to choose a save directory; modify that logic if you prefer a different fallback.
- If you want the app to prompt for an output path instead of automatic saving, add a Save As dialog in `main.py`.

License
- Personal project. Add a license file if you intend to redistribute. 
