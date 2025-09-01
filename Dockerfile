FROM python:3.13-alpine

ARG BUILD_UID
ARG BUILD_GID

# Create a non-root user
RUN addgroup -g $BUILD_GID app && adduser -D -u $BUILD_UID -G app app

RUN apk update && apk upgrade && apk add --no-cache firefox-esr jq curl tar

# Download and install geckodriver
RUN curl -sSL -o geckodriver.tar.gz $(curl -sS https://api.github.com/repos/mozilla/geckodriver/releases/latest | jq -r ".assets[] | select(.name | test(\"linux64.tar.gz$\")) | .browser_download_url") \
    && tar -xzf geckodriver.tar.gz -C /usr/local/bin \
    && chmod +x /usr/local/bin/geckodriver \
    && rm geckodriver.tar.gz

WORKDIR /app

COPY --chown=app:app app/ .

RUN pip install --no-cache-dir -r /app/requirements.txt

# Set the user
USER app

ENTRYPOINT [ "python3", "-u", "app.py" ]
