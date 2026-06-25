"""
seed_reviews.py
---------------
Seeds the Firestore 'reviews' collection with sample review data.

Usage:
    python seed_reviews.py
"""

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

SAMPLE_REVIEWS = [
    {
        'name': 'James Thornton',
        'email': 'james.t@example.com',
        'rating': 5,
        'title': 'Excellent installation — highly recommend!',
        'review': (
            'BrettenWood installed a 5000L JoJo tank system at our property in Ballito. '
            'The team was professional, punctual and tidy. The pump system has been running '
            'flawlessly for 3 months. Could not be happier with the service.'
        ),
        'timestamp': '2026-05-10T09:15:00',
    },
    {
        'name': 'Samantha Dube',
        'email': 'sam.dube@example.com',
        'rating': 5,
        'title': 'Fast, clean and professional',
        'review': (
            'We had a 2500L Eco tank installed with a Grundfos pump. The installation was done '
            'in a single day with minimal disruption. Great communication from start to finish. '
            'The water pressure in our house is now perfect.'
        ),
        'timestamp': '2026-05-22T14:30:00',
    },
    {
        'name': 'Ruan van der Merwe',
        'email': 'ruan.vdm@example.com',
        'rating': 4,
        'title': 'Very good service overall',
        'review': (
            'Solid workmanship on our 1000L JoJo installation. Minor delay on the day due to '
            'parts, but the team kept us informed and sorted everything out quickly. Would use '
            'BrettenWood again without hesitation.'
        ),
        'timestamp': '2026-06-01T11:00:00',
    },
    {
        'name': 'Priya Naidoo',
        'email': 'priya.n@example.com',
        'rating': 5,
        'title': 'Game changer during load shedding season',
        'review': (
            'With all the water outages in our area, having a 5000L backup tank has been a '
            'lifesaver. BrettenWood\'s team did a brilliant job. Clean pipework, solid tank '
            'stand, and the Grundfos pump delivers great pressure. 10/10.'
        ),
        'timestamp': '2026-06-08T16:45:00',
    },
    {
        'name': 'Craig Steyn',
        'email': 'craig.s@example.com',
        'rating': 5,
        'title': 'Best investment for our home',
        'review': (
            'Had the 2500L Eco system installed last month. The team were friendly, efficient '
            'and left the site spotless. Pricing was transparent with no hidden extras. Our '
            'household has not experienced a single water disruption since.'
        ),
        'timestamp': '2026-06-15T10:20:00',
    },
]


def seed():
    col = db.collection('reviews')

    # Check if already seeded
    existing = list(col.limit(1).stream())
    if existing:
        print('Reviews collection already has data. Skipping seed to avoid duplicates.')
        print('Delete existing documents in Firebase Console if you want to re-seed.')
        return

    for i, review in enumerate(SAMPLE_REVIEWS):
        col.add(review)
        print(f'  Added review {i + 1}/{len(SAMPLE_REVIEWS)}: {review["name"]}')

    print(f'\nDone — {len(SAMPLE_REVIEWS)} sample reviews added to Firestore.')


if __name__ == '__main__':
    seed()
