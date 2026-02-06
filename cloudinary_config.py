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
        # For unsigned uploads, we need to override the config temporarily
        # Unsigned uploads don't use API key/secret, only cloud_name and preset
        result = cloudinary.uploader.upload(
            file,
            resource_type="auto",
            upload_preset="campus_stay_unsigned",
            folder=folder,
            use_filename=True,
            unique_filename=True,
            overwrite=False
        )
        return result['secure_url']
    except Exception as e:
        print(f"Cloudinary unsigned upload error: {e}")
        
        # Fallback to signed upload if unsigned fails
        try:
            print("Trying signed upload fallback...")
            result = cloudinary.uploader.upload(
                file,
                resource_type="auto",
                folder=folder,
                use_filename=True,
                unique_filename=True
            )
            return result['secure_url']
        except Exception as e2:
            print(f"Signed upload also failed: {e2}")
            return None

def delete_image(image_url):
    """Delete image from Cloudinary"""
    try:
        if image_url and 'cloudinary' in image_url:
            parts = image_url.split('/')
            upload_index = parts.index('upload') if 'upload' in parts else -1
            if upload_index != -1 and len(parts) > upload_index + 2:
                # Handle both versioned and non-versioned URLs
                public_id_parts = parts[upload_index + 1:]  # Skip 'upload'
                # Remove version number if present (starts with 'v')
                if public_id_parts[0].startswith('v'):
                    public_id_parts = public_id_parts[1:]
                public_id = '/'.join(public_id_parts).split('.')[0]
                print(f"Deleting image with public_id: {public_id}")
                cloudinary.uploader.destroy(public_id)
                return True
    except Exception as e:
        print(f"Cloudinary delete error: {e}")
    return False