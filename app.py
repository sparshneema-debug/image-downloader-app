import streamlit as st
import pandas as pd
import requests
import os
import shutil
from io import BytesIO
from PIL import Image, ImageChops

st.set_page_config(page_title="Complete Image Tool", layout="centered")

st.title("🖼️ Complete Image Downloader & Converter")

st.write("Upload images directly or upload an Excel file with image links. Resize, crop, convert, preview, and download ZIP.")

st.header("① Directly Upload Images")
uploaded_images = st.file_uploader(
    "Upload images",
    type=["jpg", "jpeg", "png", "webp", "bmp", "tiff"],
    accept_multiple_files=True
)

st.header("② Or Upload Excel File with Image Links")
uploaded_file = st.file_uploader("Excel file (.xlsx)", type=["xlsx"])

image_url_column = st.text_input("Image URL Column Name", value="Image URL")
filename_column = st.text_input("Filename Column Name", value="Filename")

st.header("③ Image Output Settings")

output_width = st.number_input("Output width", min_value=100, max_value=5000, value=2200, step=10)
output_height = st.number_input("Output height", min_value=100, max_value=5000, value=2200, step=10)
output_dpi = st.number_input("DPI", min_value=50, max_value=1200, value=300, step=1)

output_format = st.selectbox("Output Format", ["JPG", "PNG", "WEBP"])
quality = st.slider("Image Quality", min_value=40, max_value=100, value=95)
background_color = st.color_picker("Background Color", "#FFFFFF")

resize_mode = st.radio(
    "Image Processing Mode",
    ["Resize with Padding", "Resize without Padding"],
    horizontal=True
)

crop_white = st.checkbox("Crop White Background", value=True)

auto_fill_enabled = False
fill_percent = 90
margin_cm = 0.5

if resize_mode == "Resize with Padding":
    auto_fill_enabled = st.checkbox("Auto Fill Canvas", value=True)

    if auto_fill_enabled:
        fill_percent = st.slider("Product Fill Target (%)", 85, 95, 90, 1)

    margin_cm = st.number_input("Margin (cm)", min_value=0.0, max_value=10.0, value=0.5, step=0.1)

preview_enabled = st.checkbox("Preview first 5 processed images", value=True)

process_button = st.button("🚀 Process Images")


def cm_to_pixels(cm, dpi):
    return int((cm / 2.54) * dpi)


def hex_to_rgb(hex_color):
    hex_color = hex_color.replace("#", "")
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def reset_folder(folder_path):
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)
    os.makedirs(folder_path, exist_ok=True)


def get_extension(fmt):
    return {"JPG": ".jpg", "PNG": ".png", "WEBP": ".webp"}[fmt]


def get_pil_format(fmt):
    return {"JPG": "JPEG", "PNG": "PNG", "WEBP": "WEBP"}[fmt]


def safe_filename(name):
    name = os.path.splitext(str(name))[0]
    name = "".join(c for c in name if c not in r'\/:*?"<>|').strip()

    if not name or name.lower() == "nan":
        name = "image"

    return name


def crop_white_background(img):
    img = img.convert("RGB")
    bg = Image.new("RGB", img.size, (255, 255, 255))
    diff = ImageChops.difference(img, bg).convert("L")
    bbox = diff.point(lambda p: 255 if p > 10 else 0).getbbox()

    if bbox:
        return img.crop(bbox)

    return img


def save_image(img, path, fmt, dpi, quality):
    pil_format = get_pil_format(fmt)

    if fmt == "JPG":
        img = img.convert("RGB")
        img.save(path, format=pil_format, dpi=(dpi, dpi), quality=quality, optimize=True)

    elif fmt == "PNG":
        img.save(path, format=pil_format, dpi=(dpi, dpi), optimize=True)

    elif fmt == "WEBP":
        img = img.convert("RGB")
        img.save(path, format=pil_format, quality=quality, method=6)


def get_unique_output_path(output_folder, file_name, fmt):
    base_name = safe_filename(file_name)
    ext = get_extension(fmt)

    output_path = os.path.join(output_folder, base_name + ext)
    counter = 1

    while os.path.exists(output_path):
        output_path = os.path.join(output_folder, f"{base_name}_{counter}{ext}")
        counter += 1

    return output_path


def process_image(image_source, file_name, output_folder):
    img = Image.open(image_source).convert("RGB")

    if crop_white:
        img = crop_white_background(img)

    bg_rgb = hex_to_rgb(background_color)
    output_path = get_unique_output_path(output_folder, file_name, output_format)

    if resize_mode == "Resize with Padding":
        margin_px = cm_to_pixels(margin_cm, int(output_dpi))

        inner_width = max(1, int(output_width) - 2 * margin_px)
        inner_height = max(1, int(output_height) - 2 * margin_px)

        if auto_fill_enabled:
            target_w = int(output_width * (fill_percent / 100))
            target_h = int(output_height * (fill_percent / 100))

            scale = min(target_w / img.width, target_h / img.height)
            new_width = max(1, int(img.width * scale))
            new_height = max(1, int(img.height * scale))

            img = img.resize((new_width, new_height), Image.LANCZOS)

            if img.width > inner_width or img.height > inner_height:
                img.thumbnail((inner_width, inner_height), Image.LANCZOS)
        else:
            img.thumbnail((inner_width, inner_height), Image.LANCZOS)

        canvas = Image.new("RGB", (int(output_width), int(output_height)), bg_rgb)

        left = (int(output_width) - img.width) // 2
        top = (int(output_height) - img.height) // 2

        canvas.paste(img, (left, top))
        final_img = canvas

    else:
        img.thumbnail((int(output_width), int(output_height)), Image.LANCZOS)
        final_img = img

    save_image(final_img, output_path, output_format, int(output_dpi), quality)

    return output_path


if process_button:
    output_folder = "processed_images"
    reset_folder(output_folder)

    processed_files = []
    failed_rows = []

    if uploaded_images:
        for img_file in uploaded_images:
            try:
                output_path = process_image(img_file, img_file.name, output_folder)
                processed_files.append(output_path)
            except Exception as e:
                failed_rows.append({
                    "FileName": img_file.name,
                    "Source": "Direct Upload",
                    "Error": str(e)
                })

    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file)

            if image_url_column not in df.columns:
                st.error(f"Column '{image_url_column}' not found in Excel.")
            else:
                for index, row in df.iterrows():
                    link = row.get(image_url_column)

                    if filename_column in df.columns:
                        file_name = row.get(filename_column)
                    else:
                        file_name = f"image_{index + 1}"

                    try:
                        if pd.isna(link) or str(link).strip() == "":
                            raise Exception("Empty image URL")

                        response = requests.get(str(link), timeout=20)
                        response.raise_for_status()

                        image_bytes = BytesIO(response.content)
                        output_path = process_image(image_bytes, file_name, output_folder)
                        processed_files.append(output_path)

                    except Exception as e:
                        failed_rows.append({
                            "FileName": file_name,
                            "Source": "Excel Link",
                            "Link": link,
                            "Error": str(e)
                        })

        except Exception as e:
            st.error(f"Could not read Excel file: {e}")

    if processed_files:
        st.success(f"✅ Done! {len(processed_files)} image(s) processed.")

        if preview_enabled:
            st.subheader("Preview")
            for path in processed_files[:5]:
                st.image(path, caption=os.path.basename(path), use_container_width=True)

        zip_path = shutil.make_archive("downloaded_images", "zip", output_folder)

        with open(zip_path, "rb") as zip_file:
            st.download_button(
                "⬇️ Download ZIP",
                data=zip_file,
                file_name="downloaded_images.zip",
                mime="application/zip"
            )
    else:
        st.warning("No images processed.")

    if failed_rows:
        failed_df = pd.DataFrame(failed_rows)
        csv_data = failed_df.to_csv(index=False).encode("utf-8")

        st.warning(f"⚠️ {len(failed_rows)} image(s) failed.")

        st.download_button(
            "⬇️ Download Failed Report",
            data=csv_data,
            file_name="failed_image_report.csv",
            mime="text/csv"
        )
