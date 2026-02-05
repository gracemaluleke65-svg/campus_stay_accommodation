import os
import stripe
import json
import random
import traceback
import logging
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime

from config import Config
from models import db, User, Accommodation, Booking, Review, Favorite
from forms import RegistrationForm, LoginForm, AccommodationForm, BookingForm, ReviewForm, SearchForm

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

stripe.api_key = app.config['STRIPE_SECRET_KEY']

# Ensure upload directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join('static', 'images', 'team'), exist_ok=True)

# CRITICAL: Create database tables before first request
@app.before_request
def create_tables():
    # This runs before the first request
    if not hasattr(app, 'tables_created'):
        with app.app_context():
            try:
                logger.info("Creating database tables...")
                db.create_all()
                logger.info("Database tables created successfully!")
                seed_admin()
                logger.info("Admin seeding completed!")
                app.tables_created = True
            except Exception as e:
                logger.error(f"Error creating tables: {e}")
                logger.error(traceback.format_exc())

@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except Exception as e:
        logger.error(f"Error loading user {user_id}: {e}")
        return None

@app.template_filter('range_stars')
def range_stars(rating):
    return range(int(rating))

@app.template_filter('range_empty_stars')
def range_empty_stars(rating):
    return range(5 - int(rating))

def get_amenity_icon(amenity):
    icons = {
        'wifi': 'bi-wifi',
        'parking': 'bi-car-front',
        'laundry': 'bi-water',
        'gym': 'bi-bicycle',
        'furnished': 'bi-house-door',
        'security': 'bi-shield-check',
        'pool': 'bi-droplet',
        'study_area': 'bi-book'
    }
    return icons.get(amenity, 'bi-check')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

def seed_admin():
    """Seed admin user - safe to run multiple times"""
    try:
        admin = User.query.filter_by(email=app.config['ADMIN_EMAIL']).first()
        if not admin:
            admin = User(
                full_name='System Admin',
                email=app.config['ADMIN_EMAIL'],
                student_number='00000000',
                id_number='0000000000000',
                phone='0000000000',
                is_admin=True
            )
            admin.set_password(app.config['ADMIN_PASSWORD'])
            db.session.add(admin)
            db.session.commit()
            logger.info('Admin user created successfully')
        else:
            # Update admin password if changed in env vars
            if not admin.check_password(app.config['ADMIN_PASSWORD']):
                admin.set_password(app.config['ADMIN_PASSWORD'])
                db.session.commit()
                logger.info('Admin password updated')
    except Exception as e:
        logger.error(f"Error seeding admin: {e}")
        db.session.rollback()

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    logger.error(f"500 error: {error}")
    return render_template('500.html'), 500

@app.route('/')
def index():
    try:
        featured = Accommodation.query.filter_by(is_active=True).order_by(db.func.random()).limit(3).all()
        return render_template('index.html', featured=featured, get_amenity_icon=get_amenity_icon)
    except Exception as e:
        logger.error(f"Error in index: {e}")
        return render_template('index.html', featured=[], get_amenity_icon=get_amenity_icon)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            user = User(
                full_name=form.full_name.data,
                email=form.email.data,
                student_number=form.student_number.data,
                id_number=form.id_number.data,
                phone=form.phone.data
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash('Registration successful! Please login.', 'success')
            logger.info(f"New user registered: {user.email}")
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Registration error: {e}")
            flash('Registration failed. Please try again.', 'danger')
    
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        try:
            user = User.query.filter_by(email=form.email.data).first()
            if user and user.check_password(form.password.data):
                login_user(user)
                next_page = request.args.get('next')
                flash('Login successful!', 'success')
                logger.info(f"User logged in: {user.email}")
                return redirect(next_page) if next_page else redirect(url_for('index'))
            else:
                flash('Invalid email or password.', 'danger')
        except Exception as e:
            logger.error(f"Login error: {e}")
            flash('Login failed. Please try again.', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    try:
        logout_user()
        flash('You have been logged out.', 'info')
    except Exception as e:
        logger.error(f"Logout error: {e}")
    return redirect(url_for('index'))

@app.route('/accommodations', methods=['GET', 'POST'])
def accommodations():
    form = SearchForm()
    try:
        query = Accommodation.query.filter_by(is_active=True)
        
        if request.method == 'POST' and form.validate_on_submit():
            if form.location.data:
                query = query.filter(Accommodation.location.ilike(f'%{form.location.data}%'))
            if form.min_price.data:
                query = query.filter(Accommodation.price_per_month >= form.min_price.data)
            if form.max_price.data:
                query = query.filter(Accommodation.price_per_month <= form.max_price.data)
        
        accommodations = query.all()
        
        user_favorites = []
        if current_user.is_authenticated:
            user_favorites = [f.accommodation_id for f in current_user.favorites]
        
        return render_template('accommodations.html', accommodations=accommodations, form=form, 
                             get_amenity_icon=get_amenity_icon, user_favorites=user_favorites)
    except Exception as e:
        logger.error(f"Accommodations error: {e}")
        flash('Error loading accommodations.', 'danger')
        return render_template('accommodations.html', accommodations=[], form=form, 
                             get_amenity_icon=get_amenity_icon, user_favorites=[])

@app.route('/accommodation/<int:id>')
def accommodation_detail(id):
    try:
        acc = Accommodation.query.get_or_404(id)
        if not acc.is_active:
            flash('This accommodation is no longer available.', 'warning')
            return redirect(url_for('accommodations'))
        
        booking_form = BookingForm()
        review_form = ReviewForm()
        
        has_booked = False
        can_review = False
        existing_review = None
        is_favorite = False
        
        if current_user.is_authenticated:
            has_booked = Booking.query.filter_by(
                user_id=current_user.id, 
                accommodation_id=id, 
                status='paid'
            ).first() is not None
            
            existing_review = Review.query.filter_by(
                user_id=current_user.id,
                accommodation_id=id
            ).first()
            
            is_favorite = Favorite.query.filter_by(
                user_id=current_user.id,
                accommodation_id=id
            ).first() is not None
            
            can_review = has_booked and not existing_review
        
        return render_template('accommodation_detail.html', 
                             accommodation=acc, 
                             booking_form=booking_form,
                             review_form=review_form,
                             can_review=can_review,
                             existing_review=existing_review,
                             is_favorite=is_favorite,
                             get_amenity_icon=get_amenity_icon)
    except Exception as e:
        logger.error(f"Accommodation detail error: {e}")
        flash('Error loading accommodation details.', 'danger')
        return redirect(url_for('accommodations'))

@app.route('/favorite/toggle/<int:accommodation_id>', methods=['POST'])
@login_required
def toggle_favorite(accommodation_id):
    try:
        favorite = Favorite.query.filter_by(
            user_id=current_user.id,
            accommodation_id=accommodation_id
        ).first()
        
        if favorite:
            db.session.delete(favorite)
            db.session.commit()
            return jsonify({'status': 'removed'})
        else:
            favorite = Favorite(
                user_id=current_user.id,
                accommodation_id=accommodation_id
            )
            db.session.add(favorite)
            db.session.commit()
            return jsonify({'status': 'added'})
    except Exception as e:
        logger.error(f"Toggle favorite error: {e}")
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/favorites')
@login_required
def favorites():
    try:
        user_favorites = Favorite.query.filter_by(user_id=current_user.id).all()
        accommodation_ids = [f.accommodation_id for f in user_favorites]
        accommodations = Accommodation.query.filter(Accommodation.id.in_(accommodation_ids), Accommodation.is_active==True).all()
        
        fav_ids = [f.accommodation_id for f in current_user.favorites]
        
        return render_template('favorites.html', accommodations=accommodations, 
                             get_amenity_icon=get_amenity_icon, user_favorites=fav_ids)
    except Exception as e:
        logger.error(f"Favorites error: {e}")
        flash('Error loading favorites.', 'danger')
        return render_template('favorites.html', accommodations=[], 
                             get_amenity_icon=get_amenity_icon, user_favorites=[])

@app.route('/book/<int:accommodation_id>', methods=['POST'])
@login_required
def book(accommodation_id):
    try:
        accommodation = Accommodation.query.get_or_404(accommodation_id)
        
        if accommodation.is_full():
            flash('Sorry, this accommodation is fully booked.', 'danger')
            return redirect(url_for('accommodation_detail', id=accommodation_id))
        
        duration = request.form.get('duration')
        if duration == 'annual':
            months = 10
        else:
            months = 5
        
        total_price = accommodation.price_per_month * months
        
        if total_price < 0.5:
            flash('Total price must be at least R 0.50', 'danger')
            return redirect(url_for('accommodation_detail', id=accommodation_id))
        
        booking = Booking(
            user_id=current_user.id,
            accommodation_id=accommodation_id,
            duration=duration,
            months=months,
            total_price=total_price,
            status='approved'
        )
        db.session.add(booking)
        db.session.commit()
        
        try:
            logger.info(f"Creating Stripe checkout session for booking {booking.id}")
            
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'zar',
                        'unit_amount': int(total_price * 100),
                        'product_data': {
                            'name': f'{accommodation.title}',
                            'description': f'{duration.capitalize()} booking ({months} months) - {accommodation.room_type} room',
                        },
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=url_for('payment_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=url_for('payment_cancel', booking_id=booking.id, _external=True),
            )
            
            booking.stripe_session_id = checkout_session.id
            db.session.commit()
            
            logger.info(f"Stripe session created: {checkout_session.id}")
            return redirect(checkout_session.url)
        
        except Exception as e:
            logger.error(f"Stripe Error: {str(e)}")
            db.session.delete(booking)
            db.session.commit()
            flash('Payment setup failed. Please try again.', 'danger')
            return redirect(url_for('accommodation_detail', id=accommodation_id))
            
    except Exception as e:
        logger.error(f"Booking error: {e}")
        db.session.rollback()
        flash('Booking failed. Please try again.', 'danger')
        return redirect(url_for('accommodation_detail', id=accommodation_id))

@app.route('/payment/success')
def payment_success():
    session_id = request.args.get('session_id')
    if not session_id:
        flash('Invalid payment session.', 'danger')
        return redirect(url_for('index'))
    
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status == 'paid':
            booking = Booking.query.filter_by(stripe_session_id=session_id).first()
            if booking:
                booking.status = 'paid'
                
                accommodation = Accommodation.query.get(booking.accommodation_id)
                accommodation.current_occupancy += 1
                if accommodation.current_occupancy >= accommodation.capacity:
                    accommodation.is_active = False
                
                db.session.commit()
                logger.info(f"Payment successful for booking {booking.id}")
                
                flash('Payment successful! Please leave a review.', 'success')
                return render_template('payment_success.html', accommodation_id=booking.accommodation_id)
    except Exception as e:
        logger.error(f"Payment verification error: {str(e)}")
        flash('Payment verification failed.', 'danger')
    
    return redirect(url_for('index'))

@app.route('/payment/cancel/<int:booking_id>')
def payment_cancel(booking_id):
    try:
        booking = Booking.query.get_or_404(booking_id)
        if booking.status == 'approved':
            booking.status = 'cancelled'
            db.session.commit()
        flash('Payment cancelled.', 'info')
        return render_template('payment_cancel.html')
    except Exception as e:
        logger.error(f"Payment cancel error: {e}")
        flash('Error processing cancellation.', 'danger')
        return redirect(url_for('index'))

@app.route('/review/<int:accommodation_id>', methods=['POST'])
@login_required
def submit_review(accommodation_id):
    try:
        booking = Booking.query.filter_by(
            user_id=current_user.id,
            accommodation_id=accommodation_id,
            status='paid'
        ).first()
        
        if not booking:
            flash('You can only review accommodations you have booked and paid for.', 'danger')
            return redirect(url_for('accommodation_detail', id=accommodation_id))
        
        existing = Review.query.filter_by(
            user_id=current_user.id,
            accommodation_id=accommodation_id
        ).first()
        
        if existing:
            flash('You have already reviewed this accommodation.', 'warning')
            return redirect(url_for('accommodation_detail', id=accommodation_id))
        
        form = ReviewForm()
        if form.validate_on_submit():
            review = Review(
                user_id=current_user.id,
                accommodation_id=accommodation_id,
                rating=int(form.rating.data),
                comment=form.comment.data
            )
            db.session.add(review)
            db.session.commit()
            logger.info(f"Review submitted by user {current_user.id} for accommodation {accommodation_id}")
            flash('Review submitted successfully!', 'success')
        
        return redirect(url_for('accommodation_detail', id=accommodation_id))
    except Exception as e:
        logger.error(f"Review error: {e}")
        db.session.rollback()
        flash('Failed to submit review.', 'danger')
        return redirect(url_for('accommodation_detail', id=accommodation_id))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    
    try:
        stats = {
            'total_users': User.query.count(),
            'total_accommodations': Accommodation.query.count(),
            'active_accommodations': Accommodation.query.filter_by(is_active=True).count(),
            'total_bookings': Booking.query.count(),
            'paid_bookings': Booking.query.filter_by(status='paid').count(),
            'total_revenue': db.session.query(db.func.sum(Booking.total_price)).filter_by(status='paid').scalar() or 0
        }
        
        return render_template('admin/dashboard.html', stats=stats)
    except Exception as e:
        logger.error(f"Admin dashboard error: {e}")
        flash('Error loading dashboard.', 'danger')
        return redirect(url_for('index'))

@app.route('/admin/accommodation/new', methods=['GET', 'POST'])
@login_required
def admin_new_accommodation():
    if not current_user.is_admin:
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    
    form = AccommodationForm()
    if form.validate_on_submit():
        try:
            acc = Accommodation(
                title=form.title.data,
                description=form.description.data,
                location=form.location.data,
                room_type=form.room_type.data,
                price_per_month=form.price_per_month.data,
                capacity=form.capacity.data,
                current_occupancy=form.current_occupancy.data,
                admin_id=current_user.id
            )
            
            amenities = []
            if form.wifi.data == '1': amenities.append('wifi')
            if form.parking.data == '1': amenities.append('parking')
            if form.laundry.data == '1': amenities.append('laundry')
            if form.gym.data == '1': amenities.append('gym')
            if form.furnished.data == '1': amenities.append('furnished')
            if form.security.data == '1': amenities.append('security')
            if form.pool.data == '1': amenities.append('pool')
            if form.study_area.data == '1': amenities.append('study_area')
            acc.set_amenities_list(amenities)
            
            if form.image.data:
                filename = secure_filename(form.image.data.filename)
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                filename = f"{timestamp}_{filename}"
                form.image.data.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                acc.image_filename = filename
            
            db.session.add(acc)
            db.session.commit()
            logger.info(f"New accommodation created: {acc.title}")
            flash('Accommodation added successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        except Exception as e:
            logger.error(f"Error creating accommodation: {e}")
            db.session.rollback()
            flash('Failed to add accommodation.', 'danger')
    
    return render_template('admin/accommodation_form.html', form=form, title='New Accommodation')

@app.route('/admin/accommodation/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_accommodation(id):
    if not current_user.is_admin:
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    
    try:
        acc = Accommodation.query.get_or_404(id)
        form = AccommodationForm(obj=acc)
        
        if form.validate_on_submit():
            acc.title = form.title.data
            acc.description = form.description.data
            acc.location = form.location.data
            acc.room_type = form.room_type.data
            acc.price_per_month = form.price_per_month.data
            acc.capacity = form.capacity.data
            acc.current_occupancy = form.current_occupancy.data
            
            amenities = []
            if form.wifi.data == '1': amenities.append('wifi')
            if form.parking.data == '1': amenities.append('parking')
            if form.laundry.data == '1': amenities.append('laundry')
            if form.gym.data == '1': amenities.append('gym')
            if form.furnished.data == '1': amenities.append('furnished')
            if form.security.data == '1': amenities.append('security')
            if form.pool.data == '1': amenities.append('pool')
            if form.study_area.data == '1': amenities.append('study_area')
            acc.set_amenities_list(amenities)
            
            if form.image.data:
                if acc.image_filename:
                    old_path = os.path.join(app.config['UPLOAD_FOLDER'], acc.image_filename)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                
                filename = secure_filename(form.image.data.filename)
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                filename = f"{timestamp}_{filename}"
                form.image.data.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                acc.image_filename = filename
            
            db.session.commit()
            logger.info(f"Accommodation updated: {acc.title}")
            flash('Accommodation updated successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        
        current_amenities = acc.get_amenities_list()
        form.wifi.data = '1' if 'wifi' in current_amenities else '0'
        form.parking.data = '1' if 'parking' in current_amenities else '0'
        form.laundry.data = '1' if 'laundry' in current_amenities else '0'
        form.gym.data = '1' if 'gym' in current_amenities else '0'
        form.furnished.data = '1' if 'furnished' in current_amenities else '0'
        form.security.data = '1' if 'security' in current_amenities else '0'
        form.pool.data = '1' if 'pool' in current_amenities else '0'
        form.study_area.data = '1' if 'study_area' in current_amenities else '0'
        
        return render_template('admin/accommodation_form.html', form=form, title='Edit Accommodation')
    except Exception as e:
        logger.error(f"Edit accommodation error: {e}")
        db.session.rollback()
        flash('Error updating accommodation.', 'danger')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/accommodation/<int:id>/delete', methods=['POST'])
@login_required
def admin_delete_accommodation(id):
    if not current_user.is_admin:
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    
    try:
        acc = Accommodation.query.get_or_404(id)
        
        if acc.image_filename:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], acc.image_filename)
            if os.path.exists(image_path):
                os.remove(image_path)
        
        db.session.delete(acc)
        db.session.commit()
        logger.info(f"Accommodation deleted: {id}")
        flash('Accommodation deleted successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    except Exception as e:
        logger.error(f"Delete accommodation error: {e}")
        db.session.rollback()
        flash('Error deleting accommodation.', 'danger')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/users')
@login_required
def admin_users():
    if not current_user.is_admin:
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    
    try:
        users = User.query.all()
        return render_template('admin/users.html', users=users)
    except Exception as e:
        logger.error(f"Admin users error: {e}")
        flash('Error loading users.', 'danger')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/user/<int:id>/promote', methods=['POST'])
@login_required
def admin_promote_user(id):
    if not current_user.is_admin:
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    
    try:
        user = User.query.get_or_404(id)
        if user.id == current_user.id:
            flash('You cannot modify your own admin status.', 'warning')
            return redirect(url_for('admin_users'))
        
        user.is_admin = True
        db.session.commit()
        logger.info(f"User promoted to admin: {user.email}")
        flash(f'{user.full_name} is now an admin.', 'success')
        return redirect(url_for('admin_users'))
    except Exception as e:
        logger.error(f"Promote user error: {e}")
        db.session.rollback()
        flash('Error promoting user.', 'danger')
        return redirect(url_for('admin_users'))

@app.route('/admin/user/<int:id>/demote', methods=['POST'])
@login_required
def admin_demote_user(id):
    if not current_user.is_admin:
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    
    try:
        user = User.query.get_or_404(id)  # FIXED: removed double .query
        if user.id == current_user.id:
            flash('You cannot modify your own admin status.', 'warning')
            return redirect(url_for('admin_users'))
        
        user.is_admin = False
        db.session.commit()
        logger.info(f"User demoted from admin: {user.email}")
        flash(f'{user.full_name} is no longer an admin.', 'success')
        return redirect(url_for('admin_users'))
    except Exception as e:
        logger.error(f"Demote user error: {e}")
        db.session.rollback()
        flash('Error demoting user.', 'danger')
        return redirect(url_for('admin_users'))

@app.route('/admin/bookings')
@login_required
def admin_bookings():
    if not current_user.is_admin:
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    
    try:
        bookings = Booking.query.order_by(Booking.created_at.desc()).all()
        return render_template('admin/bookings.html', bookings=bookings)
    except Exception as e:
        logger.error(f"Admin bookings error: {e}")
        flash('Error loading bookings.', 'danger')
        return redirect(url_for('admin_dashboard'))

@app.route('/team')
def team_page():
    return render_template('team.html')

@app.route('/my-bookings')
@login_required
def my_bookings():
    try:
        bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.created_at.desc()).all()
        return render_template('my_bookings.html', bookings=bookings)
    except Exception as e:
        logger.error(f"My bookings error: {e}")
        flash('Error loading your bookings.', 'danger')
        return render_template('my_bookings.html', bookings=[])

# Production entry point
def create_app():
    """Application factory for production"""
    return app

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)