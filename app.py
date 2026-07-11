import os
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

    cur.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            description TEXT,
            category    TEXT DEFAULT 'residential',
            created_at  TEXT NOT NULL
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS project_images (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id  INTEGER NOT NULL,
            filename    TEXT NOT NULL,
            is_primary  BOOLEAN DEFAULT 0,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
    ''')

    # Migration from old portfolio_descriptions table to projects
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='portfolio_descriptions'")
    if cur.fetchone():
        old_rows = cur.execute("SELECT filename, title, description, category FROM portfolio_descriptions").fetchall()
        for row in old_rows:
            cur.execute("SELECT id FROM project_images WHERE filename=?", (row['filename'],))
            if not cur.fetchone():
                cur.execute("INSERT INTO projects (title, description, category, created_at) VALUES (?, ?, ?, ?)",
                            (row['title'] or 'Untitled', row['description'] or '', row['category'], datetime.now().isoformat()))
                project_id = cur.lastrowid
                cur.execute("INSERT INTO project_images (project_id, filename, is_primary) VALUES (?, ?, 1)", (project_id, row['filename']))

    conn.commit()
    conn.close()


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


def load_projects():
    """Return all projects with their associated images."""
    db = get_db()
    rows = db.execute('''
        SELECT p.id, p.title, p.description, p.category, p.created_at,
               GROUP_CONCAT(i.filename) as filenames
        FROM projects p
        LEFT JOIN project_images i ON p.id = i.project_id
        GROUP BY p.id
        ORDER BY p.id DESC
    ''').fetchall()

    projects = []
    for r in rows:
        filenames = r['filenames'].split(',') if r['filenames'] else []
        primary_image = filenames[0] if filenames else None
        
        projects.append({
            'id': r['id'],
            'title': r['title'],
            'description': r['description'],
            'category': r['category'],
            'created_at': r['created_at'],
            'images': [{'url': f'images/portfolio/{fn}', 'filename': fn} for fn in filenames],
            'primary_image': {'url': f'images/portfolio/{primary_image}', 'filename': primary_image} if primary_image else None
        })
    return projects


def save_project(title, description, category, filenames):
    """Save a new project with multiple images."""
    db = get_db()
    cur = db.cursor()
    cur.execute(
        'INSERT INTO projects (title, description, category, created_at) VALUES (?, ?, ?, ?)',
        (title, description, category, datetime.now().isoformat())
    )
    project_id = cur.lastrowid
    
    for idx, fn in enumerate(filenames):
        is_primary = 1 if idx == 0 else 0
        cur.execute('INSERT INTO project_images (project_id, filename, is_primary) VALUES (?, ?, ?)', 
                    (project_id, fn, is_primary))
        
    db.commit()


# ---------------------------------------------------------------------------
# Tank Systems Data — grouped by size, each with JoJo + Eco variants
# ---------------------------------------------------------------------------
TANK_SYSTEMS = [
    {
        'id': '1000L',
        'capacity': '1000L',
        'pump': 'Grundfos CM3-5 Pressure Pump',
        'pump_specs': '0.55 kW | 45 L/min | Max 5 bar',
        'ideal_for': 'Small households, apartments, townhouses',
        'brands': {
            'jojo': {
                'label': 'JoJo',
                'image': 'images/tanks/jojo_1000.png',
                'tank_name': '1000L JoJo Slimline Vertical Tank',
                'stand': 'Heavy-Duty Galvanised Steel Tank Stand',
            },
            'eco': {
                'label': 'Eco',
                'image': 'images/tanks/eco_1000.jpg',
                'tank_name': '1000L Eco Slim Vertical Tank (UV Stabilised)',
                'stand': 'Powder-Coated Steel Tank Stand',
            },
        },
        'shared_components': [
            'Grundfos CM3-5 Pressure Pump',
            'Pressure Switch (adjustable cut-in/cut-out)',
            'Non-Return / Check Valve (32mm)',
            'Full Installation Kit (pipework, fittings, float valve)',
            '1-Year Labour Warranty',
        ],
    },
    {
        'id': '2500L',
        'capacity': '2500L',
        'pump': 'Grundfos CM5-7 Pressure Pump',
        'pump_specs': '0.75 kW | 65 L/min | Max 7 bar',
        'ideal_for': 'Medium to large family homes',
        'brands': {
            'jojo': {
                'label': 'JoJo',
                'image': 'images/tanks/jojo_2500.webp',
                'tank_name': '2500L JoJo Vertical Storage Tank',
                'stand': 'Heavy-Duty Galvanised Steel Tank Stand',
            },
            'eco': {
                'label': 'Eco',
                'image': 'images/tanks/eco_2500.webp',
                'tank_name': '2500L Eco Vertical Storage Tank (UV Stabilised)',
                'stand': 'Powder-Coated Steel Tank Stand',
            },
        },
        'shared_components': [
            'Grundfos CM5-7 Pressure Pump',
            'Pressure Switch (adjustable cut-in/cut-out)',
            'Non-Return / Check Valve (40mm)',
            'Full Installation Kit (pipework, fittings, float valve)',
            '1-Year Labour Warranty',
        ],
    },
    {
        'id': '5000L',
        'capacity': '5000L',
        'pump': 'Grundfos CM10-2 Pressure Pump',
        'pump_specs': '1.1 kW | 120 L/min | Max 8 bar',
        'ideal_for': 'Large family homes, small commercial',
        'brands': {
            'jojo': {
                'label': 'JoJo',
                'image': 'images/tanks/jojo_5000.jpg',
                'tank_name': '5000L JoJo Vertical Storage Tank',
                'stand': 'Heavy-Duty Galvanised Steel Tank Stand',
            },
            'eco': {
                'label': 'Eco',
                'image': 'images/tanks/eco_5000.jpg',
                'tank_name': '5000L Eco Vertical Storage Tank (UV Stabilised)',
                'stand': 'Powder-Coated Steel Tank Stand',
            },
        },
        'shared_components': [
            'Grundfos CM10-2 Pressure Pump',
            'Pressure Switch (adjustable cut-in/cut-out)',
            'Non-Return / Check Valve (50mm)',
            'Full Installation Kit (pipework, fittings, float valve)',
            'Level Indicator / Gauge',
            '1-Year Labour Warranty',
        ],
    },
]


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/systems')
def systems():
    size_filter = request.args.get('size', 'all')

    filtered = TANK_SYSTEMS
    if size_filter != 'all':
        filtered = [s for s in filtered if s['capacity'] == size_filter]

    return render_template('systems.html',
                           systems=filtered,
                           size_filter=size_filter)


@app.route('/portfolio')
def portfolio():
    projects = load_projects()
    category_filter = request.args.get('category', 'all')

    if category_filter != 'all':
        projects = [p for p in projects if p.get('category') == category_filter]

    return render_template('portfolio.html',
                           projects=projects,
                           category_filter=category_filter)


# ---------------------------------------------------------------------------
# Hidden Admin Portal Routes
# ---------------------------------------------------------------------------

ADMIN_PASSWORD = os.environ.get('BW_ADMIN_PASSWORD', 'bwProjects2026')

@app.route('/bw-admin-portal', methods=['GET', 'POST'])
def admin_portal():
    from flask import session

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'login':
            password = request.form.get('password')
            if password == ADMIN_PASSWORD:
                session['is_admin'] = True
                flash('Successfully logged into Admin Dashboard.', 'success')
            else:
                flash('Incorrect password.', 'danger')
            return redirect(url_for('admin_portal'))

        elif action == 'logout':
            session.pop('is_admin', None)
            flash('Logged out.', 'success')
            return redirect(url_for('admin_portal'))

    is_authenticated = session.get('is_admin', False)

    # If logged in, show existing portfolio items
    portfolio_items = []
    if is_authenticated:
        portfolio_items = load_projects()

    return render_template('admin.html', is_authenticated=is_authenticated, portfolio=portfolio_items)


@app.route('/submit_project', methods=['POST'])
def submit_project():
    from flask import session
    if not session.get('is_admin', False):
        flash('Unauthorized.', 'danger')
        return redirect(url_for('admin_portal'))

    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    category = request.form.get('category', 'residential').strip()
    files = request.files.getlist('files')

    if not title or not files or all(f.filename == '' for f in files):
        flash('Project title and at least one image file are required.', 'danger')
        return redirect(url_for('admin_portal'))

    try:
        os.makedirs(PORTFOLIO_IMG_DIR, exist_ok=True)
        saved_filenames = []
        for i, file in enumerate(files):
            if file and file.filename:
                ext = os.path.splitext(file.filename)[1]
                secure_name = f"portfolio_{datetime.now().strftime('%Y%m%d%H%M%S')}_{i}{ext}"
                file.save(os.path.join(PORTFOLIO_IMG_DIR, secure_name))
                saved_filenames.append(secure_name)

        if saved_filenames:
            save_project(title, description, category, saved_filenames)
            flash('New portfolio project successfully uploaded!', 'success')
        else:
            flash('No valid images were uploaded.', 'danger')
    except Exception as e:
        app.logger.error(f'Failed to upload project: {e}')
        flash(f'Error uploading project: {e}', 'danger')

    return redirect(url_for('admin_portal'))


@app.route('/delete_project/<int:project_id>', methods=['POST'])
def delete_project(project_id):
    from flask import session
    if not session.get('is_admin', False):
        flash('Unauthorized.', 'danger')
        return redirect(url_for('admin_portal'))

    try:
        db = get_db()
        # Delete image files from disk
        rows = db.execute('SELECT filename FROM project_images WHERE project_id = ?', (project_id,)).fetchall()
        for row in rows:
            filepath = os.path.join(PORTFOLIO_IMG_DIR, row['filename'])
            if os.path.exists(filepath):
                os.remove(filepath)
                
        # Delete metadata from SQLite
        db.execute('DELETE FROM project_images WHERE project_id = ?', (project_id,))
        db.execute('DELETE FROM projects WHERE id = ?', (project_id,))
        db.commit()

        flash('Project deleted.', 'success')
    except Exception as e:
        app.logger.error(f'Failed to delete project: {e}')
        flash('Error deleting project.', 'danger')

    return redirect(url_for('admin_portal'))


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

    # In production: send email via SMTP or save to DB
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
