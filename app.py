import streamlit as st
import pandas as pd
import requests
import os
from PIL import Image
from io import BytesIO
import shutil

st.title("Bulk Image Downloader and Converter (.JPG only)")
st.write("Upload images yourself or provide an Excel file with image links. All outputs will be .jpg files.")

with st.expander("1. Directly upload images"):
    uploaded_images = st.file_uploader(
        "Upload one or more images", 
        type=['jpg', 'jpeg', 'png', 'webp', 'bmp', 'tiff'], 
        accept_multiple_files=True
    )

st.markdown("---")

with st.expander("2. Or upload an Excel file with links"):
    uploaded_file = st.file_uploader("Excel file (.xlsx)", type=["xlsx"])
    col1 = st.text_input("First FileName column", value="FileName1")
    link1 = st.text_input("First ImageLink column", value="ImageLink1")
    col2 = st.text_input("Second FileName column (optional)", value="")
    link2 = st.text_input("Second ImageLink column (optional)", value="")

st.markdown("---")

# ==== Image processing settings ====
output_width = st.number_input("Output width (px)", value=2200)
output_height = st.number_input("Output height (px)", value=2200)
resize_to = (int(output_width), int(output_height))
output_dpi = st.number_input("DPI", min_value=50, max_value=1200, value=300)
jpeg_quality = st.slider("JPEG quality", 50, 100, 90)

output_folder = 'converted_images'
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

# ------------ Main logic ---------------
images_processed = 0
processed_files = []

if st.button("Process Images"):
    # 1. Images uploaded by hand
    if uploaded_images:
        for img_file in uploaded_images:
            try:
                out_path = process_image(img_file, img_file.name)
                processed_files.append(out_path)
                images_processed += 1
            except Exception as e:
                st.warning(f"Failed image upload {img_file.name}: {e}")

    # 2. Images via Excel links
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
        except Exception as e:
            st.error(f"Error processing Excel: {e}")

    # Remove non-JPG files (safety)
    for fname in os.listdir(output_folder):
        if not fname.lower().endswith('.jpg'):
            os.remove(os.path.join(output_folder, fname))

    if images_processed > 0:
        zip_path = shutil.make_archive(output_folder, 'zip', output_folder)
        with open(zip_path, "rb") as zf:
            st.success(f"Done! Processed {images_processed} images.")
            st.download_button(
                "Download all as ZIP",
                data=zf,
                file_name="converted_images.zip",
                mime="application/zip"
            )
    else:
        st.info("No images processed yet. Upload or select files and try again!")
