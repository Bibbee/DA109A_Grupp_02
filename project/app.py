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


def build_poster_url(poster_path, size="w342"):
    if not poster_path:
        return None
    return f"https://image.tmdb.org/t/p/{size}{poster_path}" 


def search_movies(query):
    """Ask TMDB for movies that match the search text.

    - If the query is empty, we just return an empty list.
    - If TMDB answers, we take the first 10 movies and keep only
      the fields we care about."""
    movies = []
    if not query:
        return movies

    url = f"{BASE_URL}/search/movie"
    params = {"api_key": API_KEY, "query": query}

    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        results = data.get("results", [])[:16]

        for m in results:
            movies.append({
                "id": m.get("id"),
                "title": m.get("title"),
                "release_date": m.get("release_date"),
                "rating": m.get("vote_average"),
                "poster_url": build_poster_url(m.get("poster_path")),
            })
    else:
        print("TMDB error:", response.status_code, response.text)

    return movies


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

    username = session["username"]
    user = find_user(username)
    if not user:
        # om nåt är helt fel, skicka 400 (bad request, ogiltig användare)
        return jsonify({"status": "error", "message": "User not found"}), 400

    if "favorites" not in user:
        user["favorites"] = []

    if not any(str(f["id"]) == str(movie_id) for f in user["favorites"]):
        details = get_movie_details(movie_id)

        user["favorites"].append({
            "id": movie_id,
            "title": title,
            "poster_url": poster_url,
            "release_date": release_date,
            "rating": rating,
            "runtime": details["runtime"], #####
            "genres": details["genres"],   #####
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

    # Gathers the username of the user.
    username = session["username"]

    # This one loads user data from our JSON
    user = find_user(username)
    favorites = user.get("favorites", []) if user else []

    # Render the my_list.html with the user's current info
    return render_template(
        "my_list.html",
        username=username,
        favorites=favorites,
    )

#--- REMOVING MOVIES ROUTE---
@app.route("/remove_favorite", methods=["POST"])
@login_required
def remove_favorite():
    # Decide which movie to remove based on id.
    movie_id = request.form.get("id")

    # Gathers username of the logged in user
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


# Wrapped functions
def get_movie_details(movie_id):
    url = f"{BASE_URL}/movie/{movie_id}"
    params = {"api_key": API_KEY}

    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        return {
            "runtime": data.get("runtime", 0) or 0,
            "genres": [g["name"] for g in data.get("genres", [])],
        }
    return {"runtime": 0, "genres": []}

@app.route("/wrapped")
@login_required
def wrapped():
    username = session["username"]
    user = find_user(username)
    favorites = user.get("favorites", []) if user else []

    total_minutes = 0
    all_genres = []

    # så den ALLTID finns (ingen crash)
    most_common_genre = None

    updated = False

    for fav in favorites:
        runtime = fav.get("runtime")
        genres = fav.get("genres")

        # Om vi redan sparat detaljer → använd direkt
        if runtime is not None and genres is not None:
            total_minutes += int(runtime or 0)
            all_genres.extend(genres)
            continue

        # Annars: hämta en gång från TMDB
        details = get_movie_details(fav["id"])
        runtime = int(details.get("runtime") or 0)
        genres = details.get("genres", [])

        total_minutes += runtime
        all_genres.extend(genres)

        # Backfill så nästa gång går snabbt
        fav["runtime"] = runtime
        fav["genres"] = genres
        updated = True

    if updated and user:
        update_user(user)

    hours = total_minutes // 60
    minutes = total_minutes % 60


    if all_genres:
        from collections import Counter
        most_common_genre = Counter(all_genres).most_common(1)[0][0]

    return render_template(
        "wrapped.html",
        hours=hours,
        minutes=minutes,
        most_common_genre=most_common_genre,
        total_movies=len(favorites)
    )

if __name__ == "__main__":
    app.run(debug=True)
