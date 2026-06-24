import streamlit as st
import pandas as pd
import requests
import os
from PIL import Image, ImageChops
from io import BytesIO
import shutil

st.set_page_config(page_title="Complete Image Tool", layout="centered")

st.title("🖼️ Complete Image Downloader & Converter")

st.markdown("""
Upload images directly **or** provide an Excel file with image links.  
Resize, crop, change background color, convert format, check Amazon compliance, preview, and download ZIP.
""")

try:
    from rembg import remove
    REMBG_AVAILABLE = True
except Exception:
    REMBG_AVAILABLE = False

st.header("① Directly Upload Images")

uploaded_images = st.file_uploader(
    "Drag and drop or browse for images",
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
    image_url_column = st.text_input("Image URL Column Name", value="Image URL")

with col2:
    filename_column = st.text_input("Filename Column Name", value="Filename")

st.divider()

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

remove_background = st.checkbox(
    "Remove Background using rembg",
    value=False,
    help="For transparent output, choose PNG."
)

if remove_background and not REMBG_AVAILABLE:
    st.error("rembg is not installed. Add rembg and onnxruntime to requirements.txt")

crop_white = False
auto_fill_enabled = False
fill_percent = 90
margin_cm = 0.0

if resize_mode == "Resize with Padding":
    crop_white = st.checkbox("Crop White Background", value=True)

    auto_fill_enabled = st.checkbox(
        "Auto Fill Canvas",
        value=True,
        help="Automatically sizes product to fill selected canvas percentage."
    )

    if auto_fill_enabled:
        fill_percent = st.slider(
            "Product Fill Target (%)",
            min_value=85,
            max_value=95,
            value=90,
            step=1
        )

    margin_cm = st.number_input(
        "Margin (cm)",
        min_value=0.0,
        max_value=10.0,
        value=0.5,
        step=0.1
    )

amazon_check = st.checkbox("Amazon Compliance Checker", value=True)
preview_enabled = st.checkbox("Preview first 5 processed images", value=True)


def cm_to_pixels(cm, dpi):
    return int((cm / 2.54) * dpi)


def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def reset_folder(folder_path):
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)
    os.makedirs(folder_path, exist_ok=True)


def get_extension(fmt):
    return {"JPG": ".jpg", "PNG": ".png", "WEBP": ".webp"}[fmt]


def get_pil_format(fmt):
    return {"JPG": "JPEG", "PNG": "PNG", "WEBP": "WEBP"}[fmt]


def get_unique_filename(output_folder, base_name, ext):
    safe_name = "".join(c for c in str(base_name) if c not in r'\/:*?"<>|').strip()

    if not safe_name or safe_name.lower() == "nan":
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


def apply_rembg(img):
    img_rgba = img.convert("RGBA")
    output = remove(img_rgba)
    return output.convert("RGBA")


def paste_on_background(img, bg_rgb):
    if img.mode == "RGBA":
        canvas = Image.new("RGBA", img.size, bg_rgb + (255,))
        canvas.alpha_composite(img)
        return canvas.convert("RGB")

    return img.convert("RGB")


def get_product_bbox_on_canvas(img, bg_rgb):
    rgb_img = img.convert("RGB")
    bg = Image.new("RGB", rgb_img.size, bg_rgb)
    diff = ImageChops.difference(rgb_img, bg).convert("L")
    mask = diff.point(lambda p: 255 if p > 12 else 0)
    return mask.getbbox()


def amazon_compliance_result(img, bg_rgb):
    width, height = img.size
    bbox = get_product_bbox_on_canvas(img, bg_rgb)

    product_fill = 0

    if bbox:
        product_w = bbox[2] - bbox[0]
        product_h = bbox[3] - bbox[1]
        product_fill = round(max(product_w / width, product_h / height) * 100, 2)

    issues = []

    if width != height:
        issues.append("Image is not square")

    if width < 1000 or height < 1000:
        issues.append("Image is below 1000px")

    if product_fill < 85:
        issues.append("Product fills less than 85% of canvas")

    if bg_rgb != (255, 255, 255):
        issues.append("Background is not pure white")

    status = "Pass" if not issues else "Review"

    return status, product_fill, "; ".join(issues) if issues else "Looks good"


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
    auto_fill_enabled,
    fill_percent,
    output_format,
    quality,
    background_color,
    remove_background
):
    img = Image.open(image_source)

    if remove_background and REMBG_AVAILABLE:
        img = apply_rembg(img)
    else:
        img = img.convert("RGB")

    ext = get_extension(output_format)
    base_name = os.path.splitext(str(file_name))[0]
    out_path = get_unique_filename(output_folder, base_name, ext)
    bg_rgb = hex_to_rgb(background_color)

    if resize_mode == "Resize with Padding":
        if crop_white and not remove_background:
            img = crop_white_background(img)

        if remove_background:
            bbox = img.getbbox()
            if bbox:
                img = img.crop(bbox)

        inner_width = max(1, output_width - 2 * margin_px)
        inner_height = max(1, output_height - 2 * margin_px)

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

        if remove_background and output_format == "PNG":
            canvas = Image.new("RGBA", (output_width, output_height), bg_rgb + (0,))
            left = (output_width - img.width) // 2
            top = (output_height - img.height) // 2
            canvas.alpha_composite(img.convert("RGBA"), (left, top))
            final_img = canvas

        else:
            canvas = Image.new("RGB", (output_width, output_height), bg_rgb)
            left = (output_width - img.width) // 2
            top = (output_height - img.height) // 2

            if img.mode == "RGBA":
                temp_bg = Image.new("RGB", img.size, bg_rgb)
                temp_bg.paste(img, mask=img.split()[3])
                img = temp_bg
            else:
                img = img.convert("RGB")

            canvas.paste(img, (left, top))
            final_img = canvas

    else:
        if crop_white and not remove_background:
            img = crop_white_background(img)

        if remove_background:
            bbox = img.getbbox()
            if bbox:
                img = img.crop(bbox)

        img.thumbnail((output_width, output_height), Image.LANCZOS)

        if img.mode == "RGBA" and output_format != "PNG":
            final_img = paste_on_background(img, bg_rgb)
        else:
            final_img = img

    save_image(final_img, out_path, output_format, output_dpi, quality)

    return out_path, final_img


st.divider()

process_button = st.button("🚀 Process Images")

if process_button:
    output_folder = "processed_images"
    zip_base_name = "downloaded_images"

    reset_folder(output_folder)

    images_processed = 0
    margin_px = cm_to_pixels(margin_cm, output_dpi)

    failed_report = []
    compliance_report = []
    preview_images = []

    df = None

    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file)
        except Exception as e:
            st.error(f"Could not read Excel file: {e}")

    total_items = 0

    if uploaded_images:
        total_items += len(uploaded_images)

    if df is not None and image_url_column in df.columns:
        total_items += len(df)

    if total_items == 0:
        st.warning("Please upload images or an Excel file with valid image links.")
        st.stop()

    progress_bar = st.progress(0, text="Starting image processing...")
    current_step = 0

    def update_progress():
        progress_value = min(current_step / total_items, 1.0)
        progress_bar.progress(
            progress_value,
            text=f"Processing {current_step} of {total_items}"
        )

    def handle_processed_image(out_path, final_img, file_name, source, link=""):
        if amazon_check:
            status, product_fill, issues = amazon_compliance_result(
                final_img,
                hex_to_rgb(background_color)
            )

            compliance_report.append({
                "FileName": file_name,
                "Source": source,
                "Link": link,
                "Width": final_img.size[0],
                "Height": final_img.size[1],
                "OutputFormat": output_format,
                "ProductFillPercent": product_fill,
                "AmazonStatus": status,
                "Notes": issues
            })

        if len(preview_images) < 5:
            preview_images.append(out_path)

    if uploaded_images:
        for img_file in uploaded_images:
            try:
                out_path, final_img = process_image(
                    img_file,
                    img_file.name,
                    margin_px,
                    output_folder,
                    int(output_width),
                    int(output_height),
                    int(output_dpi),
                    resize_mode,
                    crop_white,
                    auto_fill_enabled,
                    fill_percent,
                    output_format,
                    quality,
                    background_color,
                    remove_background
                )

                images_processed += 1
                handle_processed_image(
                    out_path,
                    final_img,
                    img_file.name,
                    "Direct Upload"
                )

            except Exception as e:
                st.warning(f"⚠️ Failed uploaded image `{img_file.name}`: {e}")

                failed_report.append({
                    "FileName": img_file.name,
                    "Source": "Direct Upload",
                    "Link": "",
                    "Error": str(e)
                })

            current_step += 1
            update_progress()

    if df is not None:
        if image_url_column not in df.columns:
            st.error(f"Column `{image_url_column}` not found in Excel.")

        else:
            for index, row in df.iterrows():
                link = row.get(image_url_column)

                if filename_column in df.columns:
                    filename = row.get(filename_column)
                else:
                    filename = f"image_{index + 1}"

                try:
                    if pd.isna(link) or str(link).strip() == "":
                        raise Exception("Empty image URL")

                    response = requests.get(str(link), timeout=20)
                    response.raise_for_status()

                    img_bytes = BytesIO(response.content)

                    out_path, final_img = process_image(
                        img_bytes,
                        filename,
                        margin_px,
                        output_folder,
                        int(output_width),
                        int(output_height),
                        int(output_dpi),
                        resize_mode,
                        crop_white,
                        auto_fill_enabled,
                        fill_percent,
                        output_format,
                        quality,
                        background_color,
                        remove_background
                    )

                    images_processed += 1

                    handle_processed_image(
                        out_path,
                        final_img,
                        filename,
                        "Excel Link",
                        link
                    )

                except Exception as e:
                    st.warning(f"⚠️ Failed: `{filename}` from `{link}`: {e}")

                    failed_report.append({
                        "FileName": filename,
                        "Source": "Excel Link",
                        "Link": link,
                        "Error": str(e)
                    })

                current_step += 1
                update_progress()

    if failed_report:
        failed_df = pd.DataFrame(failed_report)
        failed_df.to_csv(
            os.path.join(output_folder, "failed_image_report.csv"),
            index=False
        )

    if compliance_report:
        compliance_df = pd.DataFrame(compliance_report)
        compliance_df.to_csv(
            os.path.join(output_folder, "amazon_compliance_report.csv"),
            index=False
        )

    if preview_enabled and preview_images:
        st.subheader("Preview of Processed Images")

        for preview_path in preview_images:
            st.image(
                preview_path,
                caption=os.path.basename(preview_path),
                use_container_width=True
            )

    if amazon_check and compliance_report:
        st.subheader("Amazon Compliance Summary")

        compliance_df = pd.DataFrame(compliance_report)
        st.dataframe(compliance_df, use_container_width=True)

        pass_count = len(compliance_df[compliance_df["AmazonStatus"] == "Pass"])
        review_count = len(compliance_df[compliance_df["AmazonStatus"] == "Review"])

        st.info(f"✅ Pass: {pass_count} | ⚠️ Review: {review_count}")

    if images_processed > 0:
        zip_path = shutil.make_archive(zip_base_name, "zip", output_folder)

        st.success(f"✅ Done! {images_processed} image(s) processed.")

        with open(zip_path, "rb") as zip_file:
            st.download_button(
                "⬇️ Download ZIP",
                data=zip_file,
                file_name="downloaded_images.zip",
                mime="application/zip"
            )

    else:
        st.info("No images processed yet. Upload/select files and try again!")

    if failed_report:
        failed_df = pd.DataFrame(failed_report)
        csv_data = failed_df.to_csv(index=False).encode("utf-8")

        st.warning(f"⚠️ {len(failed_report)} image(s) failed.")

        st.download_button(
            "⬇️ Download Failed Image Report",
            data=csv_data,
            file_name="failed_image_report.csv",
            mime="text/csv"
        )
