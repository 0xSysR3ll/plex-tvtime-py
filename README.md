# Plex TVTime PY

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/0xsysr3ll/plex-tvtime-py/blob/main/LICENSE)
[![GitHub issues](https://img.shields.io/github/issues/0xsysr3ll/plex-tvtime-py)](https://github.com/0xsysr3ll/plex-tvtime-py/issues)
[![GitHub stars](https://img.shields.io/github/stars/0xsysr3ll/plex-tvtime-py)](https://github.com/0xsysr3ll/plex-tvtime-py/stargazers)
[![Python Version](https://img.shields.io/badge/python-3.10%20|%203.11%20-blue)](https://www.python.org/downloads/)
[![Docker Pulls](https://img.shields.io/docker/pulls/0xsysr3ll/plex-tvtime-py)](https://hub.docker.com/r/0xsysr3ll/plex-tvtime-py)


**Plex TVTime PY** is a small python application for Plex that integrates with TVTime, a popular TV show tracking service. With this application, you can sync your TVTime watchlist with Plex and easily keep track of your favorite shows.

## Features

- Sync your TVTime watchlist with Plex (movies and series)

## Installation

To deploy and configure the application, follow these steps:

1. Create a `config/config.yml` file based on the example provided.
2. Launch the Docker container using the provided `docker-compose.yml` file (make any necessary adaptations).
3. In Plex, go to Settings > Webhooks.
4. Add a new webhook with the URL exposed by the docker (the docker publishes the port `5000` by default).
> If you are not using a reverse proxy, it would be `http://<your_ip>:5000`

## Usage
Once the webhook is deployed and configured, your TVTime watchlist will automatically sync with Plex.

## Contributing
Contributions are welcome! If you have any ideas, bug reports, or feature requests, please open an issue or submit a pull request on GitHub.

## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more information.

## Disclaimer

This project is inspired by [@Zggis](https://github.com/Zggis/plex-tvtime) and serves as a homage to the original work.
It is developed with the intention of building upon the ideas presented by [@Zggis](https://github.com/Zggis/plex-tvtime), offering new features or improvements.

This project does not copy any proprietary code or infringe upon the original author's intellectual property.
It is created with respect and admiration for the original work, aiming to contribute to the community by providing an alternative or complementary solution.