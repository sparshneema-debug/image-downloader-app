import streamlit as st
import pandas as pd
import requests
import os
from PIL import Image
from io import BytesIO
import shutil

st.set_page_config(page_title="Image Downloader & Converter", layout='centered')

st.title("🖼️ Image Downloader & Converter (.JPG only)")
st.markdown("""
Upload images directly **or** provide an Excel file with image links.  
All converted images will be output as `.jpg` and provided in a downloadable ZIP archive.
""")

st.header("① Directly Upload Images")
uploaded_images = st.file_uploader(
    "Drag and drop or browse for images (multiple allowed)",
    type=['jpg', 'jpeg', 'png', 'webp', 'bmp', 'tiff'],
    accept_multiple_files=True,
    key="direct_upload"
)

st.divider()

st.header("② Or Upload Excel File with Image Links")
uploaded_file = st.file_uploader(
    "Excel file (.xlsx)",
    type=["xlsx"],
    key="excel_upload"
)
col1, col2 = st.columns(2)
with col1:
    file_col1 = st.text_input("First FileName column", value="FileName1")
    file_col2 = st.text_input("Second FileName column (optional)", value="")
with col2:
    link_col1 = st.text_input("First ImageLink column", value="ImageLink1")
    link_col2 = st.text_input("Second ImageLink column (optional)", value="")

st.divider()

st.header("③ Image Output Settings")
output_width = st.number_input("Output width (pixels)", min_value=100, max_value=5000, value=2200, step=10)
output_height = st.number_input("Output height (pixels)", min_value=100, max_value=5000, value=2200, step=10)
output_dpi = st.number_input("DPI", min_value=50, max_value=1200, value=300, step=1)
margin_cm = st.number_input("Margin (in cm, on all sides)", min_value=0.0, max_value=10.0, value=0.5, step=0.1,
                            help="Leave 0 for no margin. Margin is applied as a white border (cm to pixels is calculated using DPI).")

resize_to = (int(output_width), int(output_height))

output_folder = 'downloaded_images'
os.makedirs(output_folder, exist_ok=True)

def process_image(image, file_name, margin_px):
    img = Image.open(image).convert("RGB")
    # Calculate new max size for image itself (inside the margin)
    img_width = output_width - 2 * margin_px
    img_height = output_height - 2 * margin_px
    img_width = max(1, img_width)
    img_height = max(1, img_height)
    img.thumbnail((img_width, img_height), Image.LANCZOS)
    new_img = Image.new("RGB", (output_width, output_height), (255, 255, 255))
    left = (output_width - img.width) // 2
    top = (output_height - img.height) // 2
    new_img.paste(img, (left, top))
    ext = '.jpg'
    base = os.path.splitext(str(file_name))[0]
    out_path = os.path.join(output_folder, base + ext)
    new_img.save(out_path, format="JPEG", dpi=(output_dpi, output_dpi))
    return out_path

def cm_to_pixels(cm, dpi):
    return int((cm / 2.54) * dpi)

st.divider()

if st.button("🚀 Process Images"):
    images_processed = 0
    processed_files = []

    margin_px = cm_to_pixels(margin_cm, output_dpi)

    progress_bar = st.progress(0, text="Starting image processing...")
    step_total = (
        (len(uploaded_images) if uploaded_images else 0) +
        (
            len(pd.read_excel(uploaded_file)) *
            (1 + bool(file_col2 and link_col2))
            if uploaded_file else 0
        )
    )
    current_step = 0

    if uploaded_images:
        for img_file in uploaded_images:
            try:
                process_image(img_file, img_file.name, margin_px)
                processed_files.append(img_file.name)
                images_processed += 1
            except Exception as e:
                st.warning(f"⚠️ Failed image upload `{img_file.name}`: {e}")
            current_step += 1
            progress_bar.progress(current_step / max(1, step_total))
    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file)
            column_pairs = []
            if file_col1 and link_col1:
                column_pairs.append((file_col1, link_col1))
            if file_col2 and link_col2:
                column_pairs.append((file_col2, link_col2))
            for idx, row in df.iterrows():
                for filename_col, link_col in column_pairs:
                    filename = row.get(filename_col)
                    link = row.get(link_col)
                    if pd.notna(filename) and pd.notna(link):
                        try:
                            response = requests.get(link, timeout=10)
                            response.raise_for_status()
                            img_bytes = BytesIO(response.content)
                            process_image(img_bytes, filename, margin_px)
                            processed_files.append(filename)
                            images_processed += 1
                        except Exception as e:
                            st.warning(f"⚠️ Failed: `{filename}` from `{link}`: {e}")
                    current_step += 1
                    progress_bar.progress(current_step / max(1, step_total))
        except Exception as e:
            st.error(f"❌ Error processing Excel: {e}")

    # Remove non-JPG files (safety)
    for fname in os.listdir(output_folder):
        if not fname.lower().endswith('.jpg'):
            os.remove(os.path.join(output_folder, fname))

    if images_processed > 0:
        zip_path = shutil.make_archive(output_folder, 'zip', output_folder)
        with open(zip_path, "rb") as zf:
            st.success(f"✅ Done! Processed {images_processed} images.")
            st.download_button(
                "⬇️ Download all as ZIP",
                data=zf,
                file_name="downloaded_images.zip",
                mime="application/zip"
            )
    else:
        st.info("No images processed yet. Upload/select files and try again!")

    progress_bar.empty()

st.caption("Built by Pattern Chat • JPG outputs • Custom DPI • Custom margins (cm) supported.")
