import streamlit as st
import pandas as pd
import requests
import os
from PIL import Image
from io import BytesIO
import shutil

# ================ Streamlit UI ================
st.title("Image Downloader & Converter")
st.write("Upload an Excel file with columns for filenames and image URLs/links.")

uploaded_file = st.file_uploader("Choose an Excel file", type=["xlsx"])

column1 = st.text_input("First filename column", value="FileName1")
link1 = st.text_input("First link column", value="ImageLink1")
column2 = st.text_input("Second filename column (optional)", value="")
link2 = st.text_input("Second link column (optional)", value="")

resize_to = (2200, 2200)
output_folder = 'downloaded_images'
os.makedirs(output_folder, exist_ok=True)

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        # Use only populated column pairs
        column_pairs = []
        if column1 and link1:
            column_pairs.append((column1, link1))
        if column2 and link2:
            column_pairs.append((column2, link2))
        if not column_pairs:
            st.error("Please provide at least one valid filename/link pair.")
        else:
            progress = st.progress(0)
            total = len(df) * len(column_pairs)
            count = 0
            status_text = st.empty()
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
                            count += 1
                        except Exception as e:
                            st.warning(f"Failed {filename} from {link}: {e}")
                        progress.progress(count / total)
                        status_text.text(f"Processed {count} of {total}")
            for fname in os.listdir(output_folder):
                if not fname.lower().endswith('.jpg'):
                    os.remove(os.path.join(output_folder, fname))
            shutil.make_archive(output_folder, 'zip', output_folder)
            st.success("All downloads and conversions complete.")
            with open(f"{output_folder}.zip", "rb") as zip_file:
                st.download_button(
                    label="Download All Images as ZIP",
                    data=zip_file,
                    file_name="downloaded_images.zip",
                    mime="application/zip"
                )
    except Exception as err:
        st.error(f"Error processing file: {err}")
else:
    st.info("Awaiting Excel file upload.")
