from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import requests

app = Flask(__name__)
app.secret_key = "supersecretkey"  # required for flash messages

# ---------------- DATABASE (SQLAlchemy) ---------------- #
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///recipes.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Favorite(db.Model):
    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String, nullable=False)
    image = db.Column(db.String, nullable=False)

with app.app_context():
    db.create_all()

# ---------------- ROUTES ---------------- #

# Home Page
@app.route('/')
def index():
    return render_template('index.html')

# Search Recipes
@app.route('/search')
def search():
    query = request.args.get('query')
    if not query:
        return redirect(url_for('index'))
    meals = []
    try:
        url = f"https://www.themealdb.com/api/json/v1/1/search.php?s={query}"
        response = requests.get(url)
        data = response.json()
        meals = data.get('meals') or []
    except Exception as e:
        flash("Error fetching recipes. Try again later.", "danger")
        meals = []
    return render_template('index.html', meals=meals, query=query)

# Recipe Details
@app.route('/recipe/<id>')
def recipe(id):
    meal = None
    ingredients = []
    youtube_link = None
    image = None
    try:
        url = f"https://www.themealdb.com/api/json/v1/1/lookup.php?i={id}"
        response = requests.get(url)
        data = response.json()
        meal = data.get('meals', [None])[0]
        if meal:
            # Ingredients & Measures
            for i in range(1, 21):
                ingredient = meal.get(f"strIngredient{i}")
                measure = meal.get(f"strMeasure{i}")
                if ingredient and ingredient.strip():
                    measure_text = measure.strip() if measure else "To taste"
                    ingredients.append(f"{ingredient} - {measure_text}")
            # Image
            image = meal.get('strMealThumb')
            # YouTube
            youtube_link = meal.get('strYoutube')
    except Exception as e:
        flash("Error fetching recipe details.", "danger")
    return render_template(
        'recipe.html',
        meal=meal,
        ingredients=ingredients,
        youtube_link=youtube_link,
        image=image
    )

# Add to Favorites
@app.route('/add_favorite/<id>')
def add_favorite(id):
    try:
        url = f"https://www.themealdb.com/api/json/v1/1/lookup.php?i={id}"
        response = requests.get(url)
        meal = response.json().get('meals', [None])[0]

        if meal:
            existing = Favorite.query.get(str(meal['idMeal']))
            if existing:
                flash("Already in favorites ❤️", "info")
            else:
                new_fav = Favorite(
                    id=str(meal['idMeal']),
                    name=meal['strMeal'],
                    image=meal['strMealThumb']
                )
                db.session.add(new_fav)
                db.session.commit()
                flash("Added to favorites ❤️", "success")
    except Exception as e:
        flash("Error adding to favorites.", "danger")
    return redirect(url_for('favorites'))

# Remove Favorite
@app.route('/remove_favorite/<id>')
def remove_favorite(id):
    try:
        fav = Favorite.query.get(id)
        if fav:
            db.session.delete(fav)
            db.session.commit()
            flash("Removed from favorites ❌", "warning")
    except Exception as e:
        flash("Error removing favorite.", "danger")

    return redirect(url_for('favorites'))

# Favorites Page
@app.route('/favorites')
def favorites():
    meals = Favorite.query.all()
    return render_template('favorites.html', meals=meals)

# ---------------- RUN ---------------- #
if __name__ == '__main__':
    app.run() 