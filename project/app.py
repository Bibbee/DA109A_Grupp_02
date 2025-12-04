from flask import Flask, render_template, request
import requests
from dotenv import load_dotenv
import os

# Create Flask app
app = Flask(__name__)

# Load variables from .env
load_dotenv()
API_KEY = os.getenv("TMDB_API_KEY")  # reads from .env
BASE_URL = "https://api.themoviedb.org/3"


def build_poster_url(poster_path, size="w342"):
    if not poster_path:
        return None
    return f"https://image.tmdb.org/t/p/{size}{poster_path}"


@app.route("/", methods=["GET"])
def index():
    # In Flask, query string = request.args
    query = request.args.get("q", "").strip()
    movies = []

    if query:
        url = f"{BASE_URL}/search/movie"
        params = {"api_key": API_KEY, "query": query}

        response = requests.get(url, params=params)

        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])[:10]

            for m in results:
                movies.append({
                    "title": m.get("title"),
                    "release_date": m.get("release_date"),
                    "rating": m.get("vote_average"),
                    "overview": m.get("overview"),
                    "poster_url": build_poster_url(m.get("poster_path")),
                })
        else:
            print("TMDB error:", response.status_code, response.text)

    # Flask uses render_template and looks in /templates
    return render_template("index.html", movies=movies, query=query)


if __name__ == "__main__":
    app.run(debug=True)
