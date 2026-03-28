__module_name__ = "uploader"

import os

UPLOAD_DIR = "data/uploads"


def handle_upload(uploaded_file) -> str:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path
