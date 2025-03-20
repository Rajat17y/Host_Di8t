import pandas as pd
import numpy as np

file_path = "nutrients.csv"
dataset = pd.read_csv(file_path)
users = pd.read_csv('data/all_survey_responses.csv')

# Replace alphabets in specific columns (by index)
columns_to_replace = [3, 4, 5, 6, 7, 8]
dataset.iloc[:, columns_to_replace] = dataset.iloc[:, columns_to_replace].replace(r'[A-Za-z]', 0, regex=True)

# Extract values
X = dataset.iloc[:, 3:].values
y = dataset.iloc[:,0].values

#Users data
coef = users.iloc[:,[1,7,9,12]]

mapping = {
    'dairy products': 'A',
    'fats, oils, shortenings': 'B',
    'meat, poultry': 'C',
    'fish, seafood': 'D',
    'vegetables a-e': 'E',
    'vegetables f-p': 'F',
    'vegetables r-z': 'G',
    'fruits a-f': 'H',
    'fruits g-p': 'I',
    'fruits r-z': 'J',
    'breads, cereals, fastfood,grains': 'K',
    'soups': 'L',
    'desserts, sweets': 'M',
    'jams, jellies': 'N',
    'seeds and nuts': 'O',
    'drinks,alcohol, beverages': 'P'
}

# Clean and apply the mapping
X[:, -1] = np.vectorize(lambda x: mapping.get(x.strip().lower(), 'Z'))(X[:, -1])

'''
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
ct = ColumnTransformer(transformers=[('encoder',OneHotEncoder(),[-1])],remainder='passthrough')
X = np.array(ct.fit_transform(X))
'''

# Convert all values except the last column to integers
X[:, :-1] = np.array([[int(float(value.replace(',', ''))) if isinstance(value, str) and value.replace(',', '').replace('.', '').isdigit()
               else int(float(value)) if isinstance(value, str) and value.replace('.', '').isdigit()
               else int(value) if isinstance(value, (float, int)) and not np.isnan(value)
               else 0 
               for value in row[:-1]] for row in X])

# Keep last column unchanged
last_column = X[:, -1]

# Combine back into a single array (ensuring last column stays unchanged)
X = np.column_stack((X[:, :-1], last_column))

# Replace NaNs with 0 (if any)
X[:, :-1] = np.nan_to_num(X[:, :-1]).astype(int)

from sklearn.preprocessing import StandardScaler
sc = StandardScaler()
X[:, :-1] = sc.fit_transform(X[:, :-1])

def recommend(email,coef=coef):
    #Processing According to user
    numberRows = coef.shape[0]
    matched = []
    coef = np.array(coef)
    for i in range(0,numberRows):
        if(coef[i,0]==email):
            matched.append(coef[i,1:])

    #print(matched[0])
    a = matched[0][0]
    b = str(matched[0][1])
    c = str(matched[0][2])
    _c = 1
    if c=='Muscle gain':
        _c = 80
    # Example coefficients for each numeric column (6 columns)
    coefficients = [a,_c,1,1,1,1]  # Adjust these based on importance

    # List to store row index and calculated rating
    ratings = []

    # Loop through rows to calculate ratings
    for i, row in enumerate(X):
        # Apply coefficients to each column value (excluding last column)
        rating = sum(int(row[j]) * coefficients[j] for j in range(len(coefficients)))
    
        # Append row index and rating
        ratings.append((i, rating))

    # Sort ratings based on the rating value in descending order
    sorted_ratings = sorted(ratings, key=lambda x: x[1], reverse=True)
    final_list = []
    # Display sorted ratings

    for idx, rating in sorted_ratings:
        final_list.append([y[idx],(X[idx])])
        #print(y[idx],end=": ")
        #print(f"Row {idx} -> Rating: {rating:.2f}")
    #print(len(final_list))
    #Filter
    #print(final_list[0][1][6])
    #print(X.shape[0])
    #print(final_list)
    if b == 'Vegetarian':
        for i in range(len(final_list) - 1, -1, -1):  # Loop from last to first
            if final_list[i][1][6] == 'C':  # Check 7th element in the array
                final_list.pop(i)
    #print(len(final_list))
    return final_list
