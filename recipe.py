import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
import requests

def reci(ingredients):
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
            ingredients = ["Chicken", "Potato", "Milk", "Oats", "Fish", "Rice", "Pasta"]
            
            selected_ingredient = st.selectbox("Select an ingredient", ingredients)
            
            if st.button("Find Recipes") and selected_ingredient:
                with st.spinner(f"Searching for {selected_ingredient} recipes..."):
                    results = search_recipes(selected_ingredient)
                    
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