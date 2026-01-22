import streamlit as st
import pandas as pd
import requests
import os
from PIL import Image
from io import BytesIO
import shutil

st.title("Bulk Image Downloader and Converter")

# File uploader for Excel file
uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx"])

# Allow user to specify the column names
st.write("Enter the column names for FileName and ImageLink pairs as in your Excel.")
col1 = st.text_input("First FileName column", value="FileName1")
link1 = st.text_input("First ImageLink column", value="ImageLink1")
col2 = st.text_input("Second FileName column (optional)", value="")
link2 = st.text_input("Second ImageLink column (optional)", value="")

resize_to = (2200, 2200)
output_folder = 'downloaded_images'
os.makedirs(output_folder, exist_ok=True)

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        column_pairs = []
        if col1 and link1:
            column_pairs.append((col1, link1))
        if col2 and link2:
            column_pairs.append((col2, link2))

        progress = st.progress(0)
        total = len(df) * len(column_pairs)
        done = 0

        for idx, row in df.iterrows():
            for filename_col, link_col in column_pairs:
                filename = row.get(filename_col)
                link = row.get(link_col)
                if pd.notna(filename) and pd.notna(link):
                    try:
                        response = requests.get(link, timeout=10)
                        response.raise_for_status()
                        img = Image.open(BytesIO(response.content)).convert("RGB")
                        img.thumbnail(resize_to, Image.LANCZOS)
                        new_img = Image.new("RGB", resize_to, (255, 255, 255))
                        left = (resize_to[0] - img.width) // 2
                        top = (resize_to[1] - img.height) // 2
                        new_img.paste(img, (left, top))
                        file_jpg = str(filename)
                        if not file_jpg.lower().endswith('.jpg'):
                            file_jpg = os.path.splitext(file_jpg)[0] + '.jpg'
                        new_img.save(os.path.join(output_folder, file_jpg), format='JPEG')
                    except Exception as e:
                        st.warning(f"Failed {filename} from {link}: {e}")
                done += 1
                progress.progress(done / total)
        # Remove non-JPG files (safety; usually not needed)
        for fname in os.listdir(output_folder):
            if not fname.lower().endswith('.jpg'):
                os.remove(os.path.join(output_folder, fname))
        zip_path = shutil.make_archive(output_folder, 'zip', output_folder)
        with open(zip_path, "rb") as zf:
            st.success("Done! Download your images below.")
            st.download_button(
                "Download images as ZIP",
                data=zf,
                file_name="downloaded_images.zip",
                mime="application/zip"
            )
    except Exception as e:
        st.error(f"An error occurred: {e}")
else:
    st.info("Please upload your Excel file to start.")
