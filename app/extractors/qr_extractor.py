import cv2


def decode_qr_from_image_path(image_path: str = "qr.jpg") -> str | None:
    img_bgr = cv2.imread(image_path)
    if img_bgr is None:
        raise FileNotFoundError(f"Could not read image at path: {image_path}")

    try:
        from qreader import QReader

        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        qreader = QReader()
        detected_text = qreader.detect_and_decode(image=img_rgb)

        if isinstance(detected_text, list):
            detected_text = next((t for t in detected_text if t), None)
        return detected_text
    except Exception:
        detector = cv2.QRCodeDetector()
        data, _, _ = detector.detectAndDecode(img_bgr)
        return data or None


if __name__ == "__main__":
    print(decode_qr_from_image_path("qr.jpg"))
