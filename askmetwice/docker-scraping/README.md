## Scraping Container

A Docker container and Docker Compose file for a headful Chrome system that
is designed for running scrapers. Based on https://github.com/accetto/debian-vnc-xfce-g3

- **Owners**: @sammagid, @cguess
### Overview

### Key Features

- **Chromedriver**: The latest Chrome and Chromedriver is install when it's built
- **Python**: Python is installed along with a small amount of modules (Selenium, etc)
- **VNC**: From our base image we get both regular VNC and in-browser VNC

### Architecture

- Debian 12 (Bookworm)
    - x86 (Runnable on Apple M-series chips via Rosetta 2, built into Docker Desktop)
- Chrome (latest)
- Python 13

### Requirements

You have to be able to run Docker, if you're unsure, you're probably
the wrong audience for this. 

It'll run on any amd64-based OS, and Apple M-1 chips via Rosetta 2. 
Raspberry Pi's, or any other non-Apple ARM operating system Chromdriver 
will break on. It may be able to build for that, but this is only 
designed for servers, and so far x86/amd64 has won that battle... for now

### Quick Start

#### Using Docker

```bash
# 1) Clone and enter the project
git clone <REPO_URL>
cd <PROJECT_DIR>

# 2) Configure environment
cp .env.example .env     # then edit as needed

# 3) Build and run
docker compose up --build

# 4) Verify
curl http://localhost:<PORT>/  # expect: health or hello world
```

### Services and Endpoints

- **Base URL**: `http://localhost:<PORT>`
- **Endpoints**:
  - `GET /` — health or hello
  - `POST /scrape` — Start a test scrape with ChatGPT
  - `POST /scrape/chatgpt` - Start a test scrape with ChatGTPT
  - `POST /scrape/perplexity` - Start a test scrape with Perplexity` (not tested)
Example:
```bash
curl -X GET http://localhost:<PORT>/
```

### Troubleshooting

- **Entrypoint permission denied**
  - Ensure script has shebang (`#!/usr/bin/env bash`)
  - Ensure executable bit on host: `chmod +x path/to/entrypoint.sh`
  - If bind-mounting, exec bit must exist on host
  - Use `bash path/to/entrypoint.sh` in compose if needed
- **Chromedriver/Chrome mismatch**
  - Confirm versions: `google-chrome --version`, `chromedriver --version`
- **Port conflicts**
  - Change `PORT` or compose port mappings

### Security

- **Secrets**: Passwords and such are in the .env files (example at .evn.example)
- **Network**: Defaults
  - `5010` : The control server, access the site to kick off a scrape
  - `5901` : The VNC server to connect via TigerVNC or whatever
  - `6901` : The web-based VNC portal (no downloads needed), the password is `headless` (Lite is usually fine)
- **Dependencies**: 
  - Chrome / Chromedriver must always be in sync. The newest should be downloaded when
    this is built so just a requick rebuild should upgrade it all
  - Selenium should be brought up to date as soon as possible to keep up with Chrome
    which is why it's not pegged to a version in the `requirements.txt` file (none are right now but that's more of a "didn't get around to it thing")

### Deployment

- **Target**: Long running, either Kubernetes or Docker
- **Build**:
```bash
docker build -t <image>:<tag> .
```
- **Push**:
```bash
docker push <registry>/<image>:<tag>
```
- **Run**:
```bash
docker compose up
```

### Monitoring and Logging

_Not Implemented yet_

- **Logs**: Where to view (stdout, files, ELK, etc.)
- **Metrics**: What’s tracked and where
- **Alerts**: Thresholds and channels

### Roadmap

- [ ] Short‑term goals
- [ ] Medium‑term goals
- [ ] Long‑term goals

### Acknowledgements

- This is based on https://github.com/accetto/debian-vnc-xfce-g3