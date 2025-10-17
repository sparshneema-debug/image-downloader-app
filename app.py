import streamlit as st
import pandas as pd
import requests
from PIL import Image
from io import BytesIO
import os
import shutil
import tempfile

st.title("Bulk Image Downloader, Resizer & Padder")
st.markdown("**Made by Sparsh Neema**")

st.write("""
Upload your Excel file containing image file names and links in pairs of columns.  
E.g., columns: 'FileName1', 'ImageLink1', 'FileName2', 'ImageLink2', ...
""")

uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])
columns = st.text_input(
    "List your filename and link column pairs, separated by commas (e.g. FileName1,ImageLink1,FileName2,ImageLink2):"
)
width = st.number_input("Resize WIDTH (pixels)", min_value=1, value=2200)
height = st.number_input("Resize HEIGHT (pixels)", min_value=1, value=2200)
dpi = st.number_input("DPI for saved JPG (web=72, print=300 is common)", min_value=1, value=72)

margin_cm = st.number_input("Margin on each side (cm)", min_value=0.0, value=1.0, step=0.1)

if uploaded_file and columns:
    # Calculate margin in pixels
    margin_px = int(dpi * margin_cm / 2.54)

    content_width = width - 2 * margin_px
    content_height = height - 2 * margin_px

    if content_width <= 0 or content_height <= 0:
        st.error("Margin is too large for the given width/height!")
    else:
        column_pairs = [x.strip() for x in columns.split(",")]
        if len(column_pairs) % 2 != 0:
            st.error("Please provide pairs of filename and link columns.")
        else:
            pairs = [(column_pairs[i], column_pairs[i+1]) for i in range(0, len(column_pairs), 2)]
            tempdir = tempfile.mkdtemp()
            output_dir = os.path.join(tempdir, "downloaded_images")
            os.makedirs(output_dir, exist_ok=True)
            df = pd.read_excel(uploaded_file)
            for idx, row in df.iterrows():
                for fn_col, link_col in pairs:
                    filename = row.get(fn_col)
                    link = row.get(link_col)
                    if pd.notna(filename) and pd.notna(link):
                        try:
                            r = requests.get(link, timeout=10)
                            r.raise_for_status()
                            img = Image.open(BytesIO(r.content)).convert("RGB")

                            # Fit image to box minus margin (scale up or down as needed)
                            img_ratio = img.width / img.height
                            box_ratio = content_width / content_height

                            if img_ratio > box_ratio:
                                # Fit width
                                new_width = content_width
                                new_height = int(content_width / img_ratio)
                            else:
                                # Fit height
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
                        except Exception as e:
                            st.write(f"Failed {filename} from {link}: {e}")
            zip_path = shutil.make_archive(output_dir, 'zip', output_dir)
            with open(zip_path, 'rb') as f:
                st.download_button('Download All Images (ZIP)', f, file_name='downloaded_images.zip')
