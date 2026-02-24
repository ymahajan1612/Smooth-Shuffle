from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import FlaskSessionCacheHandler
from flask import session
import os

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
SCOPE = "playlist-read-private playlist-read-collaborative user-library-read playlist-modify-public"

def create_spotify_oauth():
    cache_handler = FlaskSessionCacheHandler(session)
    return SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
        cache_handler=cache_handler,
        show_dialog=True,
    )


def get_token():
    sp_oauth = create_spotify_oauth()
    token_info = sp_oauth.cache_handler.get_cached_token()

    if not token_info or not sp_oauth.validate_token(token_info):
        return None, sp_oauth.get_authorize_url()

    token_info = sp_oauth.cache_handler.get_cached_token()
    return token_info["access_token"], None