import requests
import json
import os
from dotenv import load_dotenv


def getSongFeatures(spotify_track_id):
    load_dotenv()
    url = f"https://track-analysis.p.rapidapi.com/pktx/spotify/{spotify_track_id}"
    headers = {
    "x-rapidapi-host": "track-analysis.p.rapidapi.com",
    "x-rapidapi-key": os.getenv("RAPIDAPI_KEY")
    }

    response = requests.get(url, headers=headers, timeout=15)
    return response.json()



def smoothShuffleFeatures(feature_response):
    print(feature_response)
    features = dict()
    features['tempo'] = feature_response['tempo']
    features['energy'] = feature_response['energy']
    features['danceability'] = feature_response['danceability']
    features['acousticness'] = feature_response['acousticness']

    loudness_str = feature_response['loudness']
    loudness_value = float(loudness_str.replace(" dB", ""))
    features['loudness'] = loudness_value

    return features