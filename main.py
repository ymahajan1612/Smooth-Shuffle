from dotenv import load_dotenv
import os
import time
import json
import gzip
import requests
from flask import Flask, request, url_for, session, redirect
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import FlaskSessionCacheHandler

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")

SCOPE = "playlist-read-private playlist-read-collaborative user-library-read playlist-modify-public"

# key: (playlist_id, snapshot_id) -> gzipped JSON bytes of compact track list
PLAYLIST_ITEMS_CACHE = {}


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


def spotify_get(url, token, params=None):
    r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, params=params)
    return r

def get_snapshot_id(playlist_id, token):
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}"
    r = spotify_get(url, token, params={"fields": "snapshot_id"})
    if r.status_code >= 400:
        return None, {"error": {"status": r.status_code, "message": r.text}}
    return r.json().get("snapshot_id"), None


def fetch_all_playlist_items(playlist_id, token):
    """
    Pagination for playlist contents using /items.
    """
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}/items"
    limit = 50
    offset = 0
    items = []

    while True:
        r = spotify_get(url, token, params={"limit": limit, "offset": offset})
        if r.status_code == 403:
            return None, {"error": {"status": 403, "message": "Forbidden: cannot read items for this playlist."}}
        if r.status_code >= 400:
            return None, {"error": {"status": r.status_code, "message": r.text}}

        data = r.json()
        items.extend(data.get("items", []))

        if not data.get("next"):
            break
        offset += limit

    return items, None


def compact_tracks(items):
    """
    Convert Spotify's /items response to a small list of dicts needed for rendering.
    """
    tracks = []
    for entry in items:
        track = entry.get("item")
        if not track or track.get("type") != "track":
            continue

        album = track.get("album") or {}
        images = album.get("images") or []
        img = images[0]["url"] if images else ""

        tracks.append(
            {
                "name": track.get("name"),
                "artists": [a.get("name") for a in track.get("artists", []) if a.get("name")],
                "img": img,
            }
        )
    return tracks


def dump_tracks(tracks):
    """gzipped compact JSON bytes"""
    payload = json.dumps(tracks, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return gzip.compress(payload)


def load_tracks(tracks_gzip):
    return json.loads(gzip.decompress(tracks_gzip).decode("utf-8"))


@app.route("/")
def home():
    token, auth_url = get_token()
    if not token:
        return redirect(auth_url)
    return redirect(url_for("get_playlists"))


@app.route("/callback")
def callback():
    sp_oauth = create_spotify_oauth()
    code = request.args.get("code")
    if not code:
        return "Missing code", 400
    sp_oauth.get_access_token(code)
    return redirect(url_for("get_playlists"))


@app.route("/get_playlists")
def get_playlists():
    from spotipy import Spotify

    token, auth_url = get_token()
    if not token:
        return redirect(auth_url)

    sp = Spotify(auth=token)
    playlists = sp.current_user_playlists()
    user_id = sp.current_user()["id"]

    html = ""
    for pl in playlists.get("items", []):
        # only show playlists you own
        if pl["owner"]["id"] != user_id:
            continue

        img = pl["images"][0]["url"] if pl.get("images") else ""
        html += f"""
        <div style="margin-bottom:20px;">
            <strong>{pl['name']}</strong><br>
            {f'<img src="{img}" style="width:200px;height:200px;">' if img else ''}
            <form action="/view" method="GET">
                <input type="hidden" name="playlist_name" value="{pl['name']}">
                <input type="hidden" name="playlist_id" value="{pl['id']}">
                <button type="submit">View Playlist</button>
            </form>
        </div>
        """
    return html


@app.route("/view")
def view():
    token, auth_url = get_token()
    if not token:
        return redirect(auth_url)

    playlist_id = request.args.get("playlist_id")
    playlist_name = request.args.get("playlist_name", "Playlist")

    # 1) snapshot-based invalidation
    snapshot_id, err = get_snapshot_id(playlist_id, token)
    if err or not snapshot_id:
        return f"<pre>{err}</pre>", 500

    key = (playlist_id, snapshot_id)

    # check if the snapshot_id exists in our cache 
    tracks_gzip = PLAYLIST_ITEMS_CACHE.get(key)
    if tracks_gzip:
        tracks = load_tracks(tracks_gzip)
    else:
        # Fetch from /items
        items, err = fetch_all_playlist_items(playlist_id, token)
        if err:
            status = err.get("error", {}).get("status", 500)
            return f"<h2>{playlist_name}</h2><pre>{err}</pre>", status

        tracks = compact_tracks(items)
        # store the playlist contents in cache
        PLAYLIST_ITEMS_CACHE[key] = dump_tracks(tracks)

    # render
    songs_html = f"""
    <h2>{playlist_name}</h2>
    <div style="margin-top:15px;"></div>
    """

    for t in tracks:
        artists_str = ", ".join(t.get("artists", []))
        img = t.get("img", "")
        name = t.get("name") or "Unknown"

        songs_html += f"""
            <div style="display:flex;align-items:center;margin-bottom:15px;">
                {f'<img src="{img}" width="60" height="60" style="margin-right:15px;">' if img else ''}
                <div>
                    <div><strong>{name}</strong></div>
                    <div style="color:gray;">{artists_str}</div>
                </div>
            </div>
        """

    return songs_html


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)