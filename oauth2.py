#!/usr/bin/env python
import json
import time
import requests
import base64
from urllib import parse


class SpotifyOAuth:
    oauth_auth_url = 'https://accounts.spotify.com/authorize'
    oauth_token_url = 'https://accounts.spotify.com/api/token'

    def __init__(self, client_id: str, client_secret: str, redirect: str, scopes: str, cache: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect = redirect
        self.scopes = scopes
        self.cache = cache

    def get_credentials(self) -> json:
        """
        Get credentials from cache file. Refresh token if it's about to expire.
        :return: token contents as a json object
        """
        try:
            with open(self.cache, 'r') as file:
                creds = json.loads(file.read())
                if self.is_token_expired(creds['expires_at']):
                    print('OAuth token is expired, refreshing...')
                    creds = self.refresh_token(creds['refresh_token'])
        except (IOError, json.decoder.JSONDecodeError):
            print('Error: cache does not exist or is empty')
            return None
        return creds

    def is_token_expired(self, token_expire: int) -> bool:
        """
        Check if token is about to expire - add 30 sec to current time to ensure it doesn't expire during run.
        :param token_expire: time at which the token expires in seconds
        :return: whether or not token is about to expire as a bool
        """
        return (time.time() + 30) > token_expire

    def refresh_token(self, refresh_token: str) -> json:
        """
        Refresh token and update cache file.
        :param refresh_token: refresh token from credentials
        :return: refreshed credentials as a json object
        """
        body = {'grant_type': 'refresh_token',
                'refresh_token': refresh_token}
        response = requests.post(self.oauth_token_url, data=body, headers=self.encode_header())
        token = json.loads(response.content.decode('utf-8'))
        self.save_token(token)
        return token

    def encode_header(self) -> dict:
        """
        Encode header token as required by OAuth specification.
        :return: dict containing header with base64 encoded client credentials
        """
        encoded_header = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode("ascii")).decode("ascii")
        return {'Authorization': f'Basic {encoded_header}'}

    def retrieve_access_token(self, code: str) -> json:
        """
        Request token from API, save to cache, and return it.
        :param code: authorization code retrieved from spotify API
        :return: credentials as a json object
        """
        body = {'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': self.redirect}
        response = requests.post(self.oauth_token_url, data=body, headers=self.encode_header())
        token = json.loads(response.content.decode('utf-8'))
        self.save_token(token)
        return token

    def get_authorize_url(self) -> str:
        """
        Create authorization URL with parameters.
        :return: authorization url with parameters appended
        """
        params = {'client_id': self.client_id,
                  'response_type': 'code',
                  'redirect_uri': self.redirect,
                  'scope': self.scopes}
        return f'{self.oauth_auth_url}?{parse.urlencode(params)}'

    def parse_response_code(self, url: str) -> str:
        """
        Extract code from response url after authorization by user.
        :url: url retrieved after user authorized access
        :return: authorization code extracted from url
        """
        try:
            return url.split('?code=')[1].split('&')[0]
        except IndexError:
            pass

    def save_token(self, token: json):
        """
        Add 'expires at' field to token and save to cache
        :param token: credentials as a json object
        """
        token['expires_at'] = round(time.time()) + int(token['expires_in'])
        with open(self.cache, 'w') as file:
            file.write(json.dumps(token))
