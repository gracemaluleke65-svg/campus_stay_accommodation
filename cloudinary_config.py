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
    """Upload image to Cloudinary using unsigned preset"""
    try:
        result = cloudinary.uploader.upload(
            file,
            resource_type="auto",
            upload_preset="campus_stay_unsigned",  # Your unsigned preset
            folder=folder  # This will be combined with your preset settings
        )
        return result['secure_url']
    except Exception as e:
        print(f"Cloudinary upload error: {e}")
        return None

def delete_image(image_url):
    """Delete image from Cloudinary"""
    try:
        if image_url and 'cloudinary' in image_url:
            parts = image_url.split('/')
            upload_index = parts.index('upload') if 'upload' in parts else -1
            if upload_index != -1 and len(parts) > upload_index + 2:
                public_id = '/'.join(parts[upload_index + 2:]).split('.')[0]
                cloudinary.uploader.destroy(public_id)
                return True
    except Exception as e:
        print(f"Cloudinary delete error: {e}")
    return False