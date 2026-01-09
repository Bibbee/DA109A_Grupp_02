from pydantic import BaseModel


class Movie(BaseModel):
    id: int = 0
    title: str = ""
    release_date: str = ""
    rating: float = 0.0
    poster_url: str = ""
    director: str = ""
    runtime: int = 0
    genres: list = []

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "releaseDate": self.release_date,
            "rating": self.rating,
            "posterUrl": self.poster_url,
            "director": self.director,
            "runtime": self.runtime,
            "genres": self.genres
        }
