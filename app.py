import os
import glob
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify

import firebase_admin
from firebase_admin import credentials, firestore

app = Flask(__name__)
app.secret_key = 'brettenwood-secret-key-2024'

# ---------------------------------------------------------------------------
# Firebase / Firestore initialisation
# ---------------------------------------------------------------------------
_SERVICE_ACCOUNT_KEY = (
    os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    or r'C:\Users\Kaylin_r7\Downloads\bretten-wood-firebase-adminsdk-fbsvc-7f400e45c0.json'
)

cred = credentials.Certificate(_SERVICE_ACCOUNT_KEY)
firebase_admin.initialize_app(cred)
db = firestore.client()

REVIEWS_COLLECTION = 'reviews'
PORTFOLIO_COLLECTION = 'portfolio_descriptions'

PORTFOLIO_IMG_DIR = os.path.join(os.path.dirname(__file__), 'static', 'images', 'portfolio')


# ---------------------------------------------------------------------------
# Firestore helpers — Reviews
# ---------------------------------------------------------------------------

def load_reviews():
    """Fetch all reviews from Firestore, ordered newest first."""
    try:
        docs = db.collection(REVIEWS_COLLECTION).order_by(
            'timestamp', direction=firestore.Query.DESCENDING
        ).stream()
        return [doc.to_dict() | {'id': doc.id} for doc in docs]
    except Exception as e:
        app.logger.error(f'Firestore load_reviews error: {e}')
        return []


def save_review(review: dict):
    """Persist a single review document to Firestore."""
    db.collection(REVIEWS_COLLECTION).add(review)


# ---------------------------------------------------------------------------
# Firestore helpers — Portfolio descriptions
# ---------------------------------------------------------------------------

def load_portfolio_descriptions():
    """
    Returns a dict keyed by filename, e.g.:
      { 'sample_installation.jpg': { title, description, category } }
    """
    try:
        docs = db.collection(PORTFOLIO_COLLECTION).stream()
        return {doc.id: doc.to_dict() for doc in docs}
    except Exception as e:
        app.logger.error(f'Firestore load_portfolio_descriptions error: {e}')
        return {}


# ---------------------------------------------------------------------------
# Portfolio image scanner
# ---------------------------------------------------------------------------

def scan_portfolio_images():
    """Scan portfolio directory for images and return structured data."""
    descriptions = load_portfolio_descriptions()
    images = []
    if not os.path.exists(PORTFOLIO_IMG_DIR):
        os.makedirs(PORTFOLIO_IMG_DIR, exist_ok=True)
        return images

    extensions = ['*.jpg', '*.jpeg', '*.png', '*.webp', '*.gif']
    found_files = []
    for ext in extensions:
        found_files.extend(glob.glob(os.path.join(PORTFOLIO_IMG_DIR, ext)))
        found_files.extend(glob.glob(os.path.join(PORTFOLIO_IMG_DIR, ext.upper())))

    seen = set()
    for filepath in found_files:
        filename = os.path.basename(filepath)
        if filename in seen:
            continue
        seen.add(filename)

        stem = os.path.splitext(filename)[0]
        title = stem.replace('_', ' ').replace('-', ' ').title()

        desc_data = descriptions.get(filename, {})
        images.append({
            'filename': filename,
            'url': f'images/portfolio/{filename}',
            'title': desc_data.get('title', title),
            'description': desc_data.get('description', ''),
            'category': desc_data.get('category', 'residential'),
        })

    return images


# ---------------------------------------------------------------------------
# Tank Systems Data (static — no DB needed)
# ---------------------------------------------------------------------------
TANK_SYSTEMS = {
    'jojo_1000': {
        'id': 'jojo_1000',
        'brand': 'JoJo',
        'capacity': '1000L',
        'image': 'images/tanks/jojo_1000.jpg',
        'pump': 'Grundfos CM3-5 Pressure Pump',
        'pump_specs': '0.55 kW | 45 L/min | Max 5 bar',
        'components': [
            '1000L JoJo Slimline Vertical Tank',
            'Grundfos CM3-5 Pressure Pump',
            'Pressure Switch (adjustable cut-in/cut-out)',
            'Non-Return / Check Valve (32mm)',
            'Heavy-Duty Galvanised Steel Tank Stand',
            'Full Installation Kit (pipework, fittings, float valve)',
            '1-Year Labour Warranty',
        ],
        'ideal_for': 'Small households, apartments, townhouses',
        'color': '#f8f9fa',
    },
    'jojo_2500': {
        'id': 'jojo_2500',
        'brand': 'JoJo',
        'capacity': '2500L',
        'image': 'images/tanks/jojo_2500.jpg',
        'pump': 'Grundfos CM5-7 Pressure Pump',
        'pump_specs': '0.75 kW | 65 L/min | Max 7 bar',
        'components': [
            '2500L JoJo Vertical Storage Tank',
            'Grundfos CM5-7 Pressure Pump',
            'Pressure Switch (adjustable cut-in/cut-out)',
            'Non-Return / Check Valve (40mm)',
            'Heavy-Duty Galvanised Steel Tank Stand',
            'Full Installation Kit (pipework, fittings, float valve)',
            '1-Year Labour Warranty',
        ],
        'ideal_for': 'Medium-sized family homes',
        'color': '#f8f9fa',
    },
    'jojo_5000': {
        'id': 'jojo_5000',
        'brand': 'JoJo',
        'capacity': '5000L',
        'image': 'images/tanks/jojo_5000.jpg',
        'pump': 'Grundfos CM10-2 Pressure Pump',
        'pump_specs': '1.1 kW | 120 L/min | Max 8 bar',
        'components': [
            '5000L JoJo Vertical Storage Tank',
            'Grundfos CM10-2 Pressure Pump',
            'Pressure Switch (adjustable cut-in/cut-out)',
            'Non-Return / Check Valve (50mm)',
            'Heavy-Duty Galvanised Steel Tank Stand',
            'Full Installation Kit (pipework, fittings, float valve)',
            'Level Indicator / Gauge',
            '1-Year Labour Warranty',
        ],
        'ideal_for': 'Large family homes, small commercial',
        'color': '#f8f9fa',
    },
    'eco_1000': {
        'id': 'eco_1000',
        'brand': 'Eco',
        'capacity': '1000L',
        'image': 'images/tanks/eco_1000.jpg',
        'pump': 'Grundfos CM3-5 Pressure Pump',
        'pump_specs': '0.55 kW | 45 L/min | Max 5 bar',
        'components': [
            '1000L Eco Slim Vertical Tank (UV Stabilised)',
            'Grundfos CM3-5 Pressure Pump',
            'Pressure Switch (adjustable cut-in/cut-out)',
            'Non-Return / Check Valve (32mm)',
            'Powder-Coated Steel Tank Stand',
            'Full Installation Kit (pipework, fittings, float valve)',
            '1-Year Labour Warranty',
        ],
        'ideal_for': 'Compact spaces, smaller properties',
        'color': '#000000',
    },
    'eco_2500': {
        'id': 'eco_2500',
        'brand': 'Eco',
        'capacity': '2500L',
        'image': 'images/tanks/eco_2500.jpg',
        'pump': 'Grundfos CM5-7 Pressure Pump',
        'pump_specs': '0.75 kW | 65 L/min | Max 7 bar',
        'components': [
            '2500L Eco Vertical Storage Tank (UV Stabilised)',
            'Grundfos CM5-7 Pressure Pump',
            'Pressure Switch (adjustable cut-in/cut-out)',
            'Non-Return / Check Valve (40mm)',
            'Powder-Coated Steel Tank Stand',
            'Full Installation Kit (pipework, fittings, float valve)',
            '1-Year Labour Warranty',
        ],
        'ideal_for': 'Standard family homes',
        'color': '#000000',
    },
    'eco_5000': {
        'id': 'eco_5000',
        'brand': 'Eco',
        'capacity': '5000L',
        'image': 'images/tanks/eco_5000.jpg',
        'pump': 'Grundfos CM10-2 Pressure Pump',
        'pump_specs': '1.1 kW | 120 L/min | Max 8 bar',
        'components': [
            '5000L Eco Vertical Storage Tank (UV Stabilised)',
            'Grundfos CM10-2 Pressure Pump',
            'Pressure Switch (adjustable cut-in/cut-out)',
            'Non-Return / Check Valve (50mm)',
            'Powder-Coated Steel Tank Stand',
            'Full Installation Kit (pipework, fittings, float valve)',
            'Level Indicator / Gauge',
            '1-Year Labour Warranty',
        ],
        'ideal_for': 'Large homes, small commercial properties',
        'color': '#000000',
    },
}

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route('/')
def home():
    return render_template('home.html')


@app.route('/systems')
def systems():
    brand_filter = request.args.get('brand', 'all').lower()
    size_filter = request.args.get('size', 'all')

    filtered = list(TANK_SYSTEMS.values())
    if brand_filter != 'all':
        filtered = [s for s in filtered if s['brand'].lower() == brand_filter]
    if size_filter != 'all':
        filtered = [s for s in filtered if s['capacity'] == size_filter]

    return render_template('systems.html',
                           systems=filtered,
                           brand_filter=brand_filter,
                           size_filter=size_filter)


@app.route('/portfolio')
def portfolio():
    images = scan_portfolio_images()
    category_filter = request.args.get('category', 'all')
    return render_template('portfolio.html',
                           images=images,
                           category_filter=category_filter)


@app.route('/reviews')
def reviews():
    all_reviews = load_reviews()
    return render_template('reviews.html', reviews=all_reviews)


@app.route('/contact')
def contact():
    return render_template('contact.html')


@app.route('/submit_review', methods=['POST'])
def submit_review():
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    rating = request.form.get('rating', '').strip()
    title = request.form.get('title', '').strip()
    review_text = request.form.get('review', '').strip()

    errors = []
    if not name:
        errors.append('Name is required.')
    if not rating or rating not in ['1', '2', '3', '4', '5']:
        errors.append('A valid rating (1-5) is required.')
    if not review_text:
        errors.append('Review text is required.')

    if errors:
        for err in errors:
            flash(err, 'danger')
        return redirect(url_for('reviews'))

    review = {
        'name': name,
        'email': email,
        'rating': int(rating),
        'title': title,
        'review': review_text,
        'timestamp': datetime.now().isoformat(),
    }

    try:
        save_review(review)
        flash('Thank you for your review! It has been submitted successfully.', 'success')
    except Exception as e:
        app.logger.error(f'Failed to save review: {e}')
        flash('Sorry, there was a problem submitting your review. Please try again.', 'danger')

    return redirect(url_for('reviews'))


@app.route('/submit_contact', methods=['POST'])
def submit_contact():
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    phone = request.form.get('phone', '').strip()
    area = request.form.get('area', '').strip()
    urgency = request.form.get('urgency', '').strip()
    message = request.form.get('message', '').strip()

    errors = []
    if not name:
        errors.append('Name is required.')
    if not email:
        errors.append('Email is required.')
    if not message:
        errors.append('Message is required.')

    if errors:
        for err in errors:
            flash(err, 'danger')
        return redirect(url_for('contact'))

    enquiry = {
        'name': name,
        'email': email,
        'phone': phone,
        'area': area,
        'urgency': urgency,
        'message': message,
        'timestamp': datetime.now().isoformat(),
    }

    try:
        db.collection('contact_enquiries').add(enquiry)
    except Exception as e:
        app.logger.error(f'Failed to save contact enquiry: {e}')

    flash(f'Thank you {name}! We will be in touch shortly.', 'success')
    return redirect(url_for('contact'))


# ---------------------------------------------------------------------------
if __name__ == '__main__':
    os.makedirs(PORTFOLIO_IMG_DIR, exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(__file__), 'static', 'images', 'tanks'), exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=5000)
