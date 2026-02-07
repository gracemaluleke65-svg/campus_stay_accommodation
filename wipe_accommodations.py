from app import create_app, db
from models import Accommodation, Booking, Review, Favorite

app = create_app()

with app.app_context():
    print("⚠️  WARNING: This will delete ALL Campus Stay data!")
    print(f"Found {Accommodation.query.count()} accommodations")
    print(f"Found {Booking.query.count()} bookings")
    print(f"Found {Review.query.count()} reviews")
    print(f"Found {Favorite.query.count()} favorites")
    
    confirm = input("\nType 'DELETE' to confirm: ")
    
    if confirm == "DELETE":
        try:
            # Delete in correct order to avoid foreign key constraints
            print("\nDeleting favorites...")
            Favorite.query.delete()
            
            print("Deleting reviews...")
            Review.query.delete()
            
            print("Deleting bookings...")
            Booking.query.delete()
            
            print("Deleting accommodations...")
            Accommodation.query.delete()
            
            db.session.commit()
            print("\n✅ All Campus Stay data wiped successfully!")
            print("Database is now clean. You can add new accommodations with Cloudinary images.")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error: {e}")
    else:
        print("\n❌ Cancelled. No changes made.")