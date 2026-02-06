"""
Database migration script to fix image_filename column length
Run this locally or include in deployment to update PostgreSQL schema
"""

import os
import sys
from flask import Flask
from sqlalchemy import text

# Add current directory to path to import app and models
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db

def fix_image_filename_column():
    """Alter image_filename column from VARCHAR(100) to VARCHAR(500)"""
    
    with app.app_context():
        try:
            print("=" * 60)
            print("Database Migration: Fix image_filename column length")
            print("=" * 60)
            
            # Check database connection
            print("\n1. Checking database connection...")
            result = db.session.execute(text("SELECT current_database(), version();"))
            db_info = result.fetchone()
            print(f"   Connected to: {db_info[0]}")
            print(f"   PostgreSQL version: {db_info[1].split()[0]}")
            
            # Check if accommodation table exists
            print("\n2. Checking if 'accommodation' table exists...")
            result = db.session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'accommodation'
                );
            """))
            table_exists = result.scalar()
            
            if not table_exists:
                print("   Table 'accommodation' does not exist yet. Skipping migration.")
                print("   (It will be created with correct column size on next app start)")
                return True
            
            print("   Table 'accommodation' found.")
            
            # Check current column definition
            print("\n3. Checking current 'image_filename' column definition...")
            result = db.session.execute(text("""
                SELECT column_name, data_type, character_maximum_length 
                FROM information_schema.columns 
                WHERE table_name = 'accommodation' 
                AND column_name = 'image_filename';
            """))
            column_info = result.fetchone()
            
            if not column_info:
                print("   Column 'image_filename' not found. Skipping migration.")
                return True
            
            current_length = column_info[2]
            print(f"   Current column: {column_info[0]}")
            print(f"   Data type: {column_info[1]}")
            print(f"   Current max length: {current_length}")
            
            # Alter column if needed
            if current_length and current_length < 500:
                print(f"\n4. Updating column length from {current_length} to 500...")
                db.session.execute(text("""
                    ALTER TABLE accommodation 
                    ALTER COLUMN image_filename TYPE VARCHAR(500);
                """))
                db.session.commit()
                print("   ✓ Column successfully updated to VARCHAR(500)")
            else:
                print(f"\n4. Column length is already sufficient ({current_length}). No changes needed.")
            
            # Verify the change
            print("\n5. Verifying changes...")
            result = db.session.execute(text("""
                SELECT character_maximum_length 
                FROM information_schema.columns 
                WHERE table_name = 'accommodation' 
                AND column_name = 'image_filename';
            """))
            new_length = result.scalar()
            print(f"   New max length: {new_length}")
            
            if new_length and new_length >= 500:
                print("\n" + "=" * 60)
                print("✓ Migration completed successfully!")
                print("=" * 60)
                return True
            else:
                print("\n" + "=" * 60)
                print("✗ Migration verification failed!")
                print("=" * 60)
                return False
                
        except Exception as e:
            db.session.rollback()
            print(f"\n✗ Error during migration: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = fix_image_filename_column()
    sys.exit(0 if success else 1)