"""
File Upload Service

Service for handling file uploads including avatar images with validation,
secure storage, and file management for the Duolingo clone backend.
"""

import logging
import os
import uuid
from pathlib import Path
from typing import List, Optional
import imghdr
import hashlib

from fastapi import UploadFile
from PIL import Image
import aiofiles

# Configure logging
logger = logging.getLogger(__name__)


class FileUploadService:
    """Service for handling file uploads with validation and secure storage."""
    
    # Configuration constants
    MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5MB in bytes
    ALLOWED_IMAGE_TYPES = {'png', 'jpeg', 'jpg', 'webp'}
    AVATAR_UPLOAD_DIR = "uploads/avatars"
    AVATAR_MAX_DIMENSIONS = (800, 800)  # Max width, height in pixels
    
    def __init__(self):
        """Initialize the file upload service."""
        self._ensure_upload_directories()
    
    def _ensure_upload_directories(self):
        """Ensure upload directories exist."""
        try:
            avatar_dir = Path(self.AVATAR_UPLOAD_DIR)
            avatar_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Upload directory ensured: {avatar_dir}")
        except Exception as e:
            logger.error(f"Failed to create upload directories: {e}")
            raise
    
    async def upload_avatar(self, file: UploadFile, user_id: str) -> str:
        """
        Upload and process user avatar image.
        
        Args:
            file: Uploaded file object
            user_id: ID of the user uploading the avatar
            
        Returns:
            URL path to the uploaded avatar
            
        Raises:
            ValueError: If file validation fails
            Exception: If upload processing fails
        """
        try:
            # Validate file
            await self._validate_avatar_file(file)
            
            # Generate unique filename
            file_extension = self._get_file_extension(file.filename or "avatar.png")
            unique_filename = f"{user_id}_{uuid.uuid4().hex[:8]}.{file_extension}"
            file_path = Path(self.AVATAR_UPLOAD_DIR) / unique_filename
            
            # Read and validate file content
            content = await file.read()
            await file.seek(0)  # Reset file pointer
            
            # Validate image content and format
            self._validate_image_content(content, file_extension)
            
            # Process and resize image if needed
            processed_content = await self._process_avatar_image(content)
            
            # Save file securely
            await self._save_file_secure(file_path, processed_content)
            
            # Generate public URL (in production this would be a CDN URL)
            avatar_url = f"/{self.AVATAR_UPLOAD_DIR}/{unique_filename}"
            
            logger.info(f"Avatar uploaded successfully for user {user_id}: {avatar_url}")
            return avatar_url
            
        except ValueError:
            # Re-raise validation errors
            raise
        except Exception as e:
            logger.error(f"Avatar upload failed for user {user_id}: {e}")
            raise Exception("Failed to upload avatar. Please try again.")
    
    async def _validate_avatar_file(self, file: UploadFile):
        """
        Validate uploaded avatar file.
        
        Args:
            file: Uploaded file object
            
        Raises:
            ValueError: If validation fails
        """
        # Check if file is provided
        if not file or not file.filename:
            raise ValueError("No file provided")
        
        # Check file size
        file_size = 0
        content = await file.read()
        file_size = len(content)
        await file.seek(0)  # Reset file pointer
        
        if file_size == 0:
            raise ValueError("File is empty")
        
        if file_size > self.MAX_AVATAR_SIZE:
            size_mb = self.MAX_AVATAR_SIZE / (1024 * 1024)
            raise ValueError(f"File size exceeds maximum allowed size of {size_mb}MB")
        
        # Check file extension
        file_extension = self._get_file_extension(file.filename)
        if file_extension.lower() not in self.ALLOWED_IMAGE_TYPES:
            allowed_types = ", ".join(self.ALLOWED_IMAGE_TYPES)
            raise ValueError(f"Invalid file type. Allowed types: {allowed_types}")
        
        # Validate MIME type
        if file.content_type and not file.content_type.startswith('image/'):
            raise ValueError("File must be an image")
    
    def _get_file_extension(self, filename: str) -> str:
        """
        Extract file extension from filename.
        
        Args:
            filename: Name of the file
            
        Returns:
            File extension without dot
        """
        if not filename:
            return "png"
        
        extension = Path(filename).suffix.lstrip('.').lower()
        return extension if extension else "png"
    
    def _validate_image_content(self, content: bytes, expected_extension: str):
        """
        Validate image content and format.
        
        Args:
            content: File content bytes
            expected_extension: Expected file extension
            
        Raises:
            ValueError: If image validation fails
        """
        try:
            # Use imghdr to detect actual image type
            detected_type = imghdr.what(None, h=content)
            
            if not detected_type:
                raise ValueError("File is not a valid image")
            
            # Map detected types to our allowed types
            type_mapping = {
                'png': 'png',
                'jpeg': 'jpeg',
                'jpg': 'jpeg',
                'webp': 'webp'
            }
            
            if detected_type not in type_mapping:
                raise ValueError(f"Unsupported image format: {detected_type}")
            
            # Check if detected type matches expected extension
            expected_mapped = type_mapping.get(expected_extension, expected_extension)
            detected_mapped = type_mapping.get(detected_type, detected_type)
            
            if expected_mapped not in ['jpeg', 'jpg'] and detected_mapped not in ['jpeg', 'jpg']:
                if expected_mapped != detected_mapped:
                    logger.warning(f"Extension mismatch: expected {expected_extension}, detected {detected_type}")
            
        except Exception as e:
            logger.error(f"Image content validation failed: {e}")
            raise ValueError("Invalid image file")
    
    async def _process_avatar_image(self, content: bytes) -> bytes:
        """
        Process avatar image (resize, optimize).
        
        Args:
            content: Original image content
            
        Returns:
            Processed image content
        """
        try:
            # Open image with PIL
            from io import BytesIO
            image = Image.open(BytesIO(content))
            
            # Convert to RGB if necessary (for JPEG compatibility)
            if image.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
            
            # Resize if needed
            if image.size[0] > self.AVATAR_MAX_DIMENSIONS[0] or image.size[1] > self.AVATAR_MAX_DIMENSIONS[1]:
                image.thumbnail(self.AVATAR_MAX_DIMENSIONS, Image.Resampling.LANCZOS)
            
            # Save processed image
            output = BytesIO()
            image.save(output, format='JPEG', quality=85, optimize=True)
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Image processing failed: {e}")
            # Return original content if processing fails
            return content
    
    async def _save_file_secure(self, file_path: Path, content: bytes):
        """
        Save file securely with proper permissions.
        
        Args:
            file_path: Path where to save the file
            content: File content to save
            
        Raises:
            Exception: If file saving fails
        """
        try:
            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save file asynchronously
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(content)
            
            # Set secure file permissions (readable by owner and group only)
            os.chmod(file_path, 0o644)
            
            logger.info(f"File saved securely: {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to save file {file_path}: {e}")
            # Clean up partial file if it exists
            if file_path.exists():
                try:
                    file_path.unlink()
                except:
                    pass
            raise
    
    def delete_avatar(self, avatar_url: str) -> bool:
        """
        Delete avatar file from storage.
        
        Args:
            avatar_url: URL/path of the avatar to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            # Extract filename from URL
            if avatar_url.startswith('/'):
                file_path = Path(avatar_url[1:])  # Remove leading slash
            else:
                file_path = Path(avatar_url)
            
            # Ensure the file is in the expected directory for security
            if not str(file_path).startswith(self.AVATAR_UPLOAD_DIR):
                logger.warning(f"Attempted to delete file outside avatar directory: {file_path}")
                return False
            
            # Delete file if it exists
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Avatar deleted: {file_path}")
                return True
            else:
                logger.warning(f"Avatar file not found: {file_path}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete avatar {avatar_url}: {e}")
            return False
    
    def get_file_info(self, file_path: str) -> Optional[dict]:
        """
        Get information about an uploaded file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with file information or None if file doesn't exist
        """
        try:
            path = Path(file_path)
            if not path.exists():
                return None
            
            stat = path.stat()
            return {
                'size': stat.st_size,
                'created': stat.st_ctime,
                'modified': stat.st_mtime,
                'extension': path.suffix.lstrip('.').lower()
            }
            
        except Exception as e:
            logger.error(f"Failed to get file info for {file_path}: {e}")
            return None