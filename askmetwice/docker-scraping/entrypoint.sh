#!/bin/bash

cd /home/headless

echo "================================================================"
echo "Updating Python and dependencies"
echo "================================================================"
export PYTHONUNBUFFERED=1
export PYTHONPATH=/scraper

python3 -m venv .venv
source .venv/bin/activate
.venv/bin/python3 -m pip install --upgrade pip
.venv/bin/python3 -m pip install -r /home/headless/app/requirements.txt

echo "================================================================"
echo "Setting up Chrome"
echo "================================================================"

export CHROME_USER_AGENT="${Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36}"
export CHROME_DRIVER=/usr/local/bin/chromedriver

echo -n 'Starting '; google-chrome --version
echo    "User agent: $CHROME_USER_AGENT"
echo    "Logging to: $(pwd)/chrome.log"
echo -n "Driver: "; ls -l $CHROME_DRIVER || echo "ERROR: Driver is missing"
echo    "VNC Password: headless"

echo "================================================================"
echo "Starting server"
echo "================================================================"
echo "Starting server on port $PORT"
.venv/bin/python3 /home/headless/app/server.py --host=0.0.0.0 --port=$PORT

killall chromedriver
