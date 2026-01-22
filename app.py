import streamlit as st
import pandas as pd
import requests
import os
from PIL import Image
from io import BytesIO
import shutil

# For PDF support
try:
    from pdf2image import convert_from_bytes
    HAVE_PDF = True
except ImportError:
    HAVE_PDF = False

st.title("Bulk Image/PDF Downloader and Converter")
st.write("Upload images or PDFs, or provide an Excel file with links.")

with st.expander("1. Directly upload images or PDFs"):
    uploaded_files = st.file_uploader(
        "Upload image or PDF files", type=['jpg', 'jpeg', 'png', 'webp', 'bmp', 'tiff', 'pdf'],
        accept_multiple_files=True)

st.markdown("---")

with st.expander("2. Or upload an Excel file with links"):
    uploaded_excel = st.file_uploader("Excel file (.xlsx)", type=["xlsx"])
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
output_format = st.selectbox(
    "Output image format", options=["JPEG", "PNG", "WEBP"], index=0)
jpeg_quality = st.slider("JPEG quality (only for JPEG)", 50, 100, 90)

output_folder = 'converted_images'
os.makedirs(output_folder, exist_ok=True)

def process_image(image, file_name):
    img = Image.open(image).convert("RGB")
    img.thumbnail(resize_to, Image.LANCZOS)
    new_img = Image.new("RGB", resize_to, (255, 255, 255))
    left = (resize_to[0] - img.width) // 2
    top = (resize_to[1] - img.height) // 2
    new_img.paste(img, (left, top))
    # Set extension according to output format
    ext = {
        'JPEG': '.jpg',
        'PNG': '.png',
        'WEBP': '.webp'
    }[output_format]
    base = os.path.splitext(str(file_name))[0]
    out_path = os.path.join(output_folder, base + ext)
    save_kwargs = {
        "format": output_format,
        "dpi": (output_dpi, output_dpi)
    }
    if output_format == "JPEG":
        save_kwargs["quality"] = jpeg_quality
    new_img.save(out_path, **save_kwargs)
    return out_path

def process_pdf(pdf_bytes, orig_file_name):
    """Convert each PDF page to an image and save."""
    if not HAVE_PDF:
        st.error("PDF support requires the pdf2image package. Please install it.")
        return []
    images = convert_from_bytes(pdf_bytes.read(), dpi=output_dpi)
    out_paths = []
    for page_num, page_img in enumerate(images, start=1):
        buf = BytesIO()
        page_img.save(buf, format="PNG")
        buf.seek(0)
        base = os.path.splitext(str(orig_file_name))[0]
        new_file_name = f"{base}_page{page_num}"
        out_paths.append(process_image(buf, new_file_name))
    return out_paths

# ------------ Main logic ---------------
images_processed = 0
processed_files = []

if st.button("Process Files"):
    # 1. Images or PDFs uploaded directly
    if uploaded_files:
        for file in uploaded_files:
            ext = os.path.splitext(file.name)[1].lower()
            try:
                if ext in ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff']:
                    out_path = process_image(file, file.name)
                    processed_files.append(out_path)
                    images_processed += 1
                elif ext == '.pdf':
                    if HAVE_PDF:
                        out_paths = process_pdf(file, file.name)
                        processed_files.extend(out_paths)
                        images_processed += len(out_paths)
                    else:
                        st.warning("PDF support not available. Please install pdf2image and Poppler.")
                else:
                    st.warning(f"Unsupported file type ({file.name})")
            except Exception as e:
                st.warning(f"Failed file {file.name}: {e}")

    # 2. Images via Excel links
    if uploaded_excel is not None:
        try:
            df = pd.read_excel(uploaded_excel)
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
                            link_ext = os.path.splitext(filename)[1].lower()
                            if link_ext == '.pdf' or ('.pdf' in link.lower()):
                                if HAVE_PDF:
                                    buf = BytesIO(response.content)
                                    out_paths = process_pdf(buf, filename)
                                    processed_files.extend(out_paths)
                                    images_processed += len(out_paths)
                                else:
                                    st.warning(f"PDF {filename} skipped (pdf2image not installed).")
                            else:
                                img_bytes = BytesIO(response.content)
                                out_path = process_image(img_bytes, filename)
                                processed_files.append(out_path)
                                images_processed += 1
                        except Exception as e:
                            st.warning(f"Failed: {filename} from {link}: {e}")
        except Exception as e:
            st.error(f"Error processing Excel: {e}")

    # Clean up non-matching extension files if they exist
    for fname in os.listdir(output_folder):
        if not any(fname.endswith(ext) for ext in [".jpg", ".png", ".webp"]):
            os.remove(os.path.join(output_folder, fname))

    if images_processed > 0:
        zip_path = shutil.make_archive(output_folder, 'zip', output_folder)
        with open(zip_path, "rb") as zf:
            st.success(f"Done! Processed {images_processed} images/pages.")
            st.download_button(
                "Download all as ZIP",
                data=zf,
                file_name="converted_images.zip",
                mime="application/zip"
            )
    else:
        st.info("No images or PDFs processed yet. Upload/select files and try again!")

if not HAVE_PDF:
    st.info("PDF upload will work only if `pdf2image` and Poppler are installed on your server/environment.")
