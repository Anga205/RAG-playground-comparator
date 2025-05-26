import base64
import io
import fitz
from PIL import Image
import pytesseract

def extract_text_from_images(doc) -> str:
    img_texts = []
    for page_index in range(len(doc)):
        images = doc.get_page_images(page_index)
        for img_index, img in enumerate(images):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            img_ext = base_image["ext"]
            image = Image.open(io.BytesIO(image_bytes))
            text = pytesseract.image_to_string(image)
            if text.strip():
                img_texts.append(f"[Image Text Page {page_index + 1} Image {img_index + 1}]\n{text.strip()}")
    return "\n\n".join(img_texts)

def extract_pdf_text_from_base64(b64_pdf: str) -> str:
    pdf_bytes = base64.b64decode(b64_pdf)
    pdf_stream = io.BytesIO(pdf_bytes)
    output = []

    with fitz.open(stream=pdf_stream, filetype="pdf") as doc:
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            if text.strip():
                output.append(f"[Page {page_num + 1} Text]\n{text.strip()}")

        ocr_text = extract_text_from_images(doc)
        if ocr_text:
            output.append("[OCR Extracted Text]\n" + ocr_text)

    return "\n\n".join(output)


def load_pdf_as_base64(pdf_path: str) -> str:
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    return base64.b64encode(pdf_bytes).decode("utf-8")

if __name__ == "__main__":
    pdf_path = "sample_text.pdf"
    b64_pdf = load_pdf_as_base64(pdf_path)
    extracted_text = extract_pdf_text_from_base64(b64_pdf)
    print(extracted_text)