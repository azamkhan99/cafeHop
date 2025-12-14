import streamlit as st
import boto3
import io
from PIL import Image
import os
from dotenv import load_dotenv
import requests
from imageio import imread
from pillow_heif import register_heif_opener
from function.utils import get_image_lat_long

register_heif_opener()
load_dotenv()

# AWS Credentials
AWS_ACCESS_KEY = os.environ["AWS_ACCESS_KEY_ID"]
AWS_SECRET_KEY = os.environ["AWS_SECRET_ACCESS_KEY"]
BUCKET_NAME = os.environ["BUCKET_NAME"]

# Initialize S3 Client
s3_client = boto3.client(
    "s3", aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY
)


def convert_to_jpg(image):
    """Convert an image to JPG format while keeping metadata."""
    img_byte_arr = io.BytesIO()
    if image.format != "JPEG":
        img = image.convert("RGB")
        img.save(img_byte_arr, format="JPEG", exif=image.info.get("exif"))
    else:
        image.save(img_byte_arr, format="JPEG", exif=image.info.get("exif"))
    return img_byte_arr.getvalue()


def upload_to_s3(file, filename, metadata):
    """Upload a file to S3."""
    try:
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=filename,
            Body=file,
            ContentType="image/jpeg",
            Metadata=metadata,
        )
        return f"https://{BUCKET_NAME}.s3.amazonaws.com/{filename}"
    except Exception as e:
        return str(e)


@st.dialog("Rename Image")
def rename_convert_upload(image):
    filename = st.text_input("Enter a filename:", placeholder="Location_X_STARS")
    filename = f"{filename}.jpg"
    if st.button("Upload"):
        jpg_image = convert_to_jpg(image)
        latitude, longitude = get_image_lat_long(jpg_image)
        image_gps = {
            "latitude": str(latitude),
            "longitude": str(longitude),
        }
        s3_url = upload_to_s3(jpg_image, filename, image_gps)
        st.toast(f"Image uploaded successfully!")
        st.session_state.rename_convert_upload = s3_url
        st.rerun()


# Streamlit UI
with st.container(border=True):
    st.header("Azam's NYC Cafe Hop Upload")

    uploaded_file = st.file_uploader(
        "Choose an image...", type=["jpg", "png", "jpeg", "heic"]
    )
    st.header("Capture a photo instead?")
    enable = st.toggle("Enable Camera")
    if enable:
        uploaded_file = st.camera_input("Take a photo", disabled=not enable)
        # capture = True

    if "rename_convert_upload" not in st.session_state:
        if uploaded_file:
            image = Image.open(uploaded_file)
            rename_convert_upload(image)
            # st.image(image, caption="Uploaded Image")
            # st.write(st.session_state.rename_convert_upload)
    else:
        # st.image(st.session_state.rename_convert_upload, caption="Recently Uploaded Image")
        st.write(f"Uploaded to {st.session_state.rename_convert_upload}")

    # if not enable:
    #     st.image(image, caption="Uploaded Image")

    # # Convert to JPG
    # jpg_image = convert_to_jpg(image)

    # # Generate a unique filename
    # filename = st.text_input("Enter a filename:", placeholder="Location_X_STARS")
    # filename = f"{filename}.jpg"

    # # Upload to S3
    # if st.button("Upload"):
    #     s3_url = upload_to_s3(jpg_image, filename)
    #     st.success(f"Image uploaded successfully!")

st.header("Recent Uploads")
response = s3_client.list_objects_v2(Bucket=BUCKET_NAME)

if "Contents" in response:
    # Sort objects by LastModified timestamp in descending order
    sorted_objects = sorted(
        response["Contents"], key=lambda obj: obj["LastModified"], reverse=True
    )

    # Get the most recent 'count' objects
    recent_files = sorted_objects[:3]

    # Display the most recent 'count' objects
    col1, col2, col3 = st.columns(3)
    for col, obj in zip([col1, col2, col3], recent_files):
        if not obj["Key"].endswith("unvisited.jpg"):
            image_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{obj['Key']}"
            caption = obj["Key"].split(".")[0]
            stars = caption.split("_")[-2]
            cafe = caption.split("_")[0]
            date = obj["LastModified"].strftime("%Y-%m-%d")
            caption = f"{cafe} ({stars} stars) \n {date}"

            col.image(image_url, caption=caption, use_container_width=True)

else:
    st.write("No images uploaded yet.")
