import json
import gzip

# key: (playlist_id, snapshot_id) -> gzipped JSON bytes of compact track list
PLAYLIST_ITEMS_CACHE = {}


def dump_tracks(tracks):
    """gzipped compact JSON bytes"""
    payload = json.dumps(tracks, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return gzip.compress(payload)


def load_tracks(tracks_gzip):
    return json.loads(gzip.decompress(tracks_gzip).decode("utf-8"))