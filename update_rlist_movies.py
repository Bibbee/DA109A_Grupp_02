#!/usr/bin/env python3
"""
Script to update rList user's favorite movies with runtime and genres from TMDB API
"""

import json
import requests
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
API_KEY = os.getenv("API_KEY")
BASE_URL = "https://api.themoviedb.org/3"

if not API_KEY:
    print("Error: API_KEY not found in .env file")
    exit(1)

def get_movie_details(movie_id):
    """Fetch full movie details from TMDB including runtime and genres."""
    url = f"{BASE_URL}/movie/{movie_id}"
    params = {"api_key": API_KEY}
    
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            genres = [g.get("name") for g in data.get("genres", [])]
            return {
                "runtime": data.get("runtime"),
                "genres": ", ".join(genres) if genres else None
            }
    except Exception as e:
        print(f"Error fetching details for movie {movie_id}: {e}")
    
    return {"runtime": None, "genres": None}


def update_rlist_movies():
    """Update all movies in rList with runtime and genres."""
    
    # Read users.json
    with open("users.json", "r", encoding="utf-8") as f:
        users = json.load(f)
    
    # Find rList user
    rlist_user = None
    for user in users:
        if user.get("username") == "rList":
            rlist_user = user
            break
    
    if not rlist_user:
        print("Error: rList user not found")
        return
    
    favorites = rlist_user.get("favorites", [])
    print(f"Found {len(favorites)} movies in rList's favorites")
    print("Fetching runtime and genres from TMDB...\n")
    
    updated_count = 0
    
    for i, movie in enumerate(favorites, 1):
        movie_id = movie.get("id")
        title = movie.get("title")
        
        # Skip if already has runtime and genres
        if movie.get("runtime") and movie.get("genres"):
            print(f"[{i}/{len(favorites)}] {title} - Already has runtime and genres, skipping")
            continue
        
        print(f"[{i}/{len(favorites)}] Updating: {title}...", end=" ")
        
        details = get_movie_details(movie_id)
        
        if details["runtime"]:
            movie["runtime"] = details["runtime"]
            updated_count += 1
        
        if details["genres"]:
            movie["genres"] = details["genres"]
        
        if details["runtime"] or details["genres"]:
            print(f"✓ (Runtime: {details['runtime']} min, Genres: {details['genres']})")
        else:
            print("✗ Could not fetch details")
    
    # Write updated users.json
    with open("users.json", "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Updated {updated_count} movies in rList's favorites")
    print("✓ users.json has been saved")


if __name__ == "__main__":
    update_rlist_movies()
