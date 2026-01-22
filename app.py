import streamlit as st
import pandas as pd
import requests
import os
from PIL import Image
from io import BytesIO
import shutil

st.title("Bulk Image Downloader and Converter (.JPG only)")
st.write("Upload your Excel file with image links. All outputs will be .jpg files.")

uploaded_file = st.file_uploader("Upload Excel file (.xlsx)", type=["xlsx"])

col1 = st.text_input("First FileName column", value="FileName1")
link1 = st.text_input("First ImageLink column", value="ImageLink1")
col2 = st.text_input("Second FileName column (optional)", value="")
link2 = st.text_input("Second ImageLink column (optional)", value="")

output_width = st.number_input("Output width (px)", value=2200)
output_height = st.number_input("Output height (px)", value=2200)
resize_to = (int(output_width), int(output_height))
output_dpi = st.number_input("DPI", min_value=50, max_value=1200, value=300)
jpeg_quality = st.slider("JPEG quality", 50, 100, 90)

output_folder = 'downloaded_images'
os.makedirs(output_folder, exist_ok=True)

def process_image(image, file_name):
    img = Image.open(image).convert("RGB")
    img.thumbnail(resize_to, Image.LANCZOS)
    new_img = Image.new("RGB", resize_to, (255, 255, 255))
    left = (resize_to[0] - img.width) // 2
    top = (resize_to[1] - img.height) // 2
    new_img.paste(img, (left, top))
    ext = '.jpg'
    base = os.path.splitext(str(file_name))[0]
    out_path = os.path.join(output_folder, base + ext)
    new_img.save(out_path, format="JPEG", quality=jpeg_quality, dpi=(output_dpi, output_dpi))
    return out_path

if st.button("Process Images"):
    images_processed = 0
    processed_files = []
    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file)
            column_pairs = []
            if col1 and link1:
                column_pairs.append((col1, link1))
            if col2 and link2:
                column_pairs.append((col2, link2))
            for idx, row in df.iterrows():
                for filename_col, link_col in column_pairs:
                    filename = row.get(filename_col)
                    link = row.get(link_col)
                    if pd.notna(filename) and pd.notna(link):
                        try:
                            response = requests.get(link, timeout=10)
                            response.raise_for_status()
                            img_bytes = BytesIO(response.content)
                            out_path = process_image(img_bytes, filename)
                            processed_files.append(out_path)
                            images_processed += 1
                        except Exception as e:
                            st.warning(f"Failed: {filename} from {link}: {e}")
            for fname in os.listdir(output_folder):
                if not fname.lower().endswith('.jpg'):
                    os.remove(os.path.join(output_folder, fname))
            zip_path = shutil.make_archive(output_folder, 'zip', output_folder)
            with open(zip_path, "rb") as zf:
                st.success(f"Done! Processed {images_processed} images.")
                st.download_button(
                    "Download all as ZIP",
                    data=zf,
                    file_name="downloaded_images.zip",
                    mime="application/zip"
                )
        except Exception as e:
            st.error(f"Error processing Excel: {e}")
    else:
        st.warning("Please upload your Excel file to start.")
