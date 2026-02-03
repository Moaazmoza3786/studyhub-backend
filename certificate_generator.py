"""
Certificate Generator for Study Hub
Creates PDF certificates with QR codes for verification
"""

import os
from datetime import datetime
from io import BytesIO

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False
    print("Warning: Pillow not installed. Using basic certificate generation.")

try:
    import qrcode
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False
    print("Warning: qrcode not installed. Certificates will not have QR codes.")

try:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import inch
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False
    print("Warning: ReportLab not installed. Using image-based certificates only.")


class CertificateGenerator:
    """Generates professional PDF certificates with QR verification codes"""
    
    def __init__(self, output_dir: str):
        """
        Initialize the certificate generator
        
        Args:
            output_dir: Directory to save generated certificates
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Certificate template settings
        self.width = 1920
        self.height = 1080
        self.bg_color = (15, 23, 42)  # Dark blue
        self.accent_color = (102, 126, 234)  # Purple accent
        self.gold_color = (255, 215, 0)  # Gold
        self.text_color = (255, 255, 255)  # White
        
        # Load fonts (use default if not available)
        self.title_font_size = 72
        self.name_font_size = 56
        self.subtitle_font_size = 32
        self.small_font_size = 24
    
    def generate(self, student_name: str, course_name: str, course_name_ar: str = None,
                 date: str = None, certificate_code: str = None, score: float = None) -> str:
        """
        Generate a certificate PDF
        
        Args:
            student_name: Name of the student
            course_name: Course/path name in English
            course_name_ar: Course/path name in Arabic
            date: Issue date (defaults to today)
            certificate_code: Unique certificate code
            score: Final score percentage
            
        Returns:
            Path to generated PDF file
        """
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        if not certificate_code:
            certificate_code = f"SH-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Generate QR code for verification
        qr_image = self._generate_qr_code(certificate_code) if HAS_QRCODE else None
        
        # Create certificate image
        cert_image = self._create_certificate_image(
            student_name, course_name, course_name_ar, date, certificate_code, score, qr_image
        )
        
        # Save as PDF
        output_path = os.path.join(self.output_dir, f'certificate_{certificate_code}.pdf')
        
        if HAS_REPORTLAB:
            self._save_as_pdf(cert_image, output_path, student_name, course_name, date, certificate_code)
        else:
            # Fallback: save as PNG
            output_path = output_path.replace('.pdf', '.png')
            cert_image.save(output_path, 'PNG')
        
        return output_path
    
    def _generate_qr_code(self, certificate_code: str) -> Image.Image:
        """Generate QR code for certificate verification"""
        if not HAS_QRCODE:
            return None
        
        verification_url = f"https://studyhub.com/verify/{certificate_code}"
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=6,
            border=2
        )
        qr.add_data(verification_url)
        qr.make(fit=True)
        
        return qr.make_image(fill_color="white", back_color="transparent")
    
    def _create_certificate_image(self, student_name: str, course_name: str, 
                                   course_name_ar: str, date: str, certificate_code: str,
                                   score: float, qr_image: Image.Image) -> Image.Image:
        """Create the certificate as an image"""
        if not HAS_PILLOW:
            # Return a placeholder
            return None
        
        # Create base image
        img = Image.new('RGB', (self.width, self.height), self.bg_color)
        draw = ImageDraw.Draw(img)
        
        try:
            # Try to load a nice font, fallback to default
            title_font = ImageFont.truetype("arial.ttf", self.title_font_size)
            name_font = ImageFont.truetype("arialbd.ttf", self.name_font_size)
            subtitle_font = ImageFont.truetype("arial.ttf", self.subtitle_font_size)
            small_font = ImageFont.truetype("arial.ttf", self.small_font_size)
        except:
            # Use default font
            title_font = ImageFont.load_default()
            name_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        # Draw decorative border
        border_width = 8
        draw.rectangle(
            [(40, 40), (self.width - 40, self.height - 40)],
            outline=self.accent_color,
            width=border_width
        )
        
        # Draw inner gold border
        draw.rectangle(
            [(60, 60), (self.width - 60, self.height - 60)],
            outline=self.gold_color,
            width=2
        )
        
        # Draw decorative corner elements
        corner_size = 50
        for x, y in [(80, 80), (self.width - 80 - corner_size, 80), 
                     (80, self.height - 80 - corner_size), 
                     (self.width - 80 - corner_size, self.height - 80 - corner_size)]:
            draw.rectangle([(x, y), (x + corner_size, y + corner_size)], 
                          outline=self.gold_color, width=2)
        
        # Title
        title_text = "🏆 CERTIFICATE OF COMPLETION 🏆"
        self._draw_centered_text(draw, title_text, 150, title_font, self.gold_color)
        
        # Arabic subtitle
        if course_name_ar:
            self._draw_centered_text(draw, "شهادة إتمام", 220, subtitle_font, self.text_color)
        
        # This is to certify that
        self._draw_centered_text(draw, "This is to certify that", 300, subtitle_font, self.text_color)
        
        # Student name (highlighted)
        self._draw_centered_text(draw, student_name, 380, name_font, self.gold_color)
        
        # Has successfully completed
        self._draw_centered_text(draw, "has successfully completed the", 460, subtitle_font, self.text_color)
        
        # Course name
        self._draw_centered_text(draw, course_name, 530, name_font, self.accent_color)
        
        # Arabic course name
        if course_name_ar:
            self._draw_centered_text(draw, course_name_ar, 600, subtitle_font, self.text_color)
        
        # Score (if provided)
        if score:
            score_text = f"with a score of {score:.1f}%"
            self._draw_centered_text(draw, score_text, 670, subtitle_font, self.gold_color)
        
        # Date
        date_text = f"Issued on: {date}"
        self._draw_centered_text(draw, date_text, 750, small_font, self.text_color)
        
        # Certificate code
        code_text = f"Certificate ID: {certificate_code}"
        self._draw_centered_text(draw, code_text, 790, small_font, self.accent_color)
        
        # Add QR code if available
        if qr_image:
            qr_resized = qr_image.resize((120, 120))
            qr_position = (self.width - 180, self.height - 180)
            # Convert QR to RGB if needed
            if qr_resized.mode != 'RGB':
                qr_rgb = Image.new('RGB', qr_resized.size, self.bg_color)
                qr_rgb.paste(qr_resized, mask=qr_resized.split()[-1] if qr_resized.mode == 'RGBA' else None)
                qr_resized = qr_rgb
            img.paste(qr_resized, qr_position)
            
            # QR label
            draw.text((self.width - 180, self.height - 50), "Scan to verify", 
                     font=small_font, fill=self.text_color)
        
        # Study Hub logo/branding
        branding = "STUDY HUB"
        draw.text((100, self.height - 100), branding, font=name_font, fill=self.accent_color)
        draw.text((100, self.height - 55), "Cybersecurity Learning Platform", 
                  font=small_font, fill=self.text_color)
        
        # Signature line
        sig_y = 850
        draw.line([(self.width//2 - 150, sig_y), (self.width//2 + 150, sig_y)], 
                  fill=self.text_color, width=2)
        self._draw_centered_text(draw, "Authorized Signature", sig_y + 20, small_font, self.text_color)
        
        return img
    
    def _draw_centered_text(self, draw: ImageDraw.Draw, text: str, y: int, 
                            font: ImageFont.FreeTypeFont, color: tuple):
        """Draw text centered horizontally"""
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
        except:
            text_width = len(text) * 20  # Rough estimate
        
        x = (self.width - text_width) // 2
        draw.text((x, y), text, font=font, fill=color)
    
    def _save_as_pdf(self, cert_image: Image.Image, output_path: str,
                     student_name: str, course_name: str, date: str, certificate_code: str):
        """Save certificate as PDF using ReportLab"""
        if not HAS_REPORTLAB or not cert_image:
            # Fallback to image save
            if cert_image:
                cert_image.save(output_path.replace('.pdf', '.png'), 'PNG')
            return
        
        # Create PDF
        c = canvas.Canvas(output_path, pagesize=landscape(A4))
        
        # Convert PIL image to bytes
        img_buffer = BytesIO()
        cert_image.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        # Draw image on PDF
        from reportlab.lib.utils import ImageReader
        img_reader = ImageReader(img_buffer)
        
        # Get A4 landscape dimensions
        page_width, page_height = landscape(A4)
        
        # Draw image to fill page
        c.drawImage(img_reader, 0, 0, width=page_width, height=page_height)
        
        # Add metadata
        c.setAuthor("Study Hub")
        c.setTitle(f"Certificate - {course_name}")
        c.setSubject(f"Certificate for {student_name}")
        c.setCreator("Study Hub Certificate Generator")
        c.setKeywords([certificate_code, student_name, course_name])
        
        c.save()


# Convenience function
def generate_certificate(student_name: str, course_name: str, output_dir: str = None,
                         **kwargs) -> str:
    """Quick function to generate a certificate"""
    if not output_dir:
        output_dir = os.path.join(os.path.dirname(__file__), 'certificates')
    
    generator = CertificateGenerator(output_dir)
    return generator.generate(student_name, course_name, **kwargs)


if __name__ == '__main__':
    # Test certificate generation
    generator = CertificateGenerator('test_certificates')
    path = generator.generate(
        student_name="أحمد محمد",
        course_name="Web Penetration Testing",
        course_name_ar="اختبار اختراق الويب",
        score=95.5
    )
    print(f"Certificate generated: {path}")
