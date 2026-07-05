import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
import os

load_dotenv()

# Connect to Firebase
cred = credentials.Certificate("backend/firebase_credentials.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

# Write a test document
db.collection('test').document('connection_test').set({
    'message': 'CivicMind Firebase connected!',
    'project': 'civicmind'
})

# Read it back
doc = db.collection('test').document('connection_test').get()
print("Firebase says:", doc.to_dict())
print("✅ Firebase is working!")