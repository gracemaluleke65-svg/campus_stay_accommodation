import cloudinary
import cloudinary.uploader
import cloudinary.api
from flask import current_app

def init_cloudinary(app):
    """Initialize Cloudinary configuration"""
    cloudinary.config(
        cloud_name=app.config['CLOUDINARY_CLOUD_NAME'],
        api_key=app.config['CLOUDINARY_API_KEY'],
        api_secret=app.config['CLOUDINARY_API_SECRET'],
        secure=True
    )

def upload_image(file, folder="campus_stay"):
    """Upload image to Cloudinary and return the URL"""
    try:
        # file can be FileStorage (from Flask form) or a file path
        result = cloudinary.uploader.upload(
            file,
            folder=folder,
            resource_type="auto"
        )
        return result['secure_url']
    except Exception as e:
        print(f"Cloudinary upload error: {e}")
        return None

def delete_image(image_url):
    """Delete image from Cloudinary"""
    try:
        if image_url and 'cloudinary' in image_url:
            # Extract public_id from URL
            # URL format: https://res.cloudinary.com/cloud_name/image/upload/v1234567890/folder/filename.jpg
            parts = image_url.split('/')
            # Find the part after 'upload' which contains version and public_id
            upload_index = parts.index('upload') if 'upload' in parts else -1
            if upload_index != -1 and len(parts) > upload_index + 2:
                # Skip version number (v1234567890) and join the rest
                public_id = '/'.join(parts[upload_index + 2:]).split('.')[0]  # Remove file extension
                cloudinary.uploader.destroy(public_id)
                return True
    except Exception as e:
        print(f"Cloudinary delete error: {e}")
    return False