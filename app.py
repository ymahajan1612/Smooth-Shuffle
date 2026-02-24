import os
from caching.playlist_DB_handler import DBHandler
from spotify_client import get_snapshot_id, fetch_all_playlist_items, compact_tracks
from spotify_auth import create_spotify_oauth, get_token
from flask import Flask, request, url_for, session, redirect
from spotipy import Spotify


app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")


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
    db_client = DBHandler()


    snapshot_id, err = get_snapshot_id(playlist_id, token)
    if err or not snapshot_id:
        return f"<pre>{err}</pre>", 500


    # check if the snapshot_id exists in our cache 
    db_result = db_client.getPlaylist(playlist_id)
    if db_result:
        fetched_snapshot_id = db_result[0]

    if not db_result or fetched_snapshot_id != snapshot_id:
        # Fetch from /items
        items, err = fetch_all_playlist_items(playlist_id, token)
        if err:
            status = err.get("error", {}).get("status", 500)
            return f"<h2>{playlist_name}</h2><pre>{err}</pre>", status
        tracks = compact_tracks(items)
        # store the playlist contents in cache
        db_client.insertPlaylist(playlist_id, snapshot_id, tracks)
    else:
        tracks = db_result[1]

    # render
    songs_html = f"""
    <h2>{playlist_name}</h2>
    <div style="margin-top:15px;"></div>
    <form action="/smooth" method="POST" style="margin:0;">
        <input type="hidden" name="playlist_id" value=f"{playlist_id}">
        <input type="hidden" name="snapshot_id" value=f"{snapshot_id}">
        <button type="submit">Smooth Shuffle</button>
    </form>
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

@app.route("/smooth", methods=["POST"])
def smooth():
    token, auth_url = get_token()
    if not token:
        return redirect(auth_url)

    playlist_id = request.form.get("playlist_id")
    snapshot_id = request.form.get("snapshot_id")
    
    return ""

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)