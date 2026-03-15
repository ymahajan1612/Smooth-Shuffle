import sqlite3
import json
import gzip

class DBHandler:

    def __init__(self):
        self.conn = None
        self.createConnection()
        self.createTables()

    def createConnection(self):
        try:
            self.conn = sqlite3.connect('caching/playlist_cache.db')
        except sqlite3.Error as e:
            print("Error establishing connection: ", e)


    def closeConnection(self):
        if self.conn:
            self.conn.close()
    
    def createTables(self):
        """
        Creates Table:
        - playlists: stores playlist ID, snapshot ID pair and the track as a gzip compressed json 
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS playlists (
                Playlist_ID TEXT PRIMARY KEY NOT NULL,
                Snapshot_ID TEXT NOT NULL,
                Tracks BLOB NOT NULL
                );

            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS track_analysis (
                    track_id TEXT PRIMARY KEY NOT NULL,
                    tempo REAL NOT NULL,
                    energy REAL NOT NULL,
                    danceability REAL NOT NULL,
                    loudness REAL NOT NULL,
                    acousticness REAL NOT NULL
                );
            """)
            self.conn.commit()
        except sqlite3.Error as e:
            self.conn.rollback()
            print("Error creating tables: ", e)

    def insertPlaylist(self, playlist_id, snapshot_id, tracks):
        try:
            cursor = self.conn.cursor()
            tracks_gzip = gzip.compress(json.dumps(tracks, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
            cursor.execute("""
            INSERT INTO playlists (Playlist_ID, Snapshot_ID, Tracks)
            VALUES (?, ?, ?)
            ON CONFLICT(Playlist_ID) DO UPDATE SET
            Snapshot_ID = excluded.Snapshot_ID,
            Tracks = excluded.Tracks;
            """, (playlist_id, snapshot_id, tracks_gzip))
            
            self.conn.commit()
            return None
        
        except sqlite3.Error as e:
            self.conn.rollback()
            return f"Error inserting playlist with ID {playlist_id}: {e}"

    def getPlaylist(self, playlist_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
            SELECT Snapshot_ID, Tracks FROM playlists
            WHERE Playlist_ID = ?;
                           """, (playlist_id,))
            row = cursor.fetchone()
            if not row:
                return None
            snapshot_id = row[0]
            tracks_gzip = row[1]
            return snapshot_id, json.loads(gzip.decompress(tracks_gzip).decode("utf-8"))
        except sqlite3.Error as e:
            print("Error retrieving Playlist: ", e)
            return None    
        
    def deletePlaylist(self, playlist_id):
        try:
            cursor = self.conn.cursor()
            # Delete from playlist table
            cursor.execute("""
            DELETE FROM playlists WHERE Playlist_ID = ?;
            """, (playlist_id,))

            self.conn.commit()
        except sqlite3.Error as e:
            self.conn.rollback()

    def insertTrack(self, track_id, track_features):
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO track_analysis (
                    track_id,
                    tempo,
                    energy,
                    danceability,
                    loudness,
                    acousticness
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (track_id, 
                  track_features['tempo'], 
                  track_features['energy'], 
                  track_features['danceability'], 
                  track_features['loudness'], 
                  track_features['acousticness']))
            self.conn.commit()
            print("track inserted")
        except sqlite3.Error as e:
            print("track not inserted")
            self.conn.rollback()
            print("Error inserting track features:", e)    
                
    def fetchTrackFeatures(self, track_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT tempo, energy, danceability, loudness, acousticness
                FROM track_analysis
                WHERE track_id = ?
            """, (track_id,))
            row = cursor.fetchone()

            if row:
                return {
                    "tempo": row[0],
                    "energy": row[1],
                    "danceability": row[2],
                    "loudness": row[3],
                    "acousticness": row[4],
                }
            return None

        except sqlite3.Error as e:
            print("Error fetching track features:", e)
            return None