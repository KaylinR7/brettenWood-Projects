import os
import json
import glob
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, g

app = Flask(__name__)
app.secret_key = 'brettenwood-secret-key-2024'

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
DATABASE = os.path.join(DATA_DIR, 'brettenwood.db')
PORTFOLIO_IMG_DIR = os.path.join(os.path.dirname(__file__), 'static', 'images', 'portfolio')

# Legacy JSON paths (used only for one-time migration)
_LEGACY_REVIEWS_FILE = os.path.join(DATA_DIR, 'reviews.json')
_LEGACY_PORTFOLIO_FILE = os.path.join(DATA_DIR, 'portfolio_descriptions.json')


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------
def get_db():
    """Get a database connection for the current request (cached on g)."""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row          # rows behave like dicts
        g.db.execute('PRAGMA journal_mode=WAL')  # better concurrency
    return g.db


@app.teardown_appcontext
def close_db(exc):
    """Close database connection at end of request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """Create tables if they don't exist and migrate legacy JSON data."""
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            name      TEXT    NOT NULL,
            email     TEXT,
            rating    INTEGER NOT NULL,
            title     TEXT,
            review    TEXT    NOT NULL,
            timestamp TEXT    NOT NULL
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS portfolio_descriptions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            filename    TEXT UNIQUE NOT NULL,
            title       TEXT,
            description TEXT,
            category    TEXT DEFAULT 'residential'
        )
    ''')

    conn.commit()

    # --- One-time migration from legacy JSON files -------------------------
    _migrate_legacy_reviews(conn)
    _migrate_legacy_portfolio(conn)

    conn.close()


def _migrate_legacy_reviews(conn):
    """Import reviews.json into the reviews table (runs once)."""
    if not os.path.exists(_LEGACY_REVIEWS_FILE):
        return
    # Only migrate if the table is empty
    count = conn.execute('SELECT COUNT(*) FROM reviews').fetchone()[0]
    if count > 0:
        return
    try:
        with open(_LEGACY_REVIEWS_FILE, 'r', encoding='utf-8') as f:
            legacy = json.load(f)
        for r in legacy:
            conn.execute(
                'INSERT INTO reviews (name, email, rating, title, review, timestamp) '
                'VALUES (?, ?, ?, ?, ?, ?)',
                (r.get('name', ''), r.get('email', ''), r.get('rating', 5),
                 r.get('title', ''), r.get('review', ''), r.get('timestamp', '')))
        conn.commit()
        print(f'[init] Migrated {len(legacy)} reviews from JSON -> SQLite')
    except (json.JSONDecodeError, KeyError) as exc:
        print(f'[init] Could not migrate reviews.json: {exc}')


def _migrate_legacy_portfolio(conn):
    """Import portfolio_descriptions.json into the DB (runs once)."""
    if not os.path.exists(_LEGACY_PORTFOLIO_FILE):
        return
    count = conn.execute('SELECT COUNT(*) FROM portfolio_descriptions').fetchone()[0]
    if count > 0:
        return
    try:
        with open(_LEGACY_PORTFOLIO_FILE, 'r', encoding='utf-8') as f:
            legacy = json.load(f)
        for filename, data in legacy.items():
            conn.execute(
                'INSERT INTO portfolio_descriptions (filename, title, description, category) '
                'VALUES (?, ?, ?, ?)',
                (filename, data.get('title', ''), data.get('description', ''),
                 data.get('category', 'residential')))
        conn.commit()
        print(f'[init] Migrated {len(legacy)} portfolio descriptions from JSON -> SQLite')
    except (json.JSONDecodeError, KeyError) as exc:
        print(f'[init] Could not migrate portfolio_descriptions.json: {exc}')


# ---------------------------------------------------------------------------
# Data access functions
# ---------------------------------------------------------------------------
def load_reviews():
    """Return all reviews as a list of dicts, newest first."""
    db = get_db()
    rows = db.execute(
        'SELECT * FROM reviews ORDER BY timestamp DESC'
    ).fetchall()
    return [dict(r) for r in rows]


def save_review(name, email, rating, title, review_text):
    """Insert a single review and return its id."""
    db = get_db()
    cur = db.execute(
        'INSERT INTO reviews (name, email, rating, title, review, timestamp) '
        'VALUES (?, ?, ?, ?, ?, ?)',
        (name, email, rating, title, review_text, datetime.now().isoformat()))
    db.commit()
    return cur.lastrowid


def load_portfolio_descriptions():
    """Return portfolio descriptions as {filename: {title, description, category}}."""
    db = get_db()
    rows = db.execute('SELECT * FROM portfolio_descriptions').fetchall()
    return {r['filename']: dict(r) for r in rows}


def save_portfolio_description(filename, title, description, category='residential'):
    """Insert or update a portfolio description."""
    db = get_db()
    db.execute(
        'INSERT INTO portfolio_descriptions (filename, title, description, category) '
        'VALUES (?, ?, ?, ?) '
        'ON CONFLICT(filename) DO UPDATE SET title=?, description=?, category=?',
        (filename, title, description, category, title, description, category))
    db.commit()


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

        # Generate a human-readable title from filename
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
# Tank Systems Data
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
    all_reviews = load_reviews()  # already sorted newest-first by the DB query
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

    save_review(name, email, int(rating), title, review_text)

    flash('Thank you for your review! It has been submitted successfully.', 'success')
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

    # In production: send email via SMTP / save to DB
    # For now just flash success
    flash(f'Thank you {name}! We will be in touch shortly.', 'success')
    return redirect(url_for('contact'))


# ---------------------------------------------------------------------------
# Initialise database on import (works with gunicorn & flask run)
# ---------------------------------------------------------------------------
init_db()

if __name__ == '__main__':
    # Ensure required directories exist
    for d in [PORTFOLIO_IMG_DIR,
              os.path.join(os.path.dirname(__file__), 'static', 'images', 'tanks')]:
        os.makedirs(d, exist_ok=True)

    app.run(debug=True, host='0.0.0.0', port=5000)
