#!/usr/bin/env python3
"""
Script to update a user's favorite movies with runtime and genres from TMDB API
"""

import json
import requests
from dotenv import load_dotenv
import os
import sys

# Load environment variables
load_dotenv()
API_KEY = os.getenv("API_KEY")
BASE_URL = "https://api.themoviedb.org/3"

if not API_KEY:
    print("Error: API_KEY not found in .env file")
    exit(1)

def get_movie_details(movie_id):
    """Fetch full movie details from TMDB including runtime, genres, and director (in ONE call)."""
    url = f"{BASE_URL}/movie/{movie_id}"
    params = {"api_key": API_KEY, "append_to_response": "credits"}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            genres = [g.get("name") for g in data.get("genres", [])]
            
            # Extract director from credits
            director = None
            for person in data.get("credits", {}).get("crew", []):
                if person.get("job") == "Director":
                    director = person.get("name")
                    break
            
            return {
                "runtime": data.get("runtime"),
                "genres": ", ".join(genres) if genres else None,
                "director": director
            }
    except Exception as e:
        print(f"Error fetching details for movie {movie_id}: {e}")
    
    return {"runtime": None, "genres": None, "director": None}


def update_user_movies(username):
    """Update all movies for a specified user with runtime, genres, and director."""
    
    # Read users.json
    with open("users.json", "r", encoding="utf-8") as f:
        users = json.load(f)
    
    # Find the user
    target_user = None
    for user in users:
        if user.get("username") == username:
            target_user = user
            break
    
    if not target_user:
        print(f"Error: User '{username}' not found")
        return
    
    favorites = target_user.get("favorites", [])
    print(f"Found {len(favorites)} movies in {username}'s favorites")
    print("Fetching runtime, genres, and director from TMDB...\n")
    
    updated_count = 0
    
    for i, movie in enumerate(favorites, 1):
        movie_id = movie.get("id")
        title = movie.get("title")
        
        # Skip if already has runtime, genres, and director
        if movie.get("runtime") and movie.get("genres") and movie.get("director"):
            print(f"[{i}/{len(favorites)}] {title} - Already has all info, skipping")
            continue
        
        print(f"[{i}/{len(favorites)}] Updating: {title}...", end=" ")
        
        details = get_movie_details(movie_id)
        
        if details["runtime"]:
            movie["runtime"] = details["runtime"]
            updated_count += 1
        
        if details["genres"]:
            movie["genres"] = details["genres"]
        
        if details["director"]:
            movie["director"] = details["director"]
        
        if details["runtime"] or details["genres"] or details["director"]:
            print(f"✓ (Runtime: {details['runtime']} min, Genres: {details['genres']}, Director: {details['director']})")
        else:
            print("✗ Could not fetch details")
    
    # Write updated users.json
    with open("users.json", "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Updated {updated_count} movies in {username}'s favorites")
    print("✓ users.json has been saved")

if __name__ == "__main__":
    # Allow specifying username as command line argument, default to "123"
    username = sys.argv[1] if len(sys.argv) > 1 else "rList"
    update_user_movies(username)
