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
Upload your Excel file containing image file names and links in pairs of columns.  
E.g., columns: 'FileName1', 'ImageLink1', 'FileName2', 'ImageLink2', ...
""")

def safe_int(value, default=0):
    try:
        return int(value)
    except:
        return default

uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])
columns = st.text_input(
    "List your filename and link column pairs, separated by commas (e.g. FileName1,ImageLink1,FileName2,ImageLink2):"
)
width = st.number_input("Resize WIDTH (pixels)", min_value=1, value=2200)
height = st.number_input("Resize HEIGHT (pixels)", min_value=1, value=2200)
dpi = st.number_input("DPI for saved JPG (web=72, print=300 is common)", min_value=1, value=72)
margin_cm = st.number_input("Margin on each side (cm)", min_value=0.0, value=1.0, step=0.1)

if uploaded_file and columns:
    try:
        margin_px = safe_int(dpi * margin_cm / 2.54)
        content_width = width - 2 * margin_px
        content_height = height - 2 * margin_px

        if content_width <= 0 or content_height <= 0:
            st.error("Margin is too large for the given width/height!")
        else:
            column_pairs = [x.strip() for x in columns.split(",") if x.strip()]
            if len(column_pairs) < 2 or len(column_pairs) % 2 != 0:
                st.error("Please provide at least one *complete* pair of filename and link column names (e.g. FileName1,ImageLink1).")
            else:
                pairs = [(column_pairs[i], column_pairs[i+1]) for i in range(0, len(column_pairs), 2)]
                
                try:
                    df = pd.read_excel(uploaded_file)
                except Exception as e:
                    st.error(f"Error loading Excel file: {e}")
                    df = None

                if df is not None:
                    missing_columns = [col for pair in pairs for col in pair if col not in df.columns]
                    if missing_columns:
                        st.error(f"Your Excel file is missing these columns: {missing_columns}")
                    else:
                        tempdir = tempfile.mkdtemp()
                        output_dir = os.path.join(tempdir, "downloaded_images")
                        os.makedirs(output_dir, exist_ok=True)
                        any_success = False
                        for idx, row in df.iterrows():
                            for fn_col, link_col in pairs:
                                filename = row.get(fn_col)
                                link = row.get(link_col)
                                # Skip blank or invalid rows
                                if pd.notna(filename) and pd.notna(link) and isinstance(link, str) and link.lower().startswith('http'):
                                    try:
                                        r = requests.get(link, timeout=15)
                                        r.raise_for_status()
                                        img = Image.open(BytesIO(r.content)).convert("RGB")

                                        # Aspect ratios
                                        img_ratio = img.width / img.height
                                        box_ratio = width / height
                                        content_box_ratio = content_width / content_height

                                        # If proportional and large enough: no margin, fill canvas
                                        AR_TOLERANCE = 0.02
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
                                            new_img = Image.new("RGB", (width, height), (255, 255, 255))
                                            left = (width - new_width) // 2
                                            top = (height - new_height) // 2
                                            new_img.paste(img_resized, (left, top))

                                        file_jpg = str(filename)
                                        if not file_jpg.lower().endswith('.jpg'):
                                            file_jpg = os.path.splitext(file_jpg)[0] + '.jpg'
                                        new_img.save(
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
                                st.download_button('Download All Images (ZIP)', f, file_name='downloaded_images.zip')
                        else:
                            st.info("No images were successfully processed. Please check your links.")
    except Exception as err:
        st.error(f"An unexpected error occurred: {err}")
else:
    st.info("To get started, upload your Excel file and enter your column pairs.")
