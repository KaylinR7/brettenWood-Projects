import os
import firebase_admin
from firebase_admin import credentials, firestore

KEY = r'C:\Users\Kaylin_r7\Downloads\bretten-wood-firebase-adminsdk-fbsvc-7f400e45c0.json'
cred = credentials.Certificate(KEY)
firebase_admin.initialize_app(cred)
db = firestore.client()

docs = list(db.collection('reviews').stream())
print(f'Found {len(docs)} reviews:')
for d in docs:
    data = d.to_dict()
    name = data.get('name', 'unknown')
    rating = data.get('rating', '?')
    title = data.get('title', '')
    print(f'  - {name} | rating={rating} | {title}')
