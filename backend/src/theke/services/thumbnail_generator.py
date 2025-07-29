import os
import io
from pathlib import Path
from typing import Optional
from PIL import Image
import fitz  # PyMuPDF


class ThumbnailGenerator:
    """Service for generating PDF thumbnails"""
    
    def __init__(self, thumbnail_dir: str = "thumbnails"):
        self.thumbnail_dir = Path(thumbnail_dir)
        self.thumbnail_dir.mkdir(exist_ok=True)
    
    def generate_thumbnail(self, pdf_path: str, page_number: int = 0, size: tuple = (200, 280)) -> Optional[str]:
        """
        Generate a thumbnail from a PDF file
        
        Args:
            pdf_path: Path to the PDF file
            page_number: Page number to generate thumbnail from (0-indexed)
            size: Thumbnail size as (width, height)
            
        Returns:
            Path to the generated thumbnail image, or None if failed
        """
        try:
            # Check if PDF file exists
            if not os.path.exists(pdf_path):
                return None
            
            # Generate thumbnail filename
            pdf_filename = Path(pdf_path).stem
            thumbnail_filename = f"{pdf_filename}_thumb.png"
            thumbnail_path = self.thumbnail_dir / thumbnail_filename
            
            # Check if thumbnail already exists
            if thumbnail_path.exists():
                return str(thumbnail_path)
            
            # Open PDF and generate thumbnail
            pdf_document = fitz.open(pdf_path)
            
            # Check if page exists
            if page_number >= len(pdf_document):
                page_number = 0
            
            if len(pdf_document) == 0:
                pdf_document.close()
                return None
            
            # Get the page
            page = pdf_document.load_page(page_number)
            
            # Create a matrix for scaling
            # Calculate scale to maintain aspect ratio
            page_rect = page.rect
            scale_x = size[0] / page_rect.width
            scale_y = size[1] / page_rect.height
            scale = min(scale_x, scale_y)
            
            matrix = fitz.Matrix(scale, scale)
            
            # Render page to pixmap
            pix = page.get_pixmap(matrix=matrix)
            
            # Convert to PIL Image
            img_data = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_data))
            
            # Create a white background with the desired size
            background = Image.new('RGB', size, 'white')
            
            # Calculate position to center the image
            x = (size[0] - image.width) // 2
            y = (size[1] - image.height) // 2
            
            # Paste the image onto the background
            background.paste(image, (x, y))
            
            # Save thumbnail
            background.save(thumbnail_path, "PNG", quality=85, optimize=True)
            
            # Clean up
            pdf_document.close()
            pix = None
            
            return str(thumbnail_path)
            
        except Exception as e:
            print(f"Error generating thumbnail for {pdf_path}: {e}")
            return None
    
    def get_thumbnail_path(self, pdf_path: str) -> Optional[str]:
        """
        Get the thumbnail path for a PDF without generating it
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Path to the thumbnail if it exists, None otherwise
        """
        try:
            pdf_filename = Path(pdf_path).stem
            thumbnail_filename = f"{pdf_filename}_thumb.png"
            thumbnail_path = self.thumbnail_dir / thumbnail_filename
            
            if thumbnail_path.exists():
                return str(thumbnail_path)
            
            return None
            
        except Exception:
            return None
    
    def delete_thumbnail(self, pdf_path: str) -> bool:
        """
        Delete thumbnail for a PDF file
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            thumbnail_path = self.get_thumbnail_path(pdf_path)
            if thumbnail_path and os.path.exists(thumbnail_path):
                os.remove(thumbnail_path)
                return True
            return False
            
        except Exception:
            return False


# Global instance
thumbnail_generator = ThumbnailGenerator()