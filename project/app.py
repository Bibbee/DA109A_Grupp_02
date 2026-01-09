# Imports (tools we use):
# Flask = the web framework. It helps us create web pages and routes
# render_template = show HTML files
# request = read data from forms and URLs
# redirect, url_for = move the user to another page
# session = remember which user is logged in
# jsonify = send back small JSON messages (for our toast popup)
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
# requests = used to call the TMDB API (ask for movie data)
import requests
# load_dotenv = reads values from .env (our API_KEY)
from dotenv import load_dotenv
# os = talk to the operating system, checks if a file exists
import os
load_dotenv()
# json = read and write JSON files (basically our database)
import json
# Counter = count occurrences of items (for finding most common genre)
from collections import Counter
# Flask setup 
app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")
API_KEY = os.getenv("API_KEY") # TMDB API key
BASE_URL = "https://api.themoviedb.org/3" # base URL for TMDB requests
DB_FILE = "users.json" # JSON file where we store users and favorites (for now)
OMDB_API_KEY = os.getenv("OMDB_API_KEY") # OMDB API key
OMDB_BASE_URL = "https://www.omdbapi.com/" # base URL for OMDB requests
  
def format_runtime(minutes):
    """ 
    This function makes sure that minutes and hours are formatted correctly,
    while also displaying remaining minutes. 'Unknown' will be shown if no data
    exists. 

    returns also makes sure that minutes and hours are displayed correctly.
    """
    if not minutes:
        return "Unknown"

    minutes = int(minutes)
    hours = minutes // 60
    mins = minutes % 60

    if hours == 0:
        return f"{mins} minute{'s' if mins != 1 else ''}"
    if mins == 0:
        return f"{hours} hour{'s' if hours != 1 else ''}"
    return f"{hours} hour{'s' if hours != 1 else ''} {mins} minute{'s' if mins != 1 else ''}"

app.jinja_env.filters['format_runtime'] = format_runtime

def build_poster_url(poster_path, size="w342"):
    
    # This function builds a readable image URL from TMBDb's image server. 
    if not poster_path:
        return None
    return f"https://image.tmdb.org/t/p/{size}{poster_path}" 

def get_director(movie_id):
    """
    This uses the movie id to get access to TMDb's credits endpoint to
    find the specific director and returns the name of the director.
    """

    url = f"{BASE_URL}/movie/{movie_id}/credits"
    res = requests.get(url, params={"api_key": API_KEY})

    if res.status_code != 200:
        return None

    for person in res.json().get("crew", []):
        if person.get("job") == "Director":
            return person.get("name")

    return None

def get_movie_details(movie_id):
    """
    This function builds an URL to the exact movie in question with all its details and
    returns genres and runtime.
    """
    url = f"{BASE_URL}/movie/{movie_id}"
    res = requests.get(url, params={"api_key": API_KEY})

    if res.status_code != 200:
        return {"runtime": None, "genres": []}

    data = res.json()
    genres = [genre.get("name") for genre in data.get("genres", [])]
    return {"runtime": data.get("runtime"), "genres": genres}

def build_movie_dict(movie_data, director=None, include_details=False):
    """
    Build a movie dictionary. If include_details=True, fetches runtime/genres/director.
    For search results, this should be False to avoid unnecessary API calls.
    """
    movie_id = movie_data.get("id")
    
    movie_dict = {
        "id": movie_id,
        "title": movie_data.get("title"),
        "release_date": movie_data.get("release_date"),
        "rating": movie_data.get("vote_average"),
        "poster_url": build_poster_url(movie_data.get("poster_path")),
    }
    
    # Only fetch expensive details if explicitly requested
    if include_details:
        details = get_movie_details(movie_id)
        movie_dict["director"] = director or get_director(movie_id)
        movie_dict["runtime"] = details.get("runtime")
        movie_dict["genres"] = details.get("genres")
    else:
        # Use data from search results if available
        movie_dict["director"] = director
        movie_dict["runtime"] = movie_data.get("runtime")
        movie_dict["genres"] = movie_data.get("genres", [])
    
    return movie_dict

def search_movies(query, limit=15):
    """Searches TMDb for movies matching a title query. Returns minimal data for speed."""
    if not query:
        return []

    url = f"{BASE_URL}/search/movie"

    try:
        response = requests.get(url, params = {"api_key": API_KEY, "query": query}, timeout=10)
    except requests.RequestException as err:
        print(f"TMDb-fel (search/movie): {err}")
        return []

    if response.status_code != 200:
        print(f"TMDb-fel (search/movie): {response.status_code}")
        return []
    
    results = response.json().get("results", [])[:limit]
    # Don't fetch details here - too slow. Return minimal data for card display
    return [build_movie_dict(movie, include_details=False) for movie in results]

def search_movies_by_director(director_name, limit=15):
    """Returns movies directed by a given person (MVP: first match)."""
    if not director_name:
        return []

    # First, search for the director
    url = f"{BASE_URL}/search/person"
    try:
        response = requests.get(url, params={"api_key": API_KEY, "query": director_name}, timeout=10)
    except requests.RequestException as err:
        print(f"TMDb-fel (seach/person): {err}")
        return []
    
    if response.status_code != 200:
        print(f"TMDb-fel (search/person): {response.status_code}")
        return []
    
    persons = response.json().get("results", [])
    if not persons:
        return []
    
    director = persons[0]  # MVP: ta första matchen
    director_id = director.get("id")
    director_display_name = director.get("name") or director_name

    if not director_id:
        return []
    
    # Get all movies directed by this person
    url = f"{BASE_URL}/person/{director_id}/movie_credits"

    try:
        response = requests.get(url, params={"api_key": API_KEY}, timeout=10)
    except requests.RequestException as err:
        print(f"TMDb-fel (movie_credits): {err}")
        return []
    
    if response.status_code != 200:
        print(f"TMDb-fel (movie_credits): {response.status_code}")
        return []
    
    crew = response.json().get("crew", [])
    directed = [movie for movie in crew if movie.get("job") == "Director"][:limit]
    # Don't fetch details here - too slow. Return minimal data for card display
    return [build_movie_dict(movie, director=director_display_name, include_details=False) for movie in directed]

# ---------- Helper functions for JSON "DB" ----------
def get_imdb_id_from_tmdb(tmdb_id):
    """Returns IMDb ID for a TMDb movie ID, or None"""
    if not tmdb_id:
        return None
    
    url = f"{BASE_URL}/movie/{tmdb_id}/external_ids"

    try:
        response = requests.get(url, params={"api_key": API_KEY}, timeout=10)
    except requests.RequestException as err:
        print(f"TMDb error (external_ids): {err}")
        return None
    
    if response.status_code != 200:
        print(f"TMDb error (external_ids): {response.status_code}")
        return None
    
    return response.json().get("imdb_id")

def get_imdb_rating_from_omdb(imdb_id):
    """Returns IMDb rating as float (0–10), or None."""
    if not imdb_id or not OMDB_API_KEY:
        return None

    try:
        response = requests.get(
            OMDB_BASE_URL,
            params={"apikey": OMDB_API_KEY, "i": imdb_id},  # <-- apikey, inte api_key
            timeout=10,
        )
    except requests.RequestException as err:
        print(f"OMDb error: {err}")
        return None

    if response.status_code != 200:
        print(f"OMDb error: {response.status_code} | {response.text[:200]}")
        return None

    data = response.json()
    if data.get("Response") != "True":
        print(f"OMDb error: {data.get('Error')}")
        return None

    rating_str = data.get("imdbRating")
    if not rating_str or rating_str == "N/A":
        return None

    try:
        return float(rating_str)
    except ValueError:
        return None

def get_or_cache_imdb_rating(favorite):
    """
    Get IMDb rating for a favorite movie, using cache if available.
    Returns tuple (rating, was_updated) where rating is float or None.
    """
    cached_rating = favorite.get("imdbRating")
    if isinstance(cached_rating, (int, float)):
        return float(cached_rating), False
    
    tmdb_id = favorite.get("id")
    if not tmdb_id:
        return None, False
    
    imdb_id = favorite.get("imdbId")
    if not imdb_id:
        imdb_id = get_imdb_id_from_tmdb(tmdb_id)
        if imdb_id:
            favorite["imdbId"] = imdb_id
        else:
            return None, False
    
    rating = get_imdb_rating_from_omdb(imdb_id)
    if rating is None:
        return None, False
    
    favorite["imdbRating"] = rating
    return rating, True

def load_users():
    """Loads all users from the JSON file. Always returns a list."""
    if not os.path.exists(DB_FILE):
        return []
    
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []
    
    return data if isinstance(data, list) else []

def save_users(users):
    """Saves the full users list to the JSON file."""
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)


def find_user(username):
    """Returns the user dict for a username, or None if not found."""
    if not username:
        return None
    
    for user in load_users():
        if user.get("username") == username:
            return user
        
    return None

def update_user(user):
    """
    Replace a user in the list and save everything.
    We look for a user with the same username,
    swap it with the new one, and then call save_users().
    """
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
    search_type = request.args.get("type", "film").strip()
    
    # Map search types to search functions
    search_functions = {
        "director": search_movies_by_director,
        "film": search_movies
    }
    
    search_func = search_functions.get(search_type, search_movies)
    movies_results = search_func(query)
    
    username = session["username"]
    user = find_user(username)
    favorites = user.get("favorites", []) if user else []

    return render_template(
        "movies.html",
        movies=movies_results,
        query=query,
        username=username,
        favorites=favorites,
    )

@app.route("/add_favorite", methods=["POST"])
@login_required
def add_favorite():
    username = session["username"]
    user = find_user(username)
    
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 400

    movie_id = request.form.get("id")
    user.setdefault("favorites", [])
    
    # Only add if not already in favorites
    if not any(str(f["id"]) == str(movie_id) for f in user["favorites"]):
        movie_fields = ["id", "title", "poster_url", "release_date", "rating", "director", "runtime", "genres"]
        user["favorites"].append({field: request.form.get(field) for field in movie_fields})
        update_user(user)

    # Return response based on request type
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    return jsonify({"status": "ok"}) if is_ajax else redirect(url_for("movies"))

@app.route("/my-list", methods=["GET"])
@login_required
def my_list():
    username = session["username"]
    user = find_user(username)
    favorites = user.get("favorites", []) if user else []
    
    sort_by = request.args.get("sort", "added")
    reverse_sort = request.args.get("reverse", "false").lower() == "true"
    
    # Define sort key functions
    sort_keys = {
        "rating": lambda x: float(x.get("rating", 0)),
        "release": lambda x: x.get("release_date", "")
    }
    
    if sort_by in sort_keys:
        favorites = sorted(favorites, key=sort_keys[sort_by], reverse=not reverse_sort)
    elif reverse_sort:
        favorites = list(reversed(favorites))

    return render_template(
        "my_list.html",
        username=username,
        favorites=favorites,
        sort_by=sort_by,
        reverse_sort=reverse_sort,
    )

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

    # Remove the movie from favorites
    user["favorites"] = [f for f in user.get("favorites", []) if str(f.get("id")) != str(movie_id)]
    update_user(user)

    # Return appropriate response based on request type
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    return jsonify({"status": "ok"}) if is_ajax else redirect(url_for("my_list"))

@app.route("/wrapped")
@login_required
def wrapped():
    username = session["username"]
    user = find_user(username)
    favorites = user.get("favorites", []) if user else []

    if not favorites:
        return render_template("wrapped.html", hours=0, minutes=0, total_movies=0)

    # Get all ratings (using cache where available)
    ratings_and_updates = [get_or_cache_imdb_rating(fav) for fav in favorites]
    imdb_ratings = [r for r, _ in ratings_and_updates if r is not None]
    dirty = any(updated for _, updated in ratings_and_updates)

    # Save if we cached new data
    if user and dirty:
        update_user(user)

    # Calculate statistics
    total_minutes = sum(int(fav.get("runtime", 0)) for fav in favorites if fav.get("runtime"))
    
    # Flatten and deduplicate genres
    all_genres = []
    for fav in favorites:
        genres = fav.get("genres")
        if genres:
            if isinstance(genres, str):
                all_genres.extend([g.strip() for g in genres.split(",")])
            else:
                all_genres.extend(genres)
    
    most_common_genre = Counter(all_genres).most_common(1)[0][0] if all_genres else None
    
    hours = total_minutes // 60
    minutes = total_minutes % 60
    average_rating = round(sum(imdb_ratings) / len(imdb_ratings), 2) if imdb_ratings else None
    
    # Determine taste label
    taste_label = None
    if average_rating is not None:
        if average_rating >= 8.0:
            taste_label = "Elite taste, you know cinema!"
        elif average_rating >= 6.0:
            taste_label = "You have good taste!"
        else:
            taste_label = "This is questionable, you need to watch better movies!"

    return render_template(
        "wrapped.html",
        hours=hours,
        minutes=minutes,
        most_common_genre=most_common_genre,
        total_movies=len(favorites),
        average_rating=average_rating,
        rated_movies=len(imdb_ratings),
        taste_label=taste_label
    )

if __name__ == "__main__":
    app.run(debug=True)
