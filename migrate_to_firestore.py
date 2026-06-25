"""
migrate_to_firestore.py
-----------------------
One-time script to seed Firestore with existing local JSON data.

Usage:
    python migrate_to_firestore.py

Make sure GOOGLE_APPLICATION_CREDENTIALS is set, or update KEY_PATH below.
"""

import json
import os

import firebase_admin
from firebase_admin import credentials, firestore

KEY_PATH = (
    os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    or r'C:\Users\Kaylin_r7\Downloads\bretten-wood-firebase-adminsdk-fbsvc-7f400e45c0.json'
)

cred = credentials.Certificate(KEY_PATH)
firebase_admin.initialize_app(cred)
db = firestore.client()

BASE_DIR = os.path.dirname(__file__)


def migrate_reviews():
    reviews_file = os.path.join(BASE_DIR, 'data', 'reviews.json')
    if not os.path.exists(reviews_file):
        print('  No reviews.json found — skipping.')
        return

    with open(reviews_file, 'r', encoding='utf-8') as f:
        reviews = json.load(f)

    if not reviews:
        print('  reviews.json is empty — skipping.')
        return

    col = db.collection('reviews')
    for i, review in enumerate(reviews):
        col.add(review)
        print(f'  Migrated review {i + 1}/{len(reviews)}: {review.get("name", "unknown")}')

    print(f'  Done — {len(reviews)} reviews uploaded.')


def migrate_portfolio_descriptions():
    desc_file = os.path.join(BASE_DIR, 'data', 'portfolio_descriptions.json')
    if not os.path.exists(desc_file):
        print('  No portfolio_descriptions.json found — skipping.')
        return

    with open(desc_file, 'r', encoding='utf-8') as f:
        descriptions = json.load(f)

    if not descriptions:
        print('  portfolio_descriptions.json is empty — skipping.')
        return

    col = db.collection('portfolio_descriptions')
    for filename, data in descriptions.items():
        col.document(filename).set(data)
        print(f'  Migrated portfolio entry: {filename}')

    print(f'  Done — {len(descriptions)} portfolio descriptions uploaded.')


if __name__ == '__main__':
    print('=== Migrating reviews ===')
    migrate_reviews()

    print('\n=== Migrating portfolio descriptions ===')
    migrate_portfolio_descriptions()

    print('\nMigration complete.')
