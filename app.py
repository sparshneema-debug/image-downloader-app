import os
import re
import shutil
import tempfile
from io import BytesIO

import pandas as pd
import requests
from PIL import Image
import streamlit as st


# ----------------------------
# Helpers
# ----------------------------
def safe_filename(name: str, default: str = "image") -> str:
    """
    Make a safe filename (no weird chars), ensure .jpg extension.
    """
    if name is None or str(name).strip() == "" or str(name).lower() == "nan":
        name = default
    name = str(name).strip()

    # Remove extension, sanitize, then add .jpg
    name_no_ext = os.path.splitext(name)[0]
    name_no_ext = re.sub(r"[^\w\-. ]+", "_", name_no_ext).strip()
    name_no_ext = re.sub(r"\s+", "_", name_no_ext)

    if not name_no_ext:
        name_no_ext = default

    return f"{name_no_ext}.jpg"


def download_image(url: str, timeout: int = 15) -> Image.Image:
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; image-downloader/1.0)"
    }
    r = requests.get(url, timeout=timeout, headers=headers)
    r.raise_for_status()
    img = Image.open(BytesIO(r.content)).convert("RGB")
    return img


def resize_pad_white(img: Image.Image, size=(2200, 2200)) -> Image.Image:
    """
    Resize maintaining aspect ratio, then pad to exact size with white background.
    """
    img_copy = img.copy()
    img_copy.thumbnail(size, Image.Resampling.LANCZOS)

    canvas = Image.new("RGB", size, (255, 255, 255))
    left = (size[0] - img_copy.width) // 2
    top = (size[1] - img_copy.height) // 2
    canvas.paste(img_copy, (left, top))
    return canvas


def make_zip(folder_path: str, zip_base_path_no_ext: str) -> str:
    """
    Creates zip and returns full zip path.
    """
    zip_path = shutil.make_archive(zip_base_path_no_ext, "zip", folder_path)
    return zip_path


# ----------------------------
# Streamlit App
# ----------------------------
st.set_page_config(page_title="Excel Image Downloader", layout="wide")
st.title("📥 Excel Image Downloader → Resize/Pad → JPG → ZIP")

st.write(
    "Upload an Excel file containing filename + image URL columns. "
    "This app downloads each image, converts to JPG, resizes with padding to a fixed square, and provides a ZIP."
)

uploaded = st.file_uploader("Upload Excel (.xlsx)", type=["xlsx"])

col1, col2, col3 = st.columns(3)
with col1:
    target_w = st.number_input("Target width", min_value=100, max_value=5000, value=2200, step=50)
with col2:
    target_h = st.number_input("Target height", min_value=100, max_value=5000, value=2200, step=50)
with col3:
    timeout = st.number_input("Download timeout (seconds)", min_value=3, max_value=120, value=15, step=1)

if uploaded is not None:
    try:
        df = pd.read_excel(uploaded)
    except Exception as e:
        st.error(f"Could not read Excel: {e}")
        st.stop()

    st.subheader("Preview")
    st.dataframe(df.head(20), use_container_width=True)

    st.subheader("Select your (filename, link) column pairs")
    st.caption("Pick as many pairs as you need. Each pair = one filename column + one URL column.")

    columns = list(df.columns)

    # how many pairs user wants
    num_pairs = st.number_input("Number of column pairs", min_value=1, max_value=20, value=2, step=1)

    pairs = []
    for i in range(int(num_pairs)):
        c1, c2 = st.columns(2)
        with c1:
            fname_col = st.selectbox(f"Filename column #{i+1}", options=columns, key=f"fname_{i}")
        with c2:
            link_col = st.selectbox(f"Image link column #{i+1}", options=columns, key=f"link_{i}")
        pairs.append((fname_col, link_col))

    st.divider()

    if st.button("🚀 Download + Convert + ZIP", type="primary"):
        resize_to = (int(target_w), int(target_h))

        # Work in a temp directory so Streamlit Cloud/local stays clean
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = os.path.join(tmpdir, "downloaded_images")
            os.makedirs(out_dir, exist_ok=True)

            progress = st.progress(0)
            status = st.empty()

            total_attempts = 0
            for _, row in df.iterrows():
                for _, _ in pairs:
                    total_attempts += 1

            done = 0
            success = 0
            failures = []

            # Optional: avoid overwriting duplicate filenames
            seen_names = {}

            for ridx, row in df.iterrows():
                for filename_col, link_col in pairs:
                    done += 1
                    progress.progress(min(done / max(total_attempts, 1), 1.0))

                    filename_val = row.get(filename_col)
                    link_val = row.get(link_col)

                    if pd.isna(filename_val) or pd.isna(link_val):
                        continue

                    url = str(link_val).strip()
                    if not url:
                        continue

                    # build output name
                    base_name = safe_filename(filename_val, default=f"row{ridx+1}")
                    # ensure uniqueness
                    if base_name in seen_names:
                        seen_names[base_name] += 1
                        name_no_ext = os.path.splitext(base_name)[0]
                        base_name = f"{name_no_ext}_{seen_names[base_name]}.jpg"
                    else:
                        seen_names[base_name] = 1

                    try:
                        status.write(f"Downloading: `{base_name}`")
                        img = download_image(url, timeout=int(timeout))
                        final_img = resize_pad_white(img, size=resize_to)

                        out_path = os.path.join(out_dir, base_name)
                        final_img.save(out_path, format="JPEG", quality=95, optimize=True)
                        success += 1
                    except Exception as e:
                        failures.append((str(filename_val), url, str(e)))

            # Safety: remove any non-jpg (shouldn't happen, but keeps your original intent)
            for fname in os.listdir(out_dir):
                if not fname.lower().endswith(".jpg"):
                    try:
                        os.remove(os.path.join(out_dir, fname))
                    except Exception:
                        pass

            zip_path = make_zip(out_dir, os.path.join(tmpdir, "downloaded_images"))

            st.success(f"Done! ✅ Saved {success} JPG(s). Failed: {len(failures)}")

            if failures:
                with st.expander("Show failures"):
                    st.dataframe(
                        pd.DataFrame(failures, columns=["Filename", "URL", "Error"]),
                        use_container_width=True
                    )

            # Provide a Streamlit download button
            with open(zip_path, "rb") as f:
                st.download_button(
                    label="⬇️ Download downloaded_images.zip",
                    data=f,
                    file_name="downloaded_images.zip",
                    mime="application/zip",
                )

            # Show a few sample outputs
            st.subheader("Sample output preview")
            jpgs = [os.path.join(out_dir, x) for x in os.listdir(out_dir) if x.lower().endswith(".jpg")]
            jpgs = sorted(jpgs)[:8]
            if jpgs:
                st.image(jpgs, use_container_width=True)
            else:
                st.info("No JPGs were generated.")
