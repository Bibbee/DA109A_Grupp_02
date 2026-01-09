"""
Movie Storage Service Layer
Handles all TMDB API calls and movie data retrieval
"""

import httpx
import os
from Movie import Movie
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
BASE_URL = "https://api.themoviedb.org/3"

if not API_KEY:
    print("Warning: API_KEY not set in .env file")

def build_poster_url(poster_path: str) -> str:
    """
    Construct full poster URL from TMDb path
    """
    if not poster_path:
        return ""
    return f"https://image.tmdb.org/t/p/w500{poster_path}"

async def search_movies(query: str, limit: int = 15) -> list:
    """
    Search for movies by title using TMDb API
    Args:
        query: Movie title to search for
        limit: Maximum number of results to return
    Returns:
        List of Movie dictionaries with full details
    """
    if not query.strip():
        return []
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/search/movie",
                params={
                    "api_key": API_KEY,
                    "query": query,
                    "page": 1,
                    "include_adult": False
                }
            )
            response.raise_for_status()
            
            data = response.json()
            movies = []
            
            # Get search results and fetch detailed info for each
            for result in data.get("results", [])[:limit]:
                movie_id = result.get("id", 0)
                if not movie_id:
                    continue
                
                # Fetch detailed movie info
                detail_response = await client.get(
                    f"{BASE_URL}/movie/{movie_id}",
                    params={
                        "api_key": API_KEY,
                        "append_to_response": "credits"
                    }
                )
                detail_response.raise_for_status()
                detail_data = detail_response.json()
                
                # Extract director from credits
                director = ""
                if "credits" in detail_data:
                    for person in detail_data["credits"].get("crew", []):
                        if person.get("job") == "Director":
                            director = person.get("name", "")
                            break
                
                # Extract genres
                genres = [g.get("name", "") for g in detail_data.get("genres", [])]
                
                movie = Movie(
                    id=detail_data.get("id", 0),
                    title=detail_data.get("title", ""),
                    release_date=detail_data.get("release_date", ""),
                    rating=detail_data.get("vote_average", 0.0),
                    poster_url=build_poster_url(detail_data.get("poster_path", "")),
                    director=director,
                    runtime=detail_data.get("runtime", 0),
                    genres=genres
                )
                movies.append(movie.to_dict())
            return movies
        
    except httpx.RequestError as e:
        print(f"API request error: {e}")
        return []
    except Exception as e:
        print(f"Error searching movies: {e}")
        return []

async def fetch_movie(movie_id: int) -> dict | None:
    """
    Fetch detailed movie information by ID from TMDb API
    Args:
        movie_id: The TMDb movie ID
    Returns:
        Movie dictionary with full details, or None if not found
    """
    if not movie_id:
        return None
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/movie/{movie_id}",
                params={"api_key": API_KEY}
            )
            response.raise_for_status()
            data = response.json()
            
            # Extract director from crew
            director = ""
            if "credits" in data:
                for person in data["credits"].get("crew", []):
                    if person.get("job") == "Director":
                        director = person.get("name", "")
                        break
            
            # Extract genres
            genres = [g.get("name", "") for g in data.get("genres", [])]
            movie = Movie(
                id=data.get("id", 0),
                title=data.get("title", ""),
                release_date=data.get("release_date", ""),
                rating=data.get("vote_average", 0.0),
                poster_url=build_poster_url(data.get("poster_path", "")),
                director=director,
                runtime=data.get("runtime", 0),
                genres=genres
            )
            return movie.to_dict()
        
    except httpx.RequestError as e:
        print(f"API request error: {e}")
        return None
    except Exception as e:
        print(f"Error fetching movie: {e}")
        return None
