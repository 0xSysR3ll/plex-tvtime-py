import time
import json
import requests
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from utils.logger import logging as log

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
        self, username: str = None, password: str = None,
        driver_location: str = None, browser_location: str = None
    ):
        """
        Initializes a new instance of the TVTime class.

        Args:
            username (str): The username for the TVTime account.
            password (str): The password for the TVTime account.
            driver_location (str): The location of the Firefox driver executable.
            browser_location (str): The location of the Firefox browser executable.
        """
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
        except Exception as e:
            log.error("Error initializing Firefox driver: %s ", e)
            exit(1)

    def login(self):
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
            except Exception as e:
                log.error("Error fetching JWT token: %s", e)
                break

        if jwt_token is None:
            log.error(
                "Unable to fetch JWT token using Selenium, application must exit.")
            driver.quit()
            exit(1)
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
        login_url = "https://beta-app.tvtime.com/sidecar?o=https://auth.tvtime.com/v1/login"
        try:
            r = requests.post(
                url=login_url,
                headers=headers,
                data=json.dumps(credentials)
            )
        except requests.exceptions.RequestException as e:
            log.error("Error connecting to TVTime API : %s", e)

        try:
            auth_resp = r.json()
        except json.JSONDecodeError as e:
            log.error("Error decoding JSON response")
            exit(1)
        if auth_resp is None:
            log.error("Error fetching JWT tokens from TVTime API")
            exit(1)
        # We need to extract the JWT token and the refresh token from the response
        try:
            token = auth_resp["data"]["jwt_token"]
            self.token = token
            self.refresh_token = auth_resp["data"]["jwt_refresh_token"]
        except KeyError as e:
            log.error("Error crafting JWT token for TVTime API : %s", e)
            exit(1)

        log.info("Successfully connected to your account !")

    def watch_episode(self, episode_id: int = None):
        if episode_id is None or not isinstance(episode_id, int):
            log.error("Invalid episode ID provided")

        headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json',
            'Host': f'{BASE_URL}:80'
        }

        watch_api = f'https://{BASE_URL}/sidecar?o=https://api2.tozelabs.com/v2/watched_episodes/episode/{episode_id}&is_rewatch=0'
        try:
            r = requests.post(
                url=watch_api,
                headers=headers,
                data=json.dumps(self.refresh_token)
            )
        except requests.exceptions.RequestException as e:
            log.error("Error connecting to TVTime API : %s", e)

        try:
            result = r.json()
        except json.JSONDecodeError as e:
            log.error("Error decoding JSON response")
            return

        status = result.get("result")
        if status is None or status != "OK":
            log.error("Error while watching episode !")

        season = result.get("season").get("number")
        episode = result.get("number")
        show = result.get("show").get("name")

        log.info(
            f"Successfully marked {show} S{season}E{episode} as watched !")

    def watch_movie(self, movie_uuid):
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json',
            'Host': f'{BASE_URL}:80'
        }

        watch_api = f"https://{BASE_URL}/sidecar?o=https://msapi.tvtime.com/prod/v1/tracking/{movie_uuid}/follow"
        try:
            r = requests.post(
                url=watch_api,
                headers=headers,
            )
        except:
            log.error("Error connecting to TVTime API")
            return

        try:
            result = r.json()
        except json.JSONDecodeError as e:
            log.error("Error decoding JSON response")
            return

        status = result.get("status")
        if status is None or status != "success":
            log.error("Error while watching movie !")
            return

        log.info("Successfully marked the movie as watched !")

    def get_movie_uuid(self, movie_id) -> str:
        if movie_id is None or not isinstance(movie_id, int):
            log.error("Invalid movie ID provided")

        headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json',
            'Host': f'{BASE_URL}:80'
        }
        search_url = f"https://{BASE_URL}/sidecar?o=https://search.tvtime.com/v1/search/series,movie&q={movie_id}&offset=0&limit=1"
        try:
            r = requests.get(
                url=search_url,
                headers=headers
            )
        except requests.exceptions.RequestException as e:
            log.error("Error connecting to TVTime API : %s", e)

        try:
            search = r.json()
        except:
            log.error("Error decoding JSON response")
            return None

        status = search.get("status")
        if status is None or status != "success":
            log.error(f"Error while searching for the movie {movie_id}")
            return None

        try:
            movies = search.get("data", [])
            for movie in movies:
                if movie.get("id") == movie_id:
                    movie_name = movie.get("name")
                    return movie.get("uuid")
        except KeyError as e:
            log.error("Error while fetching movie UUID : %s", e)
            return None
        return None