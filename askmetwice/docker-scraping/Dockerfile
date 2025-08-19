# syntax=docker/dockerfile:1
ARG HEADLESS_USER="headless"
ARG HEADLESS_USER_UID="1000"

FROM accetto/debian-vnc-xfce-g3:latest AS ai-scraper-base-chrome
USER 0

ENV VNC_RESOLUTION=2560x1440
ENV VNC_COL_DEPTH=24

RUN \
    apt-get update \
    && apt-get install -y --no-install-recommends \
        gpg curl unzip \
    && apt-get -y autoremove \
    && rm -rf /var/lib/apt/lists/*

# Surpress Chrome's initial startup message
RUN mkdir -p ~/.config/google-chrome
RUN touch ~/.config/google-chrome/First\ Run

# Install Chrome, which in Debian is called google-chrome-stable
RUN curl -fSsL https://dl.google.com/linux/linux_signing_key.pub | sudo gpg --dearmor | sudo tee /usr/share/keyrings/google-chrome.gpg >> /dev/null
RUN echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
RUN sudo apt-get update
RUN sudo apt-get install -y google-chrome-stable

RUN apt-get install -y python3-venv python3-tk

COPY . /home/headless/app
WORKDIR /home/headless/app

# Install python
# RUN python3 -m venv .
# # RUN python3 -m venv .venv
# RUN python3 -m pip install --upgrade pip
# RUN python3 -m pip install -r requirements.txt

# Electrom has a version of the driver that works with modern versions of Chrome
# You can find it here: https://github.com/electron/chromedriver/releases
# Get the latest version number from the Chrome Driver downloads page
RUN VERSION=$(curl -s https://api.github.com/repos/electron/electron/releases/latest | jq -r .tag_name) && \
    ASSET_URL="https://github.com/electron/electron/releases/download/$VERSION/chromedriver-${VERSION}-linux-x64.zip" && \
    wget -q -O /tmp/chromedriver.zip "$ASSET_URL"
RUN unzip /tmp/chromedriver.zip chromedriver -d /usr/local/bin/
RUN chmod +x /usr/local/bin/chromedriver
RUN rm /tmp/chromedriver.zip