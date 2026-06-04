import streamlit as st
import pandas as pd
import requests
import os
from PIL import Image, ImageChops
from io import BytesIO
import shutil

st.set_page_config(page_title="Image Downloader & Converter", layout="centered")

st.title("🖼️ Complete Image Downloader & Converter")
st.markdown("""
Upload images directly **or** provide an Excel file with image links.  
Resize, crop, zoom, change background color, convert format, preview, and download as ZIP.
""")

st.header("① Directly Upload Images")
uploaded_images = st.file_uploader(
    "Drag and drop or browse for images (multiple allowed)",
    type=["jpg", "jpeg", "png", "webp", "bmp", "tiff"],
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

output_format = st.selectbox(
    "Output Format",
    ["JPG", "PNG", "WEBP"],
    index=0
)

quality = st.slider(
    "Image Quality",
    min_value=40,
    max_value=100,
    value=95,
    step=1,
    help="Applies to JPG and WEBP. Higher quality = larger file size."
)

background_color = st.color_picker(
    "Background Color",
    value="#FFFFFF"
)

resize_mode = st.radio(
    "Image Processing Mode",
    [
        "Resize with Padding",
        "Resize without Padding"
    ],
    index=0,
    horizontal=True
)

crop_white = False
enlarge_image = False
zoom_percent = 100
margin_cm = 0.0

if resize_mode == "Resize with Padding":
    crop_white = st.checkbox(
        "Crop White Background",
        value=True,
        help="Removes extra white space around the product before resizing."
    )

    enlarge_image = st.checkbox(
        "Enlarge Image",
        value=True,
        help="Makes the product larger inside the canvas."
    )

    if enlarge_image:
        zoom_percent = st.slider(
            "Product Zoom (%)",
            min_value=100,
            max_value=400,
            value=180,
            step=5,
            help="Increase product size inside the canvas."
        )

    margin_cm = st.number_input(
        "Margin (in cm, on all sides)",
        min_value=0.0,
        max_value=10.0,
        value=0.5,
        step=0.1,
        help="Leave 0 for no margin."
    )

preview_enabled = st.checkbox(
    "Preview first 5 processed images",
    value=True
)

def cm_to_pixels(cm, dpi):
    return int((cm / 2.54) * dpi)

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def clean_folder(folder_path):
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)
    os.makedirs(folder_path, exist_ok=True)

def get_extension(output_format):
    if output_format == "JPG":
        return ".jpg"
    if output_format == "PNG":
        return ".png"
    if output_format == "WEBP":
        return ".webp"
    return ".jpg"

def get_pil_format(output_format):
    if output_format == "JPG":
        return "JPEG"
    if output_format == "PNG":
        return "PNG"
    if output_format == "WEBP":
        return "WEBP"
    return "JPEG"

def get_unique_filename(output_folder, base_name, ext):
    safe_name = "".join(c for c in str(base_name) if c not in r'\/:*?"<>|').strip()
    if not safe_name:
        safe_name = "image"

    file_path = os.path.join(output_folder, safe_name + ext)
    counter = 1

    while os.path.exists(file_path):
        file_path = os.path.join(output_folder, f"{safe_name}_{counter}{ext}")
        counter += 1

    return file_path

def crop_white_background(img, tolerance=245):
    img = img.convert("RGB")

    bg = Image.new("RGB", img.size, (255, 255, 255))
    diff = ImageChops.difference(img, bg).convert("L")

    mask = diff.point(lambda p: 255 if p > (255 - tolerance) else 0)
    bbox = mask.getbbox()

    if bbox:
        return img.crop(bbox)

    return img

def save_image(img, out_path, output_format, output_dpi, quality):
    pil_format = get_pil_format(output_format)

    if output_format == "JPG":
        img = img.convert("RGB")
        img.save(
            out_path,
            format=pil_format,
            dpi=(output_dpi, output_dpi),
            quality=quality,
            optimize=True
        )

    elif output_format == "PNG":
        img.save(
            out_path,
            format=pil_format,
            dpi=(output_dpi, output_dpi),
            optimize=True
        )

    elif output_format == "WEBP":
        img.save(
            out_path,
            format=pil_format,
            quality=quality,
            method=6
        )

def process_image(
    image_source,
    file_name,
    margin_px,
    output_folder,
    output_width,
    output_height,
    output_dpi,
    resize_mode,
    crop_white,
    enlarge_image,
    zoom_percent,
    output_format,
    quality,
    background_color
):
    img = Image.open(image_source).convert("RGB")

    ext = get_extension(output_format)
    base_name = os.path.splitext(str(file_name))[0]
    out_path = get_unique_filename(output_folder, base_name, ext)

    bg_rgb = hex_to_rgb(background_color)

    if resize_mode == "Resize with Padding":
        if crop_white:
            img = crop_white_background(img)

        inner_width = max(1, output_width - 2 * margin_px)
        inner_height = max(1, output_height - 2 * margin_px)

        img.thumbnail((inner_width, inner_height), Image.LANCZOS)

        if enlarge_image:
            scale = zoom_percent / 100
            new_width = int(img.width * scale)
            new_height = int(img.height * scale)

            img = img.resize((new_width, new_height), Image.LANCZOS)

            if img.width > inner_width or img.height > inner_height:
                img.thumbnail((inner_width, inner_height), Image.LANCZOS)

        canvas = Image.new("RGB", (output_width, output_height), bg_rgb)

        left = (output_width - img.width) // 2
        top = (output_height - img.height) // 2

        canvas.paste(img, (left, top))
        save_image(canvas, out_path, output_format, output_dpi, quality)

    else:
        if crop_white:
            img = crop_white_background(img)

        img.thumbnail((output_width, output_height), Image.LANCZOS)
        save_image(img, out_path, output_format, output_dpi, quality)

    return out_path

st.divider()

if st.button("🚀 Process Images"):
    output_folder = "downloaded_images"
    zip_base_name = "downloaded_images"
    zip_path = f"{zip_base_name}.zip"

    clean_folder(output_folder)

    if os.path.exists(zip_path):
        os.remove(zip_path)

    images_processed = 0
    margin_px = cm_to_pixels(margin_cm, output_dpi)

    failed_report = []
    preview_images = []

    df = None
    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file)
        except Exception as e:
            st.error(f"❌ Error reading Excel file: {e}")
            failed_report.append({
                "Source": "Excel File",
                "FileName": "Uploaded Excel",
                "Link": "",
                "Error": str(e)
            })

    column_pairs = []
    if file_col1 and link_col1:
        column_pairs.append((file_col1, link_col1))
    if file_col2 and link_col2:
        column_pairs.append((file_col2, link_col2))

    step_total = 0
    if uploaded_images:
        step_total += len(uploaded_images)
    if df is not None:
        step_total += len(df) * len(column_pairs)

    progress_bar = st.progress(0, text="Starting image processing...")
    current_step = 0

    if uploaded_images:
        for img_file in uploaded_images:
            try:
                out_path = process_image(
                    img_file,
                    img_file.name,
                    margin_px,
                    output_folder,
                    int(output_width),
                    int(output_height),
                    int(output_dpi),
                    resize_mode,
                    crop_white,
                    enlarge_image,
                    zoom_percent,
                    output_format,
                    quality,
                    background_color
                )

                images_processed += 1

                if len(preview_images) < 5:
                    preview_images.append(out_path)

            except Exception as e:
                st.warning(f"⚠️ Failed uploaded image `{img_file.name}`: {e}")
                failed_report.append({
                    "Source": "Direct Upload",
                    "FileName": img_file.name,
                    "Link": "",
                    "Error": str(e)
                })

            current_step += 1
            progress_bar.progress(current_step / max(1, step_total))

    if df is not None:
        try:
            for _, row in df.iterrows():
                for filename_col, link_col in column_pairs:
                    filename = row.get(filename_col)
                    link = row.get(link_col)

                    if pd.notna(filename) and pd.notna(link):
                        try:
                            response = requests.get(str(link), timeout=15)
                            response.raise_for_status()

                            img_bytes = BytesIO(response.content)

                            out_path = process_image(
                                img_bytes,
                                filename,
                                margin_px,
                                output_folder,
                                int(output_width),
                                int(output_height),
                                int(output_dpi),
                                resize_mode,
                                crop_white,
                                enlarge_image,
                                zoom_percent,
                                output_format,
                                quality,
                                background_color
                            )

                            images_processed += 1

                            if len(preview_images) < 5:
                                preview_images.append(out_path)

                        except Exception as e:
                            st.warning(f"⚠️ Failed: `{filename}` from `{link}`: {e}")
                            failed_report.append({
                                "Source": "Excel Link",
                                "FileName": filename,
                                "Link": link,
                                "Error": str(e)
                            })

                    current_step += 1
                    progress_bar.progress(current_step / max(1, step_total))

        except Exception as e:
            st.error(f"❌ Error processing Excel data: {e}")
            failed_report.append({
                "Source": "Excel Processing",
                "FileName": "",
                "Link": "",
                "Error": str(e)
            })

    failed_csv_path = None

    if failed_report:
        failed_df = pd.DataFrame(failed_report)
        failed_csv_path = os.path.join(output_folder, "failed_image_report.csv")
        failed_df.to_csv(failed_csv_path, index=False)

    if preview_enabled and preview_images:
        st.subheader("Preview of Processed Images")
        for preview_path in preview_images:
            st.image(preview_path, caption=os.path.basename(preview_path), use_container_width=True)

    if images_processed > 0:
        zip_path = shutil.make_archive(zip_base_name, "zip", output_folder)

        with open(zip_path, "rb") as zf:
            zip_data = zf.read()

        st.success(f"✅ Done! Processed {images_processed} images.")

        st.download_button(
            "⬇️ Download all as ZIP",
            data=zip_data,
            file_name="downloaded_images.zip",
            mime="application/zip"
        )

    else:
        st.info("No images processed yet. Upload/select files and try again!")

    if failed_report:
        failed_df = pd.DataFrame(failed_report)
        csv_data = failed_df.to_csv(index=False).encode("utf-8")

        st.warning(f"⚠️ {len(failed_report)} image(s) failed. Download failed report below.")

        st.download_button(
            "⬇️ Download Failed Image Report",
            data=csv_data,
            file_name="failed_image_report.csv",
            mime="text/csv"
        )

    progress_bar.empty()

st.caption("Made by Sparsh Neema")
