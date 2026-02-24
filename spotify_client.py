import requests

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
        id = track.get("id")
        uri = track.get("uri")

        tracks.append(
            {
                "name": track.get("name"),
                "artists": [a.get("name") for a in track.get("artists", []) if a.get("name")],
                "img": img,
                "id": id,
                "uri":uri
            }
        )
    return tracks