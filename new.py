import streamlit as st
import pyrebase
import time
import firebase_admin
from firebase_admin import credentials, firestore
import uuid
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import os
import json
import requests
import runpy
import importlib
import streamlit as st
import pandas as pd
import time
import threading
import Model_Alpha as mod

vari = 25

# Set page config
st.set_page_config(
    page_title="Diet Recommendation App",
    page_icon="🥗",
    layout="wide"
)

# Firebase configuration for authentication
firebase_config = {
    'apiKey': "AIzaSyBfOsDs3E17J2TGywpnwwysIASng9NlHkM",
    'authDomain': "diet-webapp.firebaseapp.com",
    'projectId': "diet-webapp",
    'storageBucket': "diet-webapp.firebasestorage.app",
    'messagingSenderId': "747949301601",
    'appId': "1:747949301601:web:76c51cb1e062c1e4486f20",
    'measurementId': "G-0KXZD9LRK6",
    "databaseURL": ""
}

#Functions Import

def reci(email,ingredients):
    # Initialize Firebase
    def initialize_firebase():
        if not firebase_admin._apps:
            cred = credentials.Certificate("serviceAccountKey.json")
            firebase_admin.initialize_app(cred)
        return firestore.client()

    # Spoonacular API Configuration
    SPOONACULAR_API_KEY = "f1deca61a00a46678ff751d8535e4fc1"
    SPOONACULAR_API_URL = "https://api.spoonacular.com/recipes/complexSearch"

    # Function to search recipes via Spoonacular API
    def search_recipes(query,email):
        params = {
            "apiKey": SPOONACULAR_API_KEY,
            "query": query,
            "number": 5,
            "addRecipeInformation": True,
            "fillIngredients": True,
            "instructionsRequired": True
        }
        
        try:
            response = requests.get(SPOONACULAR_API_URL, params=params)
            
            if response.status_code == 200:
                return response.json()
            else:
                st.error(f"Error fetching recipes: {response.status_code}")
                return None
        except Exception as e:
            st.error(f"API request failed: {str(e)}")
            return None

    # Save multiple ratings to Firebase
    def save_multiple_ratings_to_firebase(db, ratings_data):
        try:
            for rating_info in ratings_data:
                user_id = rating_info['user_id']
                recipe_id = rating_info['recipe_id']
                recipe_name = rating_info['recipe_name']
                rating = rating_info['rating']
                
                rating_ref = db.collection('recipe').document(f"{user_id}_{recipe_id}")
                
                rating_data = {
                    'user_id': user_id,
                    'recipe_id': str(recipe_id),
                    'recipe_name': recipe_name,
                    'rating': rating,
                    'timestamp': firestore.SERVER_TIMESTAMP
                }
                
                rating_ref.set(rating_data)
            
            # Generate CSV
            generate_csv_from_firebase(db)
            
            st.success(f"All ratings saved successfully!")
            return True
        except Exception as e:
            st.error(f"Error saving ratings: {str(e)}")
            return False

    # Generate CSV from Firebase data
    def generate_csv_from_firebase(db):
        try:
            ratings_ref = db.collection('recipe').get()
            
            ratings_data = []
            for rating in ratings_ref:
                rating_data = rating.to_dict()
                
                ratings_data.append({
                    'user_id': rating_data.get('user_id', ''),
                    'recipe_id': rating_data.get('recipe_id', ''),
                    'recipe_name': rating_data.get('recipe_name', ''),
                    'rating': rating_data.get('rating', 0),
                    'timestamp': rating_data.get('timestamp', '')
                })
            
            # Create DataFrame
            df = pd.DataFrame(ratings_data)
            
            # If the DataFrame is empty, create the column structure
            if df.empty:
                df = pd.DataFrame(columns=['user_id', 'recipe_id', 'recipe_name', 'rating', 'timestamp'])
            
            # Save to CSV
            csv_path = "recipe_ratings_database.csv"
            df.to_csv(csv_path, index=False)
            
            return csv_path
        except Exception as e:
            st.error(f"Error generating CSV: {str(e)}")
            return None

    # Function to get user's rated recipes
    def get_user_ratings(db, user_id):
        try:
            ratings = db.collection('recipe').where('user_id', '==', user_id).get()
            return [rating.to_dict() for rating in ratings]
        except Exception as e:
            st.error(f"Error fetching user ratings: {str(e)}")
            return []

    # Function to get recipe recommendations
    def get_recommendations(db, user_id):
        user_ratings = get_user_ratings(db, user_id)
        
        if not user_ratings:
            return None
        
        sorted_ratings = sorted(user_ratings, key=lambda x: x.get('rating', 0), reverse=True)
        
        if sorted_ratings:
            top_recipe = sorted_ratings[0]
            recipe_name = top_recipe.get('recipe_name', '')
            search_term = recipe_name.split()[0]
            
            return search_recipes(search_term)
        
        return None

    # Display recipe with rating
    def display_recipe(recipe, email):
        with st.expander(f"{recipe['title']}"):
            col1, col2 = st.columns([1, 2])
            
            with col1:
                # Display recipe image
                st.image(recipe['image'], width=200)
                
                recipe_id = recipe['id']
                recipe_name = recipe['title']
                
                # Check if the recipe already has a rating in the session state
                rating_key = f"rating_{recipe_id}"
                if rating_key not in st.session_state:
                    # Try to get existing rating from pending ratings
                    if 'pending_ratings' in st.session_state:
                        for rating_data in st.session_state.pending_ratings:
                            if rating_data['recipe_id'] == str(recipe_id):
                                st.session_state[rating_key] = rating_data['rating']
                                break
                        else:
                            st.session_state[rating_key] = 3
                    else:
                        st.session_state[rating_key] = 3
                
                # Generate a more unique key for the slider
                # Use the recipe_id and a unique identifier - using title which is likely to be unique
                unique_slider_key = f"slider_{recipe_id}_{hash(recipe_name) % 10000}"
                
                # Rating system
                st.session_state[rating_key] = st.slider(
                    "Rate this recipe", 
                    1, 5, 
                    st.session_state[rating_key], 
                    key=unique_slider_key
                )
                
                # Add to pending ratings
                if 'pending_ratings' not in st.session_state:
                    st.session_state.pending_ratings = []
                
                # Check if this recipe is already in pending ratings
                recipe_exists = False
                for i, rating_data in enumerate(st.session_state.pending_ratings):
                    if rating_data['recipe_id'] == str(recipe_id):
                        # Update the rating
                        st.session_state.pending_ratings[i]['rating'] = st.session_state[rating_key]
                        recipe_exists = True
                        break
                
                if not recipe_exists:
                    st.session_state.pending_ratings.append({
                        'user_id': email,
                        'recipe_id': str(recipe_id),
                        'recipe_name': recipe_name,
                        'rating': st.session_state[rating_key]
                    })
            
            with col2:
                # Display recipe details
                if 'calories' in recipe:
                    st.markdown(f"**Calories:** {recipe['calories']}")
                
                if 'diets' in recipe and recipe['diets']:
                    st.markdown(f"**Diets:** {', '.join(recipe['diets'])}")
                
                st.markdown("### Ingredients")
                for ingredient in recipe['extendedIngredients']:
                    st.markdown(f"- {ingredient['original']}")
                
                st.markdown("### Instructions")
                instructions = recipe.get('instructions', 'No instructions available for this recipe.')
                st.write(instructions.replace('\n', '\n\n') if instructions else "No instructions available for this recipe.")
                
                st.markdown(f"[View Full Recipe]({recipe.get('sourceUrl', '#')})")

    # Streamlit UI
    def main():
        st.title("Recipe Recommender")
        
        # Initialize Firebase
        db = initialize_firebase()
        
        # Session state initialization
        if 'counter' not in st.session_state:
            st.session_state.counter = 0
        
        if 'searched_recipes' not in st.session_state:
            st.session_state.searched_recipes = {}
        
        if 'pending_ratings' not in st.session_state:
            st.session_state.pending_ratings = []
        
        # User authentication
        st.sidebar.header("User Authentication")
        #email = st.sidebar.text_input("Email")
        
        if not email:
            st.warning("Please enter your email to continue")
            return
        
        # App tabs
        tab1, tab2, tab3 = st.tabs(["Browse Recipes", "Recommendations", "My Ratings"])
        
        with tab1:
            st.header("Browse Recipes by Ingredient")
            
            # Predefined ingredients list
            #ingredients = ["Chicken", "Potato", "Milk", "Oats", "Fish", "Rice", "Pasta"]
            
            selected_ingredient = st.selectbox("Select an ingredient", ingredients)
            
            if st.button("Find Recipes") and selected_ingredient:
                with st.spinner(f"Searching for {selected_ingredient} recipes..."):
                    results = search_recipes(selected_ingredient,email)
                    
                    if results:
                        recipes = results.get('results', [])
                        if recipes:
                            # Store recipes in session state
                            st.session_state.searched_recipes[selected_ingredient] = recipes
            
            # Display all searched recipes
            for ingredient, recipes in st.session_state.searched_recipes.items():
                st.subheader(f"{ingredient} Recipes ({len(recipes)})")
                for recipe in recipes:
                    display_recipe(recipe, email)
            
            # Add submit button in the Browse Recipes tab
            if 'pending_ratings' in st.session_state and st.session_state.pending_ratings:
                st.divider()
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.info(f"You have {len(st.session_state.pending_ratings)} recipes rated and ready to submit")
                with col2:
                    if st.button("Submit All Ratings"):
                        save_multiple_ratings_to_firebase(db, st.session_state.pending_ratings)
                        st.session_state.pending_ratings = []
                        st.rerun()
        
        with tab2:
            st.header("Your Recommendations")
            if st.button("Get Recommendations"):
                with st.spinner("Finding recommendations for you..."):
                    recommendations = get_recommendations(db, email)
                    
                    if recommendations:
                        recipes = recommendations.get('results', [])
                        if recipes:
                            # Store in session state
                            st.session_state.searched_recipes["Recommended"] = recipes
                    else:
                        st.info("Rate some recipes first to get recommendations!")
            
            # Display recommendations if they exist
            if "Recommended" in st.session_state.searched_recipes:
                st.subheader(f"Recommended Recipes ({len(st.session_state.searched_recipes['Recommended'])})")
                for recipe in st.session_state.searched_recipes["Recommended"]:
                    display_recipe(recipe, email)
                
                # Add submit button for recommendations tab too
                if 'pending_ratings' in st.session_state and st.session_state.pending_ratings:
                    st.divider()
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.info(f"You have {len(st.session_state.pending_ratings)} recipes rated and ready to submit")
                    with col2:
                        if st.button("Submit All Ratings", key="submit_recommendations"):
                            save_multiple_ratings_to_firebase(db, st.session_state.pending_ratings)
                            st.session_state.pending_ratings = []
                            st.rerun()
        
        with tab3:
            st.header("Your Ratings")
            st.info("All your ratings are being saved in our database. These ratings help us provide better recommendations for you.")
            
            # Show a simple message about ratings instead of the detailed view
            user_ratings = get_user_ratings(db, email)
            if user_ratings:
                st.success(f"You have rated {len(user_ratings)} recipes so far. Great job!")
            else:
                st.info("You haven't saved any ratings yet. Start rating recipes to get personalized recommendations!")

    if __name__ == "__main__":
        main()

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

# Initialize Firebase for auth
firebase = pyrebase.initialize_app(firebase_config)
auth = firebase.auth()

# Initialize Firestore (for database operations)
@st.cache_resource
def initialize_firebase_admin():
    if not firebase_admin._apps:
        # Use direct file path for simplicity during development
        cred = credentials.Certificate('serviceAccountKey.json')
        firebase_admin.initialize_app(cred)
    return firestore.client()

# Try to initialize Firestore
try:
    db = initialize_firebase_admin()
except Exception as e:
    st.warning("Firestore initialization failed. Some features may not work properly.")
    db = None

# Create data directory if it doesn't exist
if not os.path.exists('data'):
    os.makedirs('data')

# Function to save survey data to CSV
def save_to_csv(data):
    try:
        # Create a filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"data/survey_data_{timestamp}.csv"
        
        # Convert data to DataFrame
        df = pd.DataFrame([data])
        
        # If we already have a main CSV file, append to it
        main_csv = "data/all_survey_responses.csv"
        if os.path.exists(main_csv):
            existing_df = pd.read_csv(main_csv)
            combined_df = pd.concat([existing_df, df], ignore_index=True)
            combined_df.to_csv(main_csv, index=False)
        else:
            # If first entry, create the file
            df.to_csv(main_csv, index=False)
        
        # Also save individual response
        df.to_csv(filename, index=False)
        
        return True, filename
    except Exception as e:
        return False, str(e)

# Function to calculate BMI
def calculate_bmi(weight, height):
    # Height in meters (convert from cm)
    height_m = height / 100
    # BMI formula: weight (kg) / height^2 (m)
    bmi = weight / (height_m ** 2)
    return round(bmi, 2)

# Function to determine BMI category
def get_bmi_category(bmi):
    if bmi < 18.5:
        return "Underweight"
    elif bmi < 25:
        return "Normal weight"
    elif bmi < 30:
        return "Overweight"
    else:
        return "Obese"

# Function to save data to Firebase
def save_to_firebase(data):
    try:
        if db is None:
            return False, "Database not initialized"
        # Generate a unique ID for this submission
        doc_id = str(uuid.uuid4())
        # Add timestamp
        data['timestamp'] = datetime.now()
        # Save to Firestore
        db.collection('survey_responses').document(doc_id).set(data)
        return True, doc_id
    except Exception as e:
        return False, str(e)

# Function to check if user has completed the survey
def has_completed_survey(email):
    try:
        if db is None:
            return False
        # Query Firestore to check if user has a survey record
        query = db.collection('survey_responses').where('email', '==', email).limit(1).get()
        return len(query) > 0
    except Exception as e:
        st.error(f"Error checking survey status: {e}")
        return False

# Function to get user's survey data
def get_user_survey_data(email):
    try:
        if db is None:
            return None
        # Query Firestore to get user's survey data
        query = db.collection('survey_responses').where('email', '==', email).limit(1).get()
        if len(query) > 0:
            return query[0].to_dict()
        return None
    except Exception as e:
        st.error(f"Error retrieving survey data: {e}")
        return None

# Initialize session state variables
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_info' not in st.session_state:
    st.session_state.user_info = None
if 'current_page' not in st.session_state:
    st.session_state.current_page = "dashboard"
if 'first_login' not in st.session_state:
    st.session_state.first_login = False
if 'survey_completed' not in st.session_state:
    st.session_state.survey_completed = False

# Authentication Section (shown when not logged in)
if not st.session_state.logged_in:
    st.title("🥗 Diet Recommendation App")
    st.write("Log in or sign up to get personalized diet recommendations")

    # Create tabs for Login and Signup
    tab1, tab2 = st.tabs(["Login", "Signup"])

    # Login Tab
    with tab1:
        st.header("Login")
        login_email = st.text_input("Email", key="login_email")
        login_password = st.text_input("Password", type="password", key="login_password")
        
        login_button = st.button("Login")
        
        if login_button:
            if not login_email or not login_password:
                st.error("Please enter both email and password")
            else:
                try:
                    user = auth.sign_in_with_email_and_password(login_email, login_password)
                    st.success("Login successful!")
                    st.session_state.logged_in = True
                    st.session_state.user_info = user
                    
                    # Check if user has completed the survey
                    completed = has_completed_survey(user['email'])
                    st.session_state.survey_completed = completed
                    
                    # Set appropriate landing page
                    if not completed:
                        st.session_state.first_login = True
                        st.session_state.current_page = "survey"
                    else:
                        st.session_state.current_page = "dashboard"
                    
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Login failed: {e}")

    # Signup Tab
    with tab2:
        st.header("Create an Account")
        signup_email = st.text_input("Email", key="signup_email")
        signup_password = st.text_input("Password", type="password", key="signup_password")
        signup_confirm_password = st.text_input("Confirm Password", type="password", key="signup_confirm_password")
        
        signup_button = st.button("Sign Up")
        
        if signup_button:
            if not signup_email or not signup_password or not signup_confirm_password:
                st.error("Please fill in all fields")
            elif signup_password != signup_confirm_password:
                st.error("Passwords do not match")
            else:
                try:
                    user = auth.create_user_with_email_and_password(signup_email, signup_password)
                    st.success("Account created successfully!")
                    st.session_state.logged_in = True
                    st.session_state.user_info = user
                    st.session_state.first_login = True
                    st.session_state.current_page = "survey"  # Direct to survey after signup
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Signup failed: {e}")

# Dashboard (shown when logged in)
else:
    # Check if it's first login and survey not completed - direct to survey
    if st.session_state.first_login and not st.session_state.survey_completed:
        st.session_state.current_page = "survey"
    
    # Create a two-column layout
    col1, col2 = st.columns([1, 4])
    
    # Left sidebar for navigation
    with col1:
        st.sidebar.title("Diet Dashboard")
        st.sidebar.write(f"Welcome, {st.session_state.user_info['email']}")
        
        # Navigation menu
        st.sidebar.markdown("### Menu")
        
        # Navigation buttons
        if st.sidebar.button("Get Recommendation", use_container_width=True):
            st.session_state.current_page = "recommendation"
            st.rerun()

        if st.sidebar.button("Get Recipy", use_container_width=True):
            st.session_state.current_page = "recipy"
            st.rerun()

        if st.sidebar.button("My Profile", use_container_width=True):
            st.session_state.current_page = "profile"
            st.rerun()
            
        # Don't show survey after first completion
        if not st.session_state.survey_completed:
            if st.sidebar.button("Diet Survey", use_container_width=True):
                st.session_state.current_page = "survey"
                st.rerun()
                
        if st.sidebar.button("Dashboard", use_container_width=True):
            st.session_state.current_page = "dashboard"
            st.rerun()
            
        if st.sidebar.button("Health Services", use_container_width=True):
            st.session_state.current_page = "health_services"
            st.rerun()
            
        if st.sidebar.button("Contact Us", use_container_width=True):
            st.session_state.current_page = "contacts"
            st.rerun()
        
        # Logout button at the bottom of sidebar
        st.sidebar.markdown("---")
        if st.sidebar.button("Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user_info = None
            st.session_state.first_login = False
            st.session_state.survey_completed = False
            st.success("Logged out successfully!")
            time.sleep(1)
            st.rerun()
    
    # Main content area
    with col2:
        if st.session_state.current_page == "survey":
            st.title("🥗 Personalized Diet Recommendation Survey")
            st.write("Complete this survey to get a customized diet plan tailored to your needs and preferences.")
            
            # Create a form
            with st.form("diet_survey_form"):
                st.subheader("Personal Information")
                col1, col2 = st.columns(2)
                
                with col1:
                    name = st.text_input("Full Name")
                    age = st.number_input("Age", min_value=12, max_value=100, value=30)
                    gender = st.selectbox("Gender", ["Male", "Female", "Non-binary", "Prefer not to say"])
                    
                with col2:
                    height = st.number_input("Height (cm)", min_value=100, max_value=250, value=170)
                    weight = st.number_input("Weight (kg)", min_value=30, max_value=250, value=70)
                    email = st.text_input("Email Address", value=st.session_state.user_info['email'], disabled=True)
                    country = st.text_input("Country") # Added user location (country)
                
                # Calculate BMI immediately and show it
                if height and weight:
                    bmi = calculate_bmi(weight, height)
                    bmi_category = get_bmi_category(bmi)
                    
                    st.info(f"Your BMI: **{bmi}** - Category: **{bmi_category}**")
                
                st.subheader("Diet & Lifestyle")
                
                # Diet preferences
                diet_pref = st.radio("Diet Preference", 
                                    ["Vegetarian", "Non-vegetarian", "Vegan", "Pescatarian", "Flexitarian"])
                
                # Food allergies or restrictions
                food_allergies = st.multiselect("Food Allergies or Restrictions (if any)",
                                              ["Nuts", "Dairy", "Gluten", "Seafood", "Eggs", "Soy", 
                                                "Lactose Intolerant", "None"])
                
                # Activity level
                activity_level = st.select_slider("Activity Level", 
                                                options=["Sedentary (office job, little exercise)", 
                                                        "Lightly active (light exercise 1-3 days/week)", 
                                                        "Moderately active (moderate exercise 3-5 days/week)", 
                                                        "Very active (hard exercise 6-7 days/week)", 
                                                        "Extremely active (physical job & hard exercise)"])
                
                # Fitness goals
                fitness_goal = st.selectbox("Fitness Goal", 
                                          ["Weight loss", "Muscle gain", "Maintenance", 
                                          "Improve overall health", "Athletic performance"])
                
                # Sleep pattern
                sleep_hours = st.slider("Average Sleep Duration (hours per day)", 4, 12, 7)
                
                # Work-life balance
                work_life = st.select_slider("How would you describe your work-life balance?",
                                          options=["Very stressful", "Somewhat stressful", 
                                                  "Balanced", "Good balance", "Excellent balance"])
                
                # Lifestyle
                lifestyle = st.multiselect("Select aspects that describe your lifestyle",
                                         ["Long work hours", "Regular exercise", "Frequent travel", 
                                          "Work from home", "Student", "Parent/Caregiver", 
                                          "Social events with food/drink"])
                
                st.subheader("Meal Patterns & Budget")
                
                # Meals per day
                meals_per_day = st.slider("How many meals do you typically eat per day?", 1, 6, 3)
                
                # Snacking habits
                snacking = st.radio("Snacking habits", 
                                  ["Rarely snack", "Occasional snacks", "Regular snacks between meals", 
                                  "Frequent snacking throughout the day"])
                
                # Eating out frequency
                eating_out = st.select_slider("How often do you eat at restaurants or order takeout?",
                                            options=["Rarely (few times a month)", 
                                                    "Occasionally (1-2 times a week)", 
                                                    "Regularly (3-5 times a week)", 
                                                    "Very frequently (almost daily)"])
                
                # Budget constraints (CHANGED: Range from 1000 to 6000 INR)
                budget_constraint = st.slider("What's your monthly budget for food? (₹ per month)", 
                                            1000, 6000, 3000, step=500)
                
                # Cooking skills and time
                cooking_skill = st.select_slider("Cooking skills",
                                              options=["Beginner", "Can follow basic recipes", 
                                                      "Intermediate", "Advanced"])
                
                cooking_time = st.slider("How much time can you spend cooking per day (minutes)?", 
                                        15, 120, 30, step=15)
                
                # Additional information
                st.subheader("Additional Information")
                
                health_conditions = st.multiselect("Do you have any health conditions?",
                                                 ["Diabetes", "Hypertension", "Heart disease", 
                                                  "Digestive issues", "Food intolerances",
                                                  "None"])
                
                additional_info = st.text_area("Any additional information you'd like to share")
                
                # Submit button
                submitted = st.form_submit_button("Submit Survey")
                
                if submitted:
                    if not name or not country:
                        st.error("Please provide your name and country to continue.")
                    else:
                        # Prepare data for Firebase and CSV
                        survey_data = {
                            "name": name,
                            "email": email,
                            "age": age,
                            "gender": gender,
                            "height": height,
                            "weight": weight,
                            "country": country,
                            "bmi": bmi,
                            "bmi_category": bmi_category,
                            "diet_preference": diet_pref,
                            "food_allergies": ", ".join(food_allergies) if food_allergies else "None",
                            "activity_level": activity_level,
                            "fitness_goal": fitness_goal,
                            "sleep_hours": sleep_hours,
                            "work_life_balance": work_life,
                            "lifestyle": ", ".join(lifestyle) if lifestyle else "None",
                            "meals_per_day": meals_per_day,
                            "snacking_habits": snacking,
                            "eating_out_frequency": eating_out,
                            "budget_constraint": budget_constraint,
                            "cooking_skill": cooking_skill,
                            "cooking_time": cooking_time,
                            "health_conditions": ", ".join(health_conditions) if health_conditions else "None",
                            "additional_info": additional_info,
                            "submission_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        
                        # Save to Firebase
                        firebase_success, firebase_result = save_to_firebase(survey_data)
                        
                        # Save to CSV
                        csv_success, csv_result = save_to_csv(survey_data)
                        
                        if firebase_success or csv_success:
                            st.session_state.survey_completed = True
                            st.session_state.first_login = False
                            st.session_state.current_page = "dashboard"
                            st.success("Thank you for completing the survey! Your personalized diet recommendations will be sent to your email soon.")
                            if csv_success:
                                st.info(f"Your survey data has been saved to CSV file: {csv_result}")
                            st.balloons()
                            time.sleep(2)
                            st.rerun()
                        else:
                            error_message = []
                            if not firebase_success:
                                error_message.append(f"Firebase error: {firebase_result}")
                            if not csv_success:
                                error_message.append(f"CSV error: {csv_result}")
                            st.error("There was an error saving your data: " + " ".join(error_message))

        elif st.session_state.current_page == "recommendation":
            st.title("Food Recommendations 🍎")
            st.success("Generating recommendations...")
    
            # ✅ Load and execute ingredients.py content in the main area
            user_email = st.session_state.user_info.get('email')
            incri(user_email)

        elif st.session_state.current_page == "recipy":
            st.title("Food Recipies 🍎")
            st.success("Generating recipies...")
    
            # ✅ Load and execute ingredients.py content in the main area
            _it = []
            count = 0
            user_email = st.session_state.user_info.get('email')
            for i in mod.recommend(user_email):
                if(count==vari):
                    break
                _it.append(i[0])
                count+=1
            reci(user_email,_it)

        elif st.session_state.current_page == "dashboard":
            st.title("Your Diet Dashboard")
            
            # Get user's survey data
            user_data = get_user_survey_data(st.session_state.user_info['email'])
            
            if user_data:
                # Display user's profile summary
                st.header("Your Health Profile")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("BMI", f"{user_data.get('bmi', 'N/A')}", help="Body Mass Index based on your height and weight")
                with col2:
                    st.metric("Weight", f"{user_data.get('weight', 'N/A')} kg")
                with col3:
                    st.metric("Goal", user_data.get('fitness_goal', 'N/A'))
                
                # Diet plan section
                st.header("Your Personalized Diet Plan")
                st.info(f"Based on your {user_data.get('diet_preference', 'preferred')} diet preference and fitness goal of {user_data.get('fitness_goal', 'improving health')}, we've created a customized plan for you.")
                
                # Display sample meal plan
                with st.expander("View Your Recommended Meal Plan", expanded=True):
                    st.subheader("Daily Nutrition Targets")
                    
                    # Calculate approximate calories based on profile
                    weight = user_data.get('weight', 70)
                    height = user_data.get('height', 170)
                    age = user_data.get('age', 30)
                    gender = user_data.get('gender', 'Male')
                    activity = user_data.get('activity_level', 'Moderately active')
                    
                    # Very basic BMR calculation (Mifflin-St Jeor)
                    if gender == 'Male':
                        bmr = 10 * weight + 6.25 * height - 5 * age + 5
                    else:
                        bmr = 10 * weight + 6.25 * height - 5 * age - 161
                    
                    # Activity multiplier
                    activity_multipliers = {
                        "Sedentary (office job, little exercise)": 1.2,
                        "Lightly active (light exercise 1-3 days/week)": 1.375,
                        "Moderately active (moderate exercise 3-5 days/week)": 1.55,
                        "Very active (hard exercise 6-7 days/week)": 1.725,
                        "Extremely active (physical job & hard exercise)": 1.9
                    }
                    
                    multiplier = activity_multipliers.get(activity, 1.55)
                    maintenance_calories = int(bmr * multiplier)
                    
                    # Adjust based on goal
                    goal = user_data.get('fitness_goal', 'Maintenance')
                    if goal == 'Weight loss':
                        target_calories = int(maintenance_calories * 0.8)  # 20% deficit
                    elif goal == 'Muscle gain':
                        target_calories = int(maintenance_calories * 1.1)  # 10% surplus
                    else:
                        target_calories = maintenance_calories
                    
                    # Display macros
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Calories", f"{target_calories} kcal")
                    with col2:
                        protein_g = int(weight * 1.8)  # 1.8g protein per kg bodyweight
                        st.metric("Protein", f"{protein_g}g")
                    with col3:
                        fat_g = int(target_calories * 0.25 / 9)  # 25% from fat
                        st.metric("Fat", f"{fat_g}g")
                    
                    # Calculate remaining carbs
                    protein_cals = protein_g * 4
                    fat_cals = fat_g * 9
                    remaining_cals = target_calories - protein_cals - fat_cals
                    carb_g = int(remaining_cals / 4)
                    
                    st.metric("Carbohydrates", f"{carb_g}g")
                    
                    # Sample meal plan
                    st.subheader("Sample Daily Meal Plan")
                    
                    meal_plan = [
                        {"meal": "Breakfast", "time": "8:00 AM", "options": []},
                        {"meal": "Mid-Morning Snack", "time": "10:30 AM", "options": []},
                        {"meal": "Lunch", "time": "1:00 PM", "options": []},
                        {"meal": "Afternoon Snack", "time": "4:00 PM", "options": []},
                        {"meal": "Dinner", "time": "7:30 PM", "options": []}
                    ]
                    
                    # Adjust based on diet preference
                    diet_pref = user_data.get('diet_preference', 'Non-vegetarian')
                    
                    # Vegetarian options
                    if diet_pref == 'Vegetarian':
                        meal_plan[0]["options"] = ["Greek yogurt with berries and nuts", "Vegetable omelette with toast", "Oatmeal with fruits and flaxseeds"]
                        meal_plan[1]["options"] = ["Apple with almond butter", "Handful of mixed nuts", "Protein shake with banana"]
                        meal_plan[2]["options"] = ["Lentil soup with whole grain bread", "Chickpea salad with quinoa", "Bean and cheese burrito"]
                        meal_plan[3]["options"] = ["Cottage cheese with fruits", "Hummus with vegetable sticks", "Protein bar"]
                        meal_plan[4]["options"] = ["Stir-fried tofu with vegetables", "Vegetable curry with brown rice", "Mushroom pasta with salad"]
                    
                    # Vegan options
                    elif diet_pref == 'Vegan':
                        meal_plan[0]["options"] = ["Tofu scramble with vegetables", "Overnight chia pudding with fruits", "Avocado toast with nutritional yeast"]
                        meal_plan[1]["options"] = ["Trail mix with dried fruits", "Banana with peanut butter", "Coconut yogurt with berries"]
                        meal_plan[2]["options"] = ["Buddha bowl with tahini dressing", "Lentil and vegetable soup", "Quinoa salad with chickpeas"]
                        meal_plan[3]["options"] = ["Edamame beans", "Energy balls (dates, nuts, cocoa)", "Smoothie with plant protein"]
                        meal_plan[4]["options"] = ["Tempeh with steamed vegetables", "Bean and vegetable curry", "Vegan pasta with lentil bolognese"]
                    
                    # Non-vegetarian options (default)
                    else:
                        meal_plan[0]["options"] = ["Eggs with whole grain toast and avocado", "Protein smoothie with berries", "Greek yogurt with fruits and granola"]
                        meal_plan[1]["options"] = ["Protein bar", "Hard-boiled eggs", "Greek yogurt with honey"]
                        meal_plan[2]["options"] = ["Grilled chicken salad", "Tuna sandwich on whole grain bread", "Beef stir-fry with vegetables"]
                        meal_plan[3]["options"] = ["Turkey slices with nuts", "Protein shake", "Greek yogurt with berries"]
                        meal_plan[4]["options"] = ["Baked salmon with quinoa and vegetables", "Chicken curry with brown rice", "Lean beef with sweet potatoes"]
                    
                    # Display meal plan
                    for meal in meal_plan:
                        st.write(f"**{meal['meal']}** ({meal['time']})")
                        for option in meal["options"]:
                            st.write(f"- {option}")
                        st.write("")
                
                # Progress tracking
                st.header("Track Your Progress")
                st.write("Update your measurements regularly to track progress towards your goals.")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.number_input("Current Weight (kg)", min_value=30, max_value=250, value=int(user_data.get('weight', 70)))
                with col2:
                    st.date_input("Date", value=datetime.now())
                
                if st.button("Update Measurements"):
                    st.success("Measurements updated successfully!")
                
                # Quick recommendations
                st.header("Personalized Recommendations")
                st.write("Based on your profile and goals, here are some recommendations:")
                
                recommendations = [
                    f"Drink at least 8 glasses of water daily",
                    f"Include protein with every meal",
                    f"Aim for 7-9 hours of quality sleep each night",
                    f"Try to include 30 minutes of physical activity daily"
                ]
                
                # Add specific recommendations based on profile
                if user_data.get('bmi_category') == 'Overweight' or user_data.get('bmi_category') == 'Obese':
                    recommendations.append("Focus on portion control and mindful eating")
                
                if user_data.get('activity_level') in ["Sedentary (office job, little exercise)", "Lightly active (light exercise 1-3 days/week)"]:
                    recommendations.append("Consider adding more movement throughout your day")
                
                if user_data.get('cooking_time', 30) < 30:
                    recommendations.append("Try meal prepping on weekends to save time during busy weekdays")
                
                for rec in recommendations:
                    st.write(f"• {rec}")
            
            else:
                st.warning("We couldn't find your survey data. Please complete the diet survey to get personalized recommendations.")
                if st.button("Take Diet Survey Now"):
                    st.session_state.current_page = "survey"
                    st.rerun()
            
        elif st.session_state.current_page == "profile":
            st.title("Your Health Profile")
            st.write("Manage your personal information and health settings.")
            
            # Get user's existing data if available
            user_data = get_user_survey_data(st.session_state.user_info['email'])
            
            # Profile form
            with st.form("profile_form"):
                full_name = st.text_input("Full Name", value=user_data.get("name", "") if user_data else "")
                email = st.text_input("Email", value=st.session_state.user_info['email'], disabled=True)
                
                col1, col2 = st.columns(2)
                    
                with col1:
                    age = st.number_input("Age", min_value=12, max_value=100, value=user_data.get("age", 30) if user_data else 30)
                    height = st.number_input("Height (cm)", min_value=100, max_value=250, value=user_data.get("height", 170) if user_data else 170)
                    weight = st.number_input("Weight (kg)", min_value=30, max_value=250, value=user_data.get("weight", 70) if user_data else 70)
                
                with col2:
                    gender = st.selectbox("Gender", ["Male", "Female", "Non-binary", "Prefer not to say"], index=["Male", "Female", "Non-binary", "Prefer not to say"].index(user_data.get("gender", "Male")) if user_data and user_data.get("gender") in ["Male", "Female", "Non-binary", "Prefer not to say"] else 0)
                    country = st.text_input("Country", value=user_data.get("country", "") if user_data else "")
                    diet_pref = st.selectbox("Diet Preference", ["Vegetarian", "Non-vegetarian", "Vegan", "Pescatarian", "Flexitarian"], index=["Vegetarian", "Non-vegetarian", "Vegan", "Pescatarian", "Flexitarian"].index(user_data.get("diet_preference", "Non-vegetarian")) if user_data and user_data.get("diet_preference") in ["Vegetarian", "Non-vegetarian", "Vegan", "Pescatarian", "Flexitarian"] else 1)
                
                # Calculate BMI
                if height and weight:
                    bmi = calculate_bmi(weight, height)
                    bmi_category = get_bmi_category(bmi)
                    st.info(f"Your BMI: **{bmi}** - Category: **{bmi_category}**")

# Continuation of profile form
                st.subheader("Health Goals")
                fitness_goal = st.selectbox("Fitness Goal", 
                              ["Weight loss", "Muscle gain", "Maintenance", 
                              "Improve overall health", "Athletic performance"],
                              index=["Weight loss", "Muscle gain", "Maintenance", 
                              "Improve overall health", "Athletic performance"].index(user_data.get("fitness_goal", "Improve overall health")) if user_data and user_data.get("fitness_goal") in ["Weight loss", "Muscle gain", "Maintenance", "Improve overall health", "Athletic performance"] else 0)
                
                activity_level = st.select_slider("Activity Level", 
                                                options=["Sedentary (office job, little exercise)", 
                                                        "Lightly active (light exercise 1-3 days/week)", 
                                                        "Moderately active (moderate exercise 3-5 days/week)", 
                                                        "Very active (hard exercise 6-7 days/week)", 
                                                        "Extremely active (physical job & hard exercise)"],
                                                value=user_data.get("activity_level", "Moderately active (moderate exercise 3-5 days/week)") if user_data else "Moderately active (moderate exercise 3-5 days/week)")
                
                # Submit form
                submitted = st.form_submit_button("Update Profile")
                
                if submitted:
                    if not full_name or not country:
                        st.error("Please provide your name and country to continue.")
                    else:
                        # Prepare updated profile data
                        profile_data = {
                            "name": full_name,
                            "email": email,
                            "age": age,
                            "gender": gender,
                            "height": height,
                            "weight": weight,
                            "country": country,
                            "bmi": bmi,
                            "bmi_category": bmi_category,
                            "diet_preference": diet_pref,
                            "activity_level": activity_level,
                            "fitness_goal": fitness_goal,
                            # Keep other fields from original survey if available
                            "food_allergies": user_data.get("food_allergies", "None") if user_data else "None",
                            "sleep_hours": user_data.get("sleep_hours", 7) if user_data else 7,
                            "work_life_balance": user_data.get("work_life_balance", "Balanced") if user_data else "Balanced",
                            "lifestyle": user_data.get("lifestyle", "None") if user_data else "None",
                            "meals_per_day": user_data.get("meals_per_day", 3) if user_data else 3,
                            "snacking_habits": user_data.get("snacking_habits", "Occasional snacks") if user_data else "Occasional snacks",
                            "eating_out_frequency": user_data.get("eating_out_frequency", "Occasionally (1-2 times a week)") if user_data else "Occasionally (1-2 times a week)",
                            "budget_constraint": user_data.get("budget_constraint", 3000) if user_data else 3000,
                            "cooking_skill": user_data.get("cooking_skill", "Can follow basic recipes") if user_data else "Can follow basic recipes",
                            "cooking_time": user_data.get("cooking_time", 30) if user_data else 30,
                            "health_conditions": user_data.get("health_conditions", "None") if user_data else "None",
                            "additional_info": user_data.get("additional_info", "") if user_data else "",
                            "update_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        
                        # Save to Firebase
                        firebase_success, firebase_result = save_to_firebase(profile_data)
                        
                        if firebase_success:
                            st.success("Your profile has been updated successfully!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"There was an error updating your profile: {firebase_result}")
            
            # Add password change section
            st.header("Account Security")
            with st.expander("Change Password"):
                with st.form("password_form"):
                    current_password = st.text_input("Current Password", type="password")
                    new_password = st.text_input("New Password", type="password")
                    confirm_password = st.text_input("Confirm New Password", type="password")
                    
                    password_submit = st.form_submit_button("Change Password")
                    
                    if password_submit:
                        if not current_password or not new_password or not confirm_password:
                            st.error("Please fill in all password fields.")
                        elif new_password != confirm_password:
                            st.error("New passwords do not match.")
                        else:
                            try:
                                # Re-authenticate user
                                user = auth.sign_in_with_email_and_password(st.session_state.user_info['email'], current_password)
                                # Update password
                                auth.change_password(user['idToken'], new_password)
                                st.success("Password changed successfully!")
                            except Exception as e:
                                st.error(f"Failed to change password: {e}")
            
        elif st.session_state.current_page == "health_services":
            st.title("Health Services")
            st.write("Explore additional health services and resources to complement your diet plan.")
            
            # Create tabs for different services
            service_tab1, service_tab2, service_tab3 = st.tabs(["Nutrition Consultation", "Workout Plans", "Health Resources"])
            
            with service_tab1:
                st.header("Book a Nutrition Consultation")
                st.write("Get personalized advice from our registered dietitians.")
                
                col1, col2 = st.columns(2)
                with col1:
                    consultation_date = st.date_input("Preferred Date", min_value=datetime.now().date())
                    consultation_type = st.selectbox("Consultation Type", ["Initial Assessment (60 min)", "Follow-up (30 min)", "Diet Plan Review (45 min)"])
                
                with col2:
                    consultation_time = st.selectbox("Preferred Time", ["9:00 AM", "10:00 AM", "11:00 AM", "1:00 PM", "2:00 PM", "3:00 PM", "4:00 PM", "5:00 PM"])
                    consultation_mode = st.radio("Consultation Mode", ["Video Call", "Phone Call", "In-person"])
                
                if st.button("Book Consultation"):
                    st.success(f"Your {consultation_type} has been booked for {consultation_date.strftime('%A, %B %d, %Y')} at {consultation_time}. You will receive a confirmation email shortly.")
            
            with service_tab2:
                st.header("Personalized Workout Plans")
                st.write("Complement your diet with a customized workout plan.")
                
                # User's fitness data from survey if available
                user_data = get_user_survey_data(st.session_state.user_info['email'])
                
                workout_goal = st.selectbox("Workout Goal", 
                                           ["Weight Loss", "Muscle Building", "General Fitness", "Endurance", "Flexibility"],
                                           index=0 if not user_data else (0 if user_data.get("fitness_goal") == "Weight loss" else 
                                                                          1 if user_data.get("fitness_goal") == "Muscle gain" else 
                                                                          2))
                
                experience_level = st.select_slider("Experience Level", 
                                                  options=["Beginner", "Intermediate", "Advanced"])
                
                equipment = st.multiselect("Available Equipment", 
                                         ["None (Bodyweight only)", "Dumbbells", "Resistance Bands", "Full Gym Access", 
                                         "Cardio Equipment", "Yoga Mat", "Kettlebells", "Pull-up Bar"])
                
                days_per_week = st.slider("Days per week", 1, 7, 3)
                
                if st.button("Generate Workout Plan"):
                    st.success("Your personalized workout plan is being generated. It will be sent to your email within 24 hours.")
                    
                    # Preview workout plan based on selections
                    st.subheader("Preview: Sample Workout")
                    
                    # Generate simple workout preview based on selections
                    if workout_goal == "Weight Loss":
                        workout_type = "HIIT & Cardio Focus"
                        sample_exercises = ["Jumping Jacks", "Burpees", "Mountain Climbers", "High Knees", "Bodyweight Squats", "Push-ups", "Running/Walking Intervals"]
                    elif workout_goal == "Muscle Building":
                        workout_type = "Progressive Resistance Training"
                        sample_exercises = ["Squats", "Bench Press", "Deadlifts", "Shoulder Press", "Rows", "Pull-ups", "Lunges"]
                    else:
                        workout_type = "Balanced Fitness Routine"
                        sample_exercises = ["Squats", "Push-ups", "Planks", "Rows", "Lunges", "Shoulder Taps", "Jogging"]
                    
                    st.write(f"**Workout Type**: {workout_type}")
                    st.write(f"**Frequency**: {days_per_week} days per week")
                    st.write("**Sample Exercises**:")
                    for ex in sample_exercises:
                        st.write(f"- {ex}")
            
            with service_tab3:
                st.header("Health Resources")
                st.write("Access our curated collection of health and nutrition resources.")
                
                # Resource categories
                resource_categories = ["Nutrition Guides", "Recipe Collections", "Fitness Tips", "Mental Wellbeing", "Sleep Improvement"]
                
                # Display resources
                for category in resource_categories:
                    with st.expander(category):
                        if category == "Nutrition Guides":
                            st.write("• Beginner's Guide to Macro Counting")
                            st.write("• Understanding Food Labels")
                            st.write("• Healthy Eating on a Budget")
                            st.write("• Nutrient Timing for Optimal Performance")
                        elif category == "Recipe Collections":
                            st.write("• Quick & Healthy Breakfast Ideas")
                            st.write("• Protein-Packed Lunch Recipes")
                            st.write("• 30-Minute Dinner Recipes")
                            st.write("• Healthy Snack Alternatives")
                        elif category == "Fitness Tips":
                            st.write("• Home Workout Essentials")
                            st.write("• Proper Exercise Form Guide")
                            st.write("• Recovery Strategies for Athletes")
                            st.write("• Beginner's Strength Training")
                        elif category == "Mental Wellbeing":
                            st.write("• Mindful Eating Practices")
                            st.write("• Stress Reduction Techniques")
                            st.write("• Building Healthy Habits")
                            st.write("• Food and Mood Connection")
                        elif category == "Sleep Improvement":
                            st.write("• Sleep Hygiene Basics")
                            st.write("• Nutrition Tips for Better Sleep")
                            st.write("• Evening Relaxation Routines")
                            st.write("• Understanding Sleep Cycles")
                
                # Add newsletter signup
                st.subheader("Subscribe to Health Newsletter")
                with st.form("newsletter_form"):
                    st.write("Receive weekly nutrition tips, recipes, and health updates")
                    newsletter_email = st.text_input("Email Address", value=st.session_state.user_info['email'])
                    
                    interests = st.multiselect("Topics of Interest", 
                                             ["Nutrition Tips", "Recipes", "Fitness Advice", "Weight Management", 
                                             "Mental Wellbeing", "Sleep Improvement"])
                    
                    newsletter_submit = st.form_submit_button("Subscribe")
                    
                    if newsletter_submit:
                        st.success("You have successfully subscribed to our health newsletter!")
        
        elif st.session_state.current_page == "contacts":
            st.title("Contact Us")
            st.write("We're here to help you on your health journey. Reach out to our team with any questions or feedback.")
            
            # Contact options
            contact_tab1, contact_tab2 = st.tabs(["Send a Message", "Contact Information"])
            
            with contact_tab1:
                with st.form("contact_form"):
                    contact_name = st.text_input("Your Name", value=st.session_state.get("name", "") if st.session_state else "")
                    contact_email = st.text_input("Your Email", value=st.session_state.user_info['email'])
                    
                    contact_subject = st.selectbox("Subject", 
                                                ["General Inquiry", "Account Support", "Diet Plan Feedback", 
                                                "Technical Issues", "Billing Question", "Other"])
                    
                    contact_message = st.text_area("Your Message", height=150)
                    
                    contact_submit = st.form_submit_button("Send Message")
                    
                    if contact_submit:
                        if not contact_message:
                            st.error("Please enter a message before submitting.")
                        else:
                            # Save message to Firestore
                            try:
                                if db is not None:
                                    message_data = {
                                        "name": contact_name,
                                        "email": contact_email,
                                        "subject": contact_subject,
                                        "message": contact_message,
                                        "timestamp": datetime.now(),
                                        "status": "Unread"
                                    }
                                    db.collection('contact_messages').add(message_data)
                                    st.success("Your message has been sent successfully! Our team will respond within 24-48 hours.")
                                else:
                                    st.warning("Message couldn't be saved to our database, but we've recorded your request.")
                                    st.success("Your message has been sent!")
                            except Exception as e:
                                st.error(f"Error sending message: {e}")
                                st.info("Please try again later or use the email address below.")

            with contact_tab2:
                st.subheader("Our Contact Information")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Customer Support**")
                    st.write("Email: support@diet-webapp.com")
                    st.write("Phone: +91 123 456 7890")
                    st.write("Hours: Monday-Friday, 9 AM - 6 PM IST")
                
                with col2:
                    st.write("**Nutritionist Consultations**")
                    st.write("Email: nutrition@diet-webapp.com")
                    st.write("Phone: +91 123 456 7891")
                    st.write("Hours: Monday-Saturday, 10 AM - 7 PM IST")
                
                st.subheader("Frequently Asked Questions")
                
                # FAQ expandable sections
                with st.expander("How do I update my diet preferences?"):
                    st.write("You can update your diet preferences by going to your Profile page and updating your information in the profile form.")
                
                with st.expander("Can I download my meal plan?"):
                    st.write("Yes, we're working on adding a feature to download your personalized meal plan as a PDF. This feature will be available in our next update.")
                
                with st.expander("How often should I update my weight in the app?"):
                    st.write("For the best results, we recommend updating your weight once a week, preferably on the same day and time each week for consistency.")
                
                with st.expander("How do I cancel my subscription?"):
                    st.write("To cancel your subscription, please contact our customer support team via email at support@diet-webapp.com or through the contact form on this page.")
                
                with st.expander("Is my personal information secure?"):
                    st.write("Yes, we take data security very seriously. All your personal information is encrypted and stored securely. We never share your data with third parties without your explicit consent.")

# Add a footer
st.markdown("---")
st.markdown("<div style='text-align: center;'>© 2025 Diet Recommendation App. All rights reserved.</div>", unsafe_allow_html=True)