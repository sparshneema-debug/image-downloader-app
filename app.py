import os
import shutil
from PIL import Image
from pdf2image import convert_from_path

# ===================== USER SETTINGS =====================
upload_folder = './uploads'      # Folder to read uploaded files from
output_folder = 'converted_files' # Where converted files go
os.makedirs(output_folder, exist_ok=True)

# ——— SET YOUR DESIRED OUTPUT FORMAT ('JPEG', 'PNG', etc) ———
desired_format = 'JPEG'
desired_ext = '.jpg'             # Always put a '.' before ext (e.g. '.jpg', '.png')
resize_to = (2200, 2200)         # Change as needed

# For PDF conversion: choose whether to save all pages (True) or just the first (False)
convert_all_pdf_pages = True

# ================================================

def convert_image(infile, outfile):
    try:
        im = Image.open(infile).convert('RGB')   # Most to JPG need RGB
        # Resize with thumbnail & pad with white
        im.thumbnail(resize_to, Image.LANCZOS)
        new_img = Image.new("RGB", resize_to, (255, 255, 255))
        left = (resize_to[0] - im.width) // 2
        top = (resize_to[1] - im.height) // 2
        new_img.paste(im, (left, top))
        new_img.save(outfile, format=desired_format)
        print(f"Converted and saved: {outfile}")
    except Exception as e:
        print(f"Failed to convert {infile}: {e}")

def convert_pdf(infile, basename):
    try:
        images = convert_from_path(infile, dpi=300)
        pages_to_convert = enumerate(images) if convert_all_pdf_pages else [(0, images[0])]
        for i, img in pages_to_convert:
            outname = f"{basename}_page{i+1}{desired_ext}" if convert_all_pdf_pages else f"{basename}{desired_ext}"
            outpath = os.path.join(output_folder, outname)
            # Resize and save as with images
            img = img.convert('RGB')
            img.thumbnail(resize_to, Image.LANCZOS)
            new_img = Image.new("RGB", resize_to, (255, 255, 255))
            left = (resize_to[0] - img.width) // 2
            top = (resize_to[1] - img.height) // 2
            new_img.paste(img, (left, top))
            new_img.save(outpath, format=desired_format)
            print(f"PDF page saved as: {outpath}")
    except Exception as e:
        print(f"Failed to convert PDF {infile}: {e}")

# ——— MAIN PROCESS ———
for fname in os.listdir(upload_folder):
    path = os.path.join(upload_folder, fname)
    base, ext = os.path.splitext(fname)
    ext_low = ext.lower()
    try:
        if ext_low in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']:
            outname = base + desired_ext
            convert_image(path, os.path.join(output_folder, outname))
        elif ext_low == '.pdf':
            convert_pdf(path, base)
        else:
            print(f"Skipping unsupported file type: {fname}")
    except Exception as e:
        print(f"Error handling {fname}: {e}")

# ——— OPTIONALLY ZIP RESULTS ———
shutil.make_archive(output_folder, 'zip', output_folder)
print(f"Zipped folder as {output_folder}.zip")
