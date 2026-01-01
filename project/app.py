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

# json = read and write JSON files (basically our database)
import json

# Flask setup 
app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")

load_dotenv()
API_KEY = os.getenv("API_KEY") # TMDB API key
BASE_URL = "https://api.themoviedb.org/3" # base URL for TMDB requests
DB_FILE = "users.json" # JSON file where we store users and favorites (for now)

    
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



def build_movie_dict(movie_data, director=None):
    """
    This function makes sure that a clean movie dictionary is made with only
    the necessary data to display in the movie cards in our HTML .
    """
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


def search_movies(query, limit=15):
    """Ask TMDB for movies that match the search text."""
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
    return [build_movie_dict(movie) for movie in results]

def search_movies_by_director(director_name, limit=15):
    """Search for all movies by a specific director."""
    if not director_name:
        return []

    # First, search for the director
    url = f"{BASE_URL}/search/person"
    try:
        response = requests.get(url, params = {"api_key": API_KEY, "query": director_name}, timeout=10)
    except requests.RequestException as err:
        print(f"TMDb fel (seach/person): {err}")
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
        response = requests.get(url, params = {"api_key": API_KEY}, timeout=10)
    except requests.RequestException as err:
        print(f"TMDb-fel (movie_credits): {err}")
        return []
    
    if response.status_code != 200:
        print(f"TMDb-fel (movie_credits): {response.status_code}")
        return []
    
    crew = response.json().get("crew", [])
    directed = [movie for movie in crew if movie.get("job") == "Director"][:limit]

    return [build_movie_dict(movie, director_display_name) for movie in directed]


# ---------- Helper functions for JSON "DB" ----------

def load_users():
    """
    "Read all users from the JSON file.

    If the file does not exist or is broken,
    we just return an empty list so the app still works.
    """
    if not os.path.exists(DB_FILE):
        return []
    with open(DB_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def save_users(users):
    """
    Save the whole users list back into the JSON file.
    This overwrites the file with the new data.
    """
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)


def find_user(username):
    """
    Find one user with a matching username.
    Returns the user dict if found, otherwise None.
    """
    users = load_users()
    for u in users:
        if u["username"] == username:
            return u
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


@app.route("/", methods=["GET", "POST"])
def login():
    """
    If the user is already logged in, redirect to the movies page.
    validate the username and password and start a session.
    If already logged in, go directly to movies.
    """
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
    """
    Handles both displaying the registration form (GET) and processing
    submitted registration data (POST). Validates user input and ensures
    that usernames are unique before saving the user to the JSON database.
    Automatically logs in the user upon successfyul registration. 
    """
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
            
            session["username"] = username
            return redirect(url_for("movies"))

    return render_template("register.html", error=error)


@app.route("/logout")
def logout():
    """
    Logout the current user.
    Removes the username from the session and returns to the login page.
    """
    session.pop("username", None)
    return redirect(url_for("login"))


# ---------- Protected movies route ----------

def login_required(func):
    """
    Decorator that blocks access to a route if the user is not logged in.
    """
    from functools import wraps

    @wraps(func)
    def wrapper(*args, **kwargs):
        """ 
        args = all positional arguments passed to the route
        kwargs = all keyword arguments passed to the route
        """
        # Checks login status
        if "username" not in session:
            return redirect(url_for("login"))
        #call the original function exactly as it was called
        return func(*args, **kwargs)
    #replace the original function wuth the wrapped one
    return wrapper


@app.route("/movies", methods=["GET", "POST"])
@login_required
def movies():
    """
    Displays searched for movies based on user query and search type. 
    Either by movie name or by director.
    Also retrieves the logged-in user's favorite movies for display.
    """
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
    """
    Adds a movie to the logged-in user's list of favorite movies.
    """
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
    """
    Displays the logged-in user's list of favorite movies.
    Allows sorting by rating or release date, with optional reverse sorting.
    """
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
    """
    Removes a movie from the logged-in user's list of favorite movies.
    """
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
    """
    Displays a summary of the logged-in user's favorite movies,
    including total runtime and most common genre.
    """
    username = session["username"]
    user = find_user(username)
    favorites = user.get("favorites", []) if user else []

    # Calculate total runtime
    total_minutes = sum(int(fav.get("runtime", 0)) for fav in favorites)
    hours, minutes = divmod(total_minutes, 60)
    
    # Collect all genres
    all_genres = []
    for fav in favorites:
        genres = fav.get("genres")
        if isinstance(genres, str):
            all_genres.extend([g.strip() for g in genres.split(",")])
        elif genres:
            all_genres.extend(genres)
    
    # Find most common genre
    most_common_genre = Counter(all_genres).most_common(1)[0][0] if all_genres else None

    return render_template(
        "wrapped.html",
        hours=hours,
        minutes=minutes,
        most_common_genre=most_common_genre,
        total_movies=len(favorites)
    )

if __name__ == "__main__":
    app.run(debug=True)
