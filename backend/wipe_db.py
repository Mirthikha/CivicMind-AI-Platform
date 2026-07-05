# wipe_db.py
import os
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase
cred_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "firebase_credentials.json")
if not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)

db = firestore.client()

def delete_collection(collection_name):
    print(f"Purging collection: '{collection_name}'...")
    docs = db.collection(collection_name).stream()
    count = 0
    for doc in docs:
        doc.reference.delete()
        count += 1
    print(f" Successfully deleted {count} documents from '{collection_name}'.")

if __name__ == "__main__":
    print("🧹 Starting CivicMind Database Clean-Up...")
    # Wipe the normal complaints
    delete_collection("complaints")
    # Wipe the emergency escalations
    delete_collection("emergencies")

    delete_collection("citizens")
    print("✨ Database is now completely fresh and ready!")