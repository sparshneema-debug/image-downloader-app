import pandas as pd
import requests
import os
from PIL import Image
from io import BytesIO
import shutil

# ===================== USER SETTINGS =====================
excel_file = '/content/file.xlsx'   # Path to your Excel file

# List your (filename, link) pairs as per your Excel headers here:
column_pairs = [
    ('FileName1', 'ImageLink1'),
    ('FileName2', 'ImageLink2'),
    # Add more pairs as needed
]
# =========================================================

output_folder = 'downloaded_images'
os.makedirs(output_folder, exist_ok=True)
resize_to = (2200, 2200)
df = pd.read_excel(excel_file)

for idx, row in df.iterrows():
    for filename_col, link_col in column_pairs:
        filename = row.get(filename_col)
        link = row.get(link_col)
        if pd.notna(filename) and pd.notna(link):
            try:
                response = requests.get(link, timeout=10)
                response.raise_for_status()
                img = Image.open(BytesIO(response.content)).convert("RGB")
                # Resize, maintain aspect ratio & pad with white
                img.thumbnail(resize_to, Image.LANCZOS)
                new_img = Image.new("RGB", resize_to, (255, 255, 255))
                left = (resize_to[0] - img.width) // 2
                top = (resize_to[1] - img.height) // 2
                new_img.paste(img, (left, top))
                # Ensure .jpg extension
                file_jpg = str(filename)
                if not file_jpg.lower().endswith('.jpg'):
                    file_jpg = os.path.splitext(file_jpg)[0] + '.jpg'
                new_img.save(os.path.join(output_folder, file_jpg), format='JPEG')
                print(f"Downloaded, resized, and saved: {file_jpg}")
            except Exception as e:
                print(f"Failed {filename} from {link}: {e}")

print("All downloads and conversions complete.")

# ======== Remove non-JPG files from the output folder ========
for fname in os.listdir(output_folder):
    if not fname.lower().endswith('.jpg'):
        os.remove(os.path.join(output_folder, fname))

# ========== ZIP the images folder ==========
shutil.make_archive(output_folder, 'zip', output_folder)
print(f"Zipped folder as {output_folder}.zip")

# ========== Google Colab/Jupyter: offer download ==========
try:
    from google.colab import files
    files.download(f"{output_folder}.zip")
except ImportError:
    print("If not using Colab, manually download 'downloaded_images.zip' from your workspace.")