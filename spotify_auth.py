import spotipy
from spotipy.oauth2 import SpotifyOAuth
import configparser

def get_spotify_client():
    # Load Spotify configuration from config.ini
    config = configparser.ConfigParser()
    config.read('config.ini')

    CLIENT_ID = config['spotify']['client_id']
    CLIENT_SECRET = config['spotify']['client_secret']
    REDIRECT_URI = config['spotify']['redirect_uri']
    SCOPE = config['spotify']['scope']

    # Set up Spotify OAuth
    sp_oauth = SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
        cache_path=".spotify_caches/cache"  # Store token information in a local cache file
    )

    # Initialize Spotify client
    sp = spotipy.Spotify(auth_manager=sp_oauth)

    # Check if the token is available
    if not sp_oauth.get_cached_token():
        # If no token is found, the user will be redirected to log in via Spotify and authorize the app
        print("Please authorize the application.")
        auth_url = sp_oauth.get_authorize_url()
        print(f"Open this URL in your browser: {auth_url}")

        # Open the authorization URL in the browser and ask the user to enter the redirected URL
        response = input("Enter the URL you were redirected to: ")

        # Parse the authorization code from the redirected URL and fetch the access token
        code = sp_oauth.parse_response_code(response)
        token_info = sp_oauth.get_access_token(code)
    else:
        # If a token is found in the cache, reuse it
        token_info = sp_oauth.get_cached_token()

    return sp  # Return the initialized Spotify client