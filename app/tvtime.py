"""
tvtime.py

This module provides a class for interacting with the TVTime API.
It includes methods for logging in, marking episodes as watched, and watching movies on TVTime.
"""

import time
import json
import sys
import requests
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from utils.logger import logging as log  # pylint: disable=import-error

BASE_URL = "app.tvtime.com"


class TVTime():
    """
    A class for interacting with the TVTime API.

    Args:
        username (str): The username for the TVTime account.
        password (str): The password for the TVTime account.
        driver_location (str): The location of the Firefox driver executable.
        browser_location (str): The location of the Firefox browser executable.
    """

    def __init__(
        self, user: str, username: str = None, password: str = None,
        driver_location: str = None, browser_location: str = None
    ):
        """
        Initializes a new instance of the TVTime class.

        Args:
            user (str): The name of plex's user to map with TVTime.
            username (str): The username for the TVTime account.
            password (str): The password for the TVTime account.
            driver_location (str): The location of the Firefox driver executable.
            browser_location (str): The location of the Firefox browser executable.
        """
        self.user = user
        self.username = username
        self.password = password
        self.token: str = ""
        self.refresh_token: str = ""
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--allow-origins=*")
        options.add_argument("--log-level=3")

        if browser_location:
            options.binary_location = browser_location

        try:
            log.info("Initializing Firefox driver")
            self.driver = webdriver.Firefox(
                service=Service(driver_location), options=options)
        except Exception as _:  # pylint: disable=broad-except
            log.error("Error initializing Firefox driver: %s ", _)
            sys.exit(1)

    def login(self) -> None:
        """
        Logs in to the TVTime API using Selenium and requests.

        This method performs the following steps:
        1. Fetches a JWT token from the local storage using Selenium.
        2. Uses the JWT token to authenticate with the TVTime API.
        3. Extracts the JWT token and refresh token from the API response.

        Raises:
            Exception: If there is an error fetching the JWT token or connecting to the TVTime API.

        Returns:
            None
        """
        driver = self.driver
        driver.get(f"https://{BASE_URL}/welcome?mode=auth")
        time.sleep(5)  # The page can take a while to load

        jwt_token: str = None
        for i in range(1, 4):
            time.sleep(5 + (2 * i))  # Wait a bit longer each time
            log.debug(f"Attempt {i} to fetch JWT token")
            # We need to fetch a JWT token from the local storage in order to connect
            try:
                jwt_token = driver.execute_script(
                    "return window.localStorage.getItem('flutter.jwtToken');")
                if jwt_token:
                    break
            except Exception as _:  # pylint: disable=broad-except
                log.error("Error fetching JWT token: %s", _)
                break

        if jwt_token is None:
            log.error(
                "Unable to fetch JWT token using Selenium, application must exit.")
            driver.quit()
            sys.exit(1)
        log.info("JWT token fetched successfully ! Exiting Selenium...")
        driver.quit()

        jwt_token = jwt_token.strip('"')

        headers = {
            'Authorization': f'Bearer {jwt_token}',
            'Content-Type': 'application/json',
        }
        credentials = {
            "username": self.username,
            "password": self.password
        }
        log.debug("Trying to connect to your account...")
        login_url = (
            'https://beta-app.tvtime.com/sidecar?'
            'o=https://auth.tvtime.com/v1/login'
        )
        try:
            r = requests.post(
                url=login_url,
                headers=headers,
                data=json.dumps(credentials),
                timeout=(5, 10)
            )
        except requests.exceptions.RequestException as _:
            log.error("Error connecting to TVTime API : %s", _)

        try:
            auth_resp = r.json()
        except json.JSONDecodeError as _:
            log.error("Error decoding JSON response: %s", _)
            sys.exit(1)
        if auth_resp is None:
            log.error("Error fetching JWT tokens from TVTime API")
            sys.exit(1)
        # We need to extract the JWT token and the refresh token from the response
        try:
            token = auth_resp["data"]["jwt_token"]
            self.token = token
            self.refresh_token = auth_resp["data"]["jwt_refresh_token"]
        except KeyError as _:
            log.error("Error crafting JWT token for TVTime API : %s", _)
            sys.exit(1)

        log.info("Successfully connected to %s's TVtime account !", self.user)

    def watch_episode(self, episode_id: int, retry: bool = False) -> None:
        """
        Marks an episode as watched in TVTime.

        Args:
            episode_id (int): The ID of the episode to be marked as watched.

        Returns:
            None

        Raises:
            None: This method does not raise any exceptions.

        """

        if episode_id is None or not isinstance(episode_id, int):
            log.error("Invalid episode ID provided")

        headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json',
            'Host': f'{BASE_URL}:80'
        }

        watch_api = (
            f'https://{BASE_URL}/sidecar?'
            f'o=https://api2.tozelabs.com/v2/watched_episodes/episode/{episode_id}'
            '&is_rewatch=0'
        )
        try:
            r = requests.post(
                url=watch_api,
                headers=headers,
                data=json.dumps(self.refresh_token),
                timeout=(5, 10)
            )
        except requests.exceptions.RequestException as _:
            log.error("Error connecting to TVTime API : %s", _)

        try:
            result = r.json()
        except json.JSONDecodeError as _:
            log.error("Error decoding JSON response: %s", _)
            if retry:
                log.error(
                    "Error while watching movie a second time !"
                    "Something is not right..."
                )
                return
            log.debug("Maybe the jwt token has expired, trying to refresh it...")
            self.login()
            log.info("Retrying to watch the episode...")
            self.watch_episode(episode_id=episode_id, retry=True)
            return

        status = result.get("result")
        if status is None or status != "OK":
            log.error("Error while watching episode !")

        season = result.get("season").get("number")
        episode = result.get("number")
        show = result.get("show").get("name")

        log.info(
            f"Successfully marked {show} S{season}E{episode} as watched !")

    def watch_movie(self, movie_uuid: str, retry: bool = False) -> None:
        """
        Watch a movie on TVTime.

        Args:
            movie_uuid (str): The UUID of the movie to watch.

        Returns:
            None: This method does not return anything.

        Raises:
            None: This method does not raise any exceptions.
        """

        headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json',
            'Host': f'{BASE_URL}:80'
        }

        watch_api = (
            f"https://{BASE_URL}/sidecar?"
            f"o=https://msapi.tvtime.com/prod/v1/tracking/{movie_uuid}/watch"
        )
        try:
            r = requests.post(
                url=watch_api,
                headers=headers,
                timeout=(5, 10)
            )
        except requests.exceptions.RequestException as _:
            log.error("Error connecting to TVTime API: %s", _)
            return

        try:
            result = r.json()
        except json.JSONDecodeError as _:
            log.error("Error decoding JSON response: %s", _)
            if retry:
                log.error(
                    "Error while watching movie a second time !"
                    "Something is not right..."
                )
                return
            log.debug("Maybe the jwt token has expired, trying to refresh it...")
            self.login()
            log.info("Retrying to watch the movie...")
            self.watch_movie(movie_uuid=movie_uuid, retry=1)
            return

        status = result.get("status")
        if status is None or status != "success":
            log.error("Error while watching movie !")
            return

        log.info("Successfully marked the movie as watched !")

    def get_movie_uuid(self, movie_id: int) -> str:
        """
        Retrieves the UUID of a movie from the TVTime API based on the provided movie ID.

        Args:
            movie_id (int): The ID of the movie.

        Returns:
            str: The UUID of the movie if found, None otherwise.
        """
        if movie_id is None or not isinstance(movie_id, int):
            log.error("Invalid movie ID provided")

        headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json',
            'Host': f'{BASE_URL}:80'
        }
        search_url = (
            f"https://{BASE_URL}/sidecar?"
            f"o=https://search.tvtime.com/v1/search/series,movie&q={movie_id}"
            "&offset=0&limit=1"
        )
        try:
            r = requests.get(
                url=search_url,
                headers=headers,
                timeout=(5, 10)
            )
        except requests.exceptions.RequestException as _:
            log.error("Error connecting to TVTime API : %s", _)

        try:
            search = r.json()
        except json.JSONDecodeError as _:
            log.error("Error decoding JSON response: %s", _)
            return None

        status = search.get("status")
        if status is None or status != "success":
            log.error(f"Error while searching for the movie {movie_id}")
            return None

        try:
            movies = search.get("data", [])
            for movie in movies:
                if movie.get("id") == movie_id:
                    return movie.get("uuid")
        except KeyError as _:
            log.error("Error while fetching movie UUID : %s", _)
            return None
        return None
