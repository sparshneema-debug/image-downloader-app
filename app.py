import streamlit as st
import pandas as pd
import requests
from PIL import Image
from io import BytesIO
import os
import shutil
import tempfile

st.set_page_config(page_title="Bulk Image Downloader, Resizer & Padder")
st.title("Bulk Image Downloader, Resizer & Padder")
st.markdown("**Made by Sparsh Neema**")

st.write("""
You can either:
- Upload your Excel file with image file names and public URLs, **OR**
- Upload one or more images directly from your computer.
All images will be resized and padded according to your settings!
""")

# === Configuration options: shared for both workflows ===
width = st.number_input("Resize WIDTH (pixels)", min_value=1, value=2200)
height = st.number_input("Resize HEIGHT (pixels)", min_value=1, value=2200)
dpi = st.number_input("DPI for saved JPG (web=72, print=300 is common)", min_value=1, value=72)
margin_cm = st.number_input("Margin on each side (cm)", min_value=0.0, value=1.0, step=0.1)

margin_px = int(dpi * margin_cm / 2.54)
content_width = width - 2 * margin_px
content_height = height - 2 * margin_px
AR_TOLERANCE = 0.02  # Aspect ratio tolerance for skipping margin

tempdir = tempfile.mkdtemp()

# === Option 1: Excel file upload with URLs ===
with st.expander("Option 1: Use Excel File With Image URLs"):
    uploaded_excel = st.file_uploader("Upload Excel File", type=["xlsx"])
    columns = st.text_input(
        "Excel column pairs (e.g. FileName1,ImageLink1,FileName2,ImageLink2):"
    )

# === Option 2: Directly upload images ===
with st.expander("Option 2: Upload Images Directly"):
    uploaded_images = st.file_uploader(
        "Upload one or more images", type=["jpg", "jpeg", "png"], accept_multiple_files=True
    )

def process_image(img, file_jpg):
    img_ratio = img.width / img.height
    box_ratio = width / height
    content_box_ratio = content_width / content_height

    # If the original image nearly fills the canvas and is big, skip margin
    is_proportional = abs(img_ratio - box_ratio) < AR_TOLERANCE
    is_big_enough = img.width >= width and img.height >= height

    if is_proportional and is_big_enough:
        img_resized = img.resize((width, height), Image.LANCZOS)
        new_img = img_resized
    else:
        # Fit in content area (with margin)
        if img_ratio > content_box_ratio:
            new_width = content_width
            new_height = int(content_width / img_ratio)
        else:
            new_height = content_height
            new_width = int(content_height * img_ratio)
        img_resized = img.resize((new_width, new_height), Image.LANCZOS)
        new_img = Image.new("RGB", (width, height), (255,255,255))
        left = (width - new_width) // 2
        top = (height - new_height) // 2
        new_img.paste(img_resized, (left, top))
    return new_img

# === Handle Excel workflow ===
if uploaded_excel and columns:
    column_pairs = [x.strip() for x in columns.split(",") if x.strip()]
    if len(column_pairs) < 2 or len(column_pairs) % 2 != 0:
        st.error("Please provide at least one complete pair of filename and link column names (e.g. FileName1,ImageLink1).")
    else:
        pairs = [(column_pairs[i], column_pairs[i+1]) for i in range(0, len(column_pairs), 2)]
        try:
            df = pd.read_excel(uploaded_excel)
            missing_columns = [col for pair in pairs for col in pair if col not in df.columns]
            if missing_columns:
                st.error(f"Excel file is missing these columns: {missing_columns}")
            else:
                output_dir = os.path.join(tempdir, "downloaded_images")
                os.makedirs(output_dir, exist_ok=True)
                any_success = False
                for idx, row in df.iterrows():
                    for fn_col, link_col in pairs:
                        filename = row.get(fn_col)
                        link = row.get(link_col)
                        if pd.notna(filename) and pd.notna(link) and isinstance(link, str) and link.lower().startswith('http'):
                            try:
                                r = requests.get(link, timeout=15)
                                r.raise_for_status()
                                img = Image.open(BytesIO(r.content)).convert("RGB")
                                file_jpg = str(filename)
                                if not file_jpg.lower().endswith('.jpg'):
                                    file_jpg = os.path.splitext(file_jpg)[0] + '.jpg'
                                processed_img = process_image(img, file_jpg)
                                processed_img.save(
                                    os.path.join(output_dir, file_jpg),
                                    "JPEG",
                                    dpi=(dpi, dpi)
                                )
                                any_success = True
                            except Exception as ex:
                                st.warning(f"Failed to process '{filename}' from '{link}': {ex}")
                if any_success:
                    zip_path = shutil.make_archive(output_dir, 'zip', output_dir)
                    with open(zip_path, 'rb') as f:
                        st.download_button('Download Images (ZIP)', f, file_name='downloaded_images.zip')
                else:
                    st.info("No images were successfully processed (check your links and columns).")
        except Exception as ex:
            st.error(f"Error processing Excel file: {ex}")

# === Handle direct image upload workflow ===
if uploaded_images:
    output_dir2 = os.path.join(tempdir, "uploaded_images")
    os.makedirs(output_dir2, exist_ok=True)
    any_img = False
    for uploaded_image in uploaded_images:
        try:
            img = Image.open(uploaded_image).convert("RGB")
            output_name = uploaded_image.name
            file_jpg = output_name if output_name.lower().endswith('.jpg') else os.path.splitext(output_name)[0] + ".jpg"
            processed_img = process_image(img, file_jpg)
            processed_img.save(os.path.join(output_dir2, file_jpg), "JPEG", dpi=(dpi, dpi))
            any_img = True
        except Exception as ex:
            st.warning(f"Failed to process {uploaded_image.name}: {ex}")
    if any_img:
        zip_path2 = shutil.make_archive(output_dir2, 'zip', output_dir2)
        with open(zip_path2, 'rb') as f2:
            st.download_button('Download Uploaded Images (ZIP)', f2, file_name='uploaded_images.zip')

st.info("Select either Excel upload or direct image upload, set your parameters, and download the results as a ZIP file.")
