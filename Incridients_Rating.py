import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import json
import os
from datetime import datetime
import time
import threading
import Model_Alpha as mod

vari = 25

def incri(email):
    _it = []
    count = 0
    for i in mod.recommend(email):
        if(count==vari):
            break
        _it.append(i[0])
        count+=1

    # Configuration for Firebase
    # Hardcoded username (you can change this to any username you want)
    USERNAME =  email#"bhaveshnayak934@gmail.com"

    # Set the path for auto-save CSV file
    CSV_PATH = "food_ratings_export.csv"

    # Initialize Firebase (runs only on first execution)
    @st.cache_resource
    def initialize_firebase():
        # Check if Firebase is already initialized
        if not firebase_admin._apps:
            # You need to create a service account key file from Firebase console
            # and save it as "serviceAccountKey.json" in the same directory
            # or update the path below to point to your key file
            
            # For Streamlit deployment where you can't use a file:
            # You can use this approach with environment variables or secrets
            if os.path.exists("serviceAccountKey.json"):
                cred = credentials.Certificate("serviceAccountKey.json")
            else:
                # Alternative approach using a JSON string for Streamlit Cloud
                # You'd set this as a secret in Streamlit Cloud
                key_dict = json.loads(st.secrets["firebase_service_account_key"])
                cred = credentials.Certificate(key_dict)
                
            firebase_admin.initialize_app(cred)
        
        return firestore.client()

    def fetch_all_ratings(db):
        """Fetch all food ratings from Firebase"""
        try:
            # Reference to the 'food_ratings' collection
            ratings_collection = db.collection('incri_rating')
            
            # Get all documents
            docs = ratings_collection.get()
            
            # Process the data
            all_ratings = []
            for doc in docs:
                data = doc.to_dict()
                username = data.get('username', 'unknown')
                ratings_dict = data.get('ratings', {})
                
                # Flatten the data structure for CSV
                for food, rating in ratings_dict.items():
                    all_ratings.append({
                        'username': username,
                        'food': food,
                        'rating': rating
                    })
            
            return all_ratings
        except Exception as e:
            st.error(f"Error fetching data from Firebase: {e}")
            return []

    def auto_export_to_csv(db, interval=300):
        """
        Automatically export data to CSV at regular intervals
        interval: time in seconds between exports (default 5 minutes)
        """
        while True:
            try:
                all_ratings = fetch_all_ratings(db)
                if all_ratings:
                    df = pd.DataFrame(all_ratings)
                    df.to_csv(CSV_PATH, index=False)
                    print(f"Data automatically exported to {CSV_PATH} at {datetime.now()}")
                else:
                    print(f"No data to export at {datetime.now()}")
                
                # Sleep for the specified interval
                time.sleep(interval)
            except Exception as e:
                print(f"Error in auto export: {e}")
                time.sleep(interval)  # Still wait before retrying

    def setup_auto_export(db):
        """Set up automatic export in a separate thread"""
        if 'auto_export_running' not in st.session_state:
            st.session_state.auto_export_running = True
            export_thread = threading.Thread(target=auto_export_to_csv, args=(db,))
            export_thread.daemon = True  # Thread will exit when main program exits
            export_thread.start()
            return True
        return False

    def main():
        st.title("Food Rating")
        
        # Display username (hardcoded)
        st.markdown(f"**User:** {USERNAME}")
        
        # Connect to Firebase
        try:
            db = initialize_firebase()
            firebase_available = True
            # Set up auto-export if Firebase is available
            setup_auto_export(db)
        except Exception as e:
            st.error(f"Firebase connection error: {e}")
            firebase_available = False
        
        # Sample list of food items (you can replace with your own)
        food_items = [
            "Pizza",
            "Burger",
            "Sushi",
            "Pasta",
            "Salad"
        ]
        
        # Initialize session state for ratings if not already present
        if 'ratings' not in st.session_state:
            st.session_state.ratings = {item: 5 for item in _it}  # Default rating of 5
        
        # Create two columns layout
        col1, col2 = st.columns(2)
        
        # Display items in the left column
        with col1:
            st.subheader("Food Items")
            for item in _it:
                st.write(f"• {item}")
        
        # Display rating options in the right column
        with col2:
            st.subheader("Ratings (1-10)")
            for item in _it:
                st.session_state.ratings[item] = st.slider(
                    f"Rate {item}",
                    min_value=1,
                    max_value=10,
                    value=st.session_state.ratings[item]
                )
        
        # Display current ratings summary
        st.divider()
        st.subheader("Current Ratings")
        
        # Create a DataFrame to display all ratings
        ratings_df = pd.DataFrame({
            'Food': list(st.session_state.ratings.keys()),
            'Rating': list(st.session_state.ratings.values())
        })
        
        st.dataframe(ratings_df, use_container_width=True)
        
        # Button to save ratings to Firebase
        if st.button("Submit"):
            if firebase_available:
                save_to_firebase(db, USERNAME, st.session_state.ratings)
                
                # Force an immediate export to CSV after submission
                all_ratings = fetch_all_ratings(db)
                if all_ratings:
                    df = pd.DataFrame(all_ratings)
                    df.to_csv(CSV_PATH, index=False)
            else:
                st.error("Firebase is not configured properly. Check your credentials.")

    def save_to_firebase(db, username, ratings):
        try:
            # Reference to the 'food_ratings' collection
            ratings_collection = db.collection('incri_rating')
            
            # Prepare data to save
            data = {
                'username': username,
                'timestamp': datetime.now(),
                'ratings': ratings
            }
            
            # Add the document to Firestore
            doc_ref = ratings_collection.add(data)
            
            st.success(f"Ratings submitted successfully!")
            
        except Exception as e:
            st.error(f"Error saving to Firebase: {e}")

    if __name__ == "__main__":
        main()
#incri('yadaw@gmail.com')