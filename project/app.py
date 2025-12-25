from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import requests
from dotenv import load_dotenv
import os
import json

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")

load_dotenv()
API_KEY = os.getenv("API_KEY") # TMDB API key
BASE_URL = "https://api.themoviedb.org/3" # base URL for TMDB requests
DB_FILE = "users.json" # JSON file where we store users and favorites (for now)


def format_runtime(minutes):
    if not minutes:
        return "Unknown"
    minutes = int(minutes)
    if minutes >= 60:
        hours = minutes // 60
        remaining_minutes = minutes % 60
        if remaining_minutes == 0:
            return f"{hours} hour{'s' if hours > 1 else ''}"
        else:
            return f"{hours} hour{'s' if hours > 1 else ''} {remaining_minutes} minute{'s' if remaining_minutes > 1 else ''}"
    else:
        return f"{minutes} minute{'s' if minutes > 1 else ''}"

app.jinja_env.filters['format_runtime'] = format_runtime

def build_poster_url(poster_path, size="w342"):
    if not poster_path:
        return None
    return f"https://image.tmdb.org/t/p/{size}{poster_path}" 

def get_director(movie_id):
    url = f"{BASE_URL}/movie/{movie_id}/credits"
    params = {"api_key": API_KEY}
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        crew = data.get("crew", [])
        for person in crew:
            if person.get("job") == "Director":
                return person.get("name")
    return None

def get_movie_details(movie_id):
    url = f"{BASE_URL}/movie/{movie_id}"
    params = {"api_key": API_KEY}
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        genres = [g.get("name") for g in data.get("genres", [])]
        return {
            "runtime": data.get("runtime"),
            "genres": genres
        }
    return {"runtime": None, "genres": []}

def build_movie_dict(movie_data, director=None):
    """Helper function to build a standardized movie dictionary from TMDB data."""
    movie_id = movie_data.get("id")
    details = get_movie_details(movie_id)
    
    return {
        "id": movie_id,
        "title": movie_data.get("title"),
        "release_date": movie_data.get("release_date"),
        "rating": movie_data.get("vote_average"),
        "poster_url": build_poster_url(movie_data.get("poster_path")),
        "director": director or get_director(movie_id),
        "runtime": details.get("runtime"),
        "genres": details.get("genres"),
    }

def search_movies(query):
    """Ask TMDB for movies that match the search text."""
    movies = []
    if not query:
        return movies

    url = f"{BASE_URL}/search/movie"
    params = {"api_key": API_KEY, "query": query}
    response = requests.get(url, params=params)

    if response.status_code == 200:
        results = response.json().get("results", [])[:16]
        for m in results:
            movies.append(build_movie_dict(m))
    else:
        print("TMDB error:", response.status_code, response.text)

    return movies

def search_movies_by_director(director_name):
    movies = []
    if not director_name:
        return movies

    # First, search for the director
    url = f"{BASE_URL}/search/person"
    params = {"api_key": API_KEY, "query": director_name}
    response = requests.get(url, params=params)
    
    if response.status_code != 200:
        print("TMDB error:", response.status_code, response.text)
        return movies
    
    results = response.json().get("results", [])
    if not results:
        return movies
    
    director_id = results[0].get("id")
    actual_director_name = results[0].get("name")
    
    # Get all movies directed by this person
    url = f"{BASE_URL}/person/{director_id}/movie_credits"
    params = {"api_key": API_KEY}
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        crew = response.json().get("crew", [])
        directed_movies = [m for m in crew if m.get("job") == "Director"][:16]
        
        for m in directed_movies:
            movies.append(build_movie_dict(m, director=actual_director_name))
    
    return movies
# ---------- Helper functions for JSON "DB" ----------

def load_users():
    if not os.path.exists(DB_FILE):
        return []
    with open(DB_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_users(users):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)

def find_user(username):
    users = load_users()
    for u in users:
        if u["username"] == username:
            return u
    return None

def update_user(user):
    users = load_users()
    for i, u in enumerate(users):
        if u["username"] == user["username"]:
            users[i] = user
            break
    save_users(users)

# ---------- Auth routes ----------

@app.route("/", methods=["GET", "POST"])
def login():
    # If already logged in, go directly to movies
    if "username" in session:
        return redirect(url_for("movies"))

    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        user = find_user(username)
        if user and user["password"] == password:
            session["username"] = username
            return redirect(url_for("movies"))
        else:
            error = "Invalid username or password."

    return render_template("index.html", error=error)

@app.route("/register", methods=["GET", "POST"])
def register():
    if "username" in session:
        return redirect(url_for("movies"))

    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        confirm = request.form.get("confirm", "").strip()

        if not username or not password:
            error = "Username and password are required."
        elif password != confirm:
            error = "Passwords do not match."
        elif find_user(username):
            error = "Username already taken."
        else:
            users = load_users()
            users.append({
                "username": username,
                "password": password,
                "favorites": []
            })
            save_users(users)
            # auto-login after register
            session["username"] = username
            return redirect(url_for("movies"))

    return render_template("register.html", error=error)

@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))

# ---------- Protected movies route ----------

def login_required(func):
    from functools import wraps

    @wraps(func)
    def wrapper(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))
        return func(*args, **kwargs)

    return wrapper

@app.route("/movies", methods=["GET", "POST"])
@login_required
def movies():
    query = request.args.get("q", "").strip()
    search_type = request.args.get("type", "film").strip()  # Default to "film"
    
    # Choose search function based on type
    if search_type == "director":
        movies = search_movies_by_director(query)
    else:
        movies = search_movies(query)
    
    username = session["username"]
    user = find_user(username)
    favorites = user.get("favorites", []) if user else []

    return render_template(
        "movies.html",
        movies=movies,
        query=query,
        username=username,
        favorites=favorites,
    )

# ---------- Add favorite ----------
@app.route("/add_favorite", methods=["POST"])
@login_required
def add_favorite():
    movie_id = request.form.get("id")
    title = request.form.get("title")
    poster_url = request.form.get("poster_url")
    release_date = request.form.get("release_date")
    rating = request.form.get("rating")
    director = request.form.get("director")
    runtime = request.form.get("runtime")
    genres = request.form.get("genres")

    username = session["username"]
    user = find_user(username)
    if not user:
        # om nåt är helt fel, skicka 400 (bad request, ogiltig användare)
        return jsonify({"status": "error", "message": "User not found"}), 400

    if "favorites" not in user:
        user["favorites"] = []

    if not any(str(f["id"]) == str(movie_id) for f in user["favorites"]):
        user["favorites"].append({
            "id": movie_id,
            "title": title,
            "poster_url": poster_url,
            "release_date": release_date,
            "rating": rating,
            "director": director,
            "runtime": runtime,
            "genres": genres,
        })
        update_user(user)

    # Om det är en AJAX-request → skicka JSON
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"status": "ok"})

    # fallback om man skulle POST:a utan JS
    return redirect(url_for("movies"))

#--- NEW ROUTE FOR: MY LIST---
@app.route("/my-list", methods=["GET"])
@login_required
def my_list():
    username = session["username"]

    user = find_user(username)
    favorites = user.get("favorites", []) if user else []
    
    # Get sort parameter from query string, default to "added"
    sort_by = request.args.get("sort", "added")
    reverse_sort = request.args.get("reverse", "false").lower() == "true"
    
    if sort_by == "rating":
        favorites = sorted(favorites, key=lambda x: float(x.get("rating", 0)), reverse=not reverse_sort)
    elif sort_by == "release":
        favorites = sorted(favorites, key=lambda x: x.get("release_date", ""), reverse=not reverse_sort)
    elif reverse_sort:
        favorites = list(reversed(favorites))

    return render_template(
        "my_list.html",
        username=username,
        favorites=favorites,
        sort_by=sort_by,
        reverse_sort=reverse_sort,
    )

#--- REMOVING MOVIES ROUTE---
@app.route("/remove_favorite", methods=["POST"])
@login_required
def remove_favorite():
    movie_id = request.form.get("id")

    username = session["username"]
    user = find_user(username)

    if not user:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"status": "error", "message": "User not found"}), 400
        return redirect(url_for("my_list"))

    favorites = user.get("favorites", []) # All the current favorite movies
    new_favorites = [f for f in favorites if str(f.get("id")) != str(movie_id)]
    user["favorites"] = new_favorites
    update_user(user) # Save the changes to JSON

    # Javascript call: ensures the cards are succesfully removed by with the animation thing; no need to reload the page now. 
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"status": "ok"})
    
    return redirect(url_for("my_list"))

@app.route("/wrapped")
@login_required
def wrapped():
    username = session["username"]
    user = find_user(username)
    favorites = user.get("favorites", []) if user else []

    total_minutes = 0
    all_genres = []

    # Loop through each favorite movie to get details
    for fav in favorites:
        runtime = fav.get("runtime")
        if runtime:
            total_minutes += int(runtime)
        
        genres = fav.get("genres")
        if genres:
            if isinstance(genres, str):
                all_genres.extend([g.strip() for g in genres.split(",")])
            else:
                all_genres.extend(genres)

    hours = total_minutes // 60
    minutes = total_minutes % 60

    most_common_genre = None
    if all_genres:
        from collections import Counter
        genre_counts = Counter(all_genres)
        most_common_genre = genre_counts.most_common(1)[0][0]

    return render_template(
        "wrapped.html",
        hours=hours,
        minutes=minutes,
        most_common_genre=most_common_genre,
        total_movies=len(favorites)
    )

if __name__ == "__main__":
    app.run(debug=True)
