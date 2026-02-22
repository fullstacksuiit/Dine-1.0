import base64
import qrcode

from qrcode.image.pil import PilImage
from PIL import ImageDraw, ImageFont

from io import BytesIO


class QRService:
    @classmethod
    def generate_qr_code_for_payment(cls, amount: str, note: str, upi_id: str):
        if not upi_id:
            return None

        upi_uri = f"upi://pay?pa={upi_id}&am={amount}&tn={note}&cu=INR"
        # Generate the QR code image
        img = qrcode.make(upi_uri)

        # Convert the image to a BytesIO buffer
        buffered = BytesIO()
        img.save(buffered, format="PNG")

        # Encode the buffer to a Base64 string
        img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return img_b64

    @classmethod
    def generate_qr_for_url(cls, url: str, restaurant_name: str):
        # Generate QR code with whitespace (border)
        qr = qrcode.QRCode(box_size=10, border=6)  # Increased border for whitespace
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="white", back_color="black", image_factory=PilImage)
        if hasattr(img, 'get_image'):
            img = img.get_image().convert('RGBA')
        else:
            img = img.convert('RGBA')

        # Only draw restaurant name if present and non-empty
        if restaurant_name:
            draw = ImageDraw.Draw(img)
            width, height = img.size
            # Try several monospaced fonts commonly available on macOS, Linux, and Windows
            font = None
            font_candidates = [
                "Menlo.ttc",           # macOS
                "Courier New.ttf",     # Windows/macOS
                "DejaVuSansMono.ttf",  # Linux/most systems
                "LiberationMono-Regular.ttf"  # Linux
            ]
            for font_name in font_candidates:
                try:
                    font = ImageFont.truetype(font_name, size=width // 14)
                    break
                except Exception:
                    continue
            if font is None:
                font = ImageFont.load_default()

            text = restaurant_name
            text_bbox = draw.textbbox((0, 0), text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            padding = max(12, width // 40)
            # Create a new image with extra space at the bottom for the text and margin
            bottom_margin = padding * 2
            new_height = height + text_height + padding + bottom_margin
            new_img = img.copy()
            new_img = new_img.crop((0, 0, width, new_height))
            # Fill the new area with black
            draw_new = ImageDraw.Draw(new_img)
            draw_new.rectangle([0, height, width, new_height], fill="black")
            # Draw the text centered in the new area, in white, with extra margin at the bottom
            text_x = (width - text_width) // 2
            text_y = height + padding // 2  # closer to the QR, more space below
            draw_new.text((text_x, text_y), text, fill="white", font=font)
            img = new_img

        buf = BytesIO()
        img = img.convert('RGB')
        img.save(buf, "PNG")
        buf.seek(0)
        return buf
