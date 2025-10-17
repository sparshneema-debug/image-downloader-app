import streamlit as st
import pandas as pd
import requests
from PIL import Image
from io import BytesIO
import os
import shutil
import tempfile

st.title("Bulk Image Downloader, Resizer & Padder")
st.markdown("**Made by Sparsh Neema**")   # <--- Your name here

st.write("""
Upload your Excel file containing image file names and links in pairs of columns.  
E.g., columns: 'FileName1', 'ImageLink1', 'FileName2', 'ImageLink2', ...
""")

uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])
columns = st.text_input(
    "List your filename and link column pairs, separated by commas (e.g. FileName1,ImageLink1,FileName2,ImageLink2):"
)
resize_dim = st.number_input("Resize and pad to size (pixels; e.g. 2200):", min_value=1, value=2200)

if uploaded_file and columns:
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
                        img.thumbnail((resize_dim, resize_dim), Image.LANCZOS)
                        new_img = Image.new("RGB", (resize_dim, resize_dim), (255,255,255))
                        left = (resize_dim - img.width)//2
                        top = (resize_dim - img.height)//2
                        new_img.paste(img, (left, top))
                        file_jpg = str(filename)
                        if not file_jpg.lower().endswith('.jpg'):
                            file_jpg = os.path.splitext(file_jpg)[0] + '.jpg'
                        new_img.save(os.path.join(output_dir, file_jpg), "JPEG")
                    except Exception as e:
                        st.write(f"Failed {filename} from {link}: {e}")
        zip_path = shutil.make_archive(output_dir, 'zip', output_dir)
        with open(zip_path, 'rb') as f:
            st.download_button('Download All Images (ZIP)', f, file_name='downloaded_images.zip')
