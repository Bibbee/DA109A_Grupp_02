from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import movie_storage as storage
from Movie import Movie
import json
from collections import Counter

app = FastAPI(title="MovieApp API", version="1.0.0")

# Define paths
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

# Database file for users
DB_FILE = "users.json"

# ========== DATA MODELS ==========
class LoginRequest(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    username: str
    message: str


# ========== HELPER FUNCTIONS ==========
def load_users() -> list[dict]:
    """Load users from JSON database"""
    if not os.path.exists(DB_FILE):
        return []
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []

def save_users(users: list[dict]) -> None:
    """Save users to JSON database"""
    with open(DB_FILE, "w") as f:
        json.dump(users, f, indent=2)


def find_user(username: str) -> dict | None:
    """Find user by username"""
    for user in load_users():
        if user.get("username") == username:
            return user
    return None


@app.get("/search.html")
async def serve_search():
    """Serve simple search page"""
    search_file = os.path.join(STATIC_DIR, "search.html")
    if os.path.exists(search_file):
        return FileResponse(search_file, media_type="text/html")
    raise HTTPException(status_code=404, detail="Search page not found")


# ========== MOVIE ROUTES ==========
@app.get("/api/movies/search")
async def search_movies(q: str):
    """Search movies by title."""
    if not q:
        raise HTTPException(status_code=400, detail="Query parameter 'q' is required")
    
    movies = await storage.search_movies(q)
    return {"query": q, "count": len(movies), "movies": movies}

@app.get("/api/movies/{movie_id}")
async def get_movie(movie_id: int):
    """Get detailed information about a specific movie."""
    movie = await storage.fetch_movie(movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    return movie

# ========== USER ROUTES ==========
@app.post("/api/auth/register")
async def register(username: str, password: str):
    """Register a new user account"""
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password required")
    
    users = load_users()
    
    # Check if user already exists
    if find_user(username):
        raise HTTPException(status_code=400, detail="User already exists")
    
    # Create new user
    new_user = {
        "username": username,
        "password": password,  # Note: In production, hash this!
        "list": []
    }
    users.append(new_user)
    save_users(users)
    
    return {"status": "success", "username": username, "message": "User registered successfully"}

@app.post("/api/auth/login")
async def login(username: str, password: str):
    """Login to your account"""
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password required")
    
    user = find_user(username)
    
    if not user or user.get("password") != password:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    return {
        "status": "success",
        "username": username,
        "message": "Login successful",
        "list_count": len(user.get("list", []))
    }

# ========== FAVORITE LIST ROUTES ==========
@app.post("/api/list/add")
async def add_to_list(username: str, movie_id: int, title: str = ""):
    """Add a movie to user's list"""
    if not username:
        raise HTTPException(status_code=400, detail="Username required")
    
    users = load_users()
    user = find_user(username)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if already in list
    user_list = user.get("list", [])
    if any(m.get("id") == movie_id for m in user_list):
        raise HTTPException(status_code=400, detail="Movie already in your list")
    
    # Add to list
    user_list.append({"id": movie_id, "title": title})
    user["list"] = user_list
    save_users(users)
    
    return {"status": "success", "message": f"'{title}' added to your list"}

@app.get("/api/list/{username}")
async def get_list(username: str):
    """Get user's movie list"""
    user = find_user(username)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_list = user.get("list", [])
    return {
        "username": username,
        "count": len(user_list),
        "movies": user_list
    }

@app.delete("/api/list/{username}/{movie_id}")
async def delete_from_list(username: str, movie_id: int):
    """Remove a movie from user's list"""
    users = load_users()
    user = find_user(username)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_list = user.get("list", [])
    original_count = len(user_list)
    
    # Remove the movie
    user["list"] = [m for m in user_list if m.get("id") != movie_id]
    
    if len(user["list"]) == original_count:
        raise HTTPException(status_code=404, detail="Movie not found in your list")
    
    save_users(users)
    return {"status": "success", "message": "Movie removed from your list"}

# ========== TEST ENDPOINT ==========
@app.get("/")
async def root():
    """API documentation"""
    return {
        "app": "MovieApp API",
        "version": "1.0.0",
        "docs": "http://localhost:8000/docs",
        "endpoints": {
            "search": "GET /api/movies/search?q=inception",
            "get_movie": "GET /api/movies/{movie_id}",
            "register": "POST /api/auth/register?username=john&password=pass123",
            "login": "POST /api/auth/login?username=john&password=pass123",
            "add_to_list": "POST /api/list/add?username=john&movie_id=550&title=Fight%20Club",
            "get_list": "GET /api/list/{username}",
            "delete_from_list": "DELETE /api/list/{username}/{movie_id}"
        }
    }