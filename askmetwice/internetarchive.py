import requests
import time

def send_spn_request(access_key, secret_key, url):
    """
    Sends a URL-save request to the Internet Archive Save Page Now API.

    Args:
        access_key (str): Internet Archive S3-Like API access key (https://archive.org/account/s3.php).
        secret_key (str): Internet Archive S3-Like API secret key (https://archive.org/account/s3.php).
        url (str): URL to attempt to archive.
    
    Returns:
        requests.models.Response: Response object containing response code and text.
    """
    # API endpoint
    endpoint = "https://web.archive.org/save"

    # headers and data payload
    headers = {
        "Accept": "application/json",
        "Authorization": f"LOW {access_key}:{secret_key}"
    }
    data = {
        "url": url
    }

    # send POST request and handle a bunch of possible errors
    try:
        response = requests.post(endpoint, headers = headers, data = data, timeout = 30)
        response.raise_for_status()
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred in send_spn_request(): {http_err}.")
        return None
    except requests.exceptions.Timeout:
        print("Request timed out in send_spn_request().")
        return None
    except Exception as err:
        print(f"Other error occurred in send_spn_request(): {err}.")
        return None

    return response # None if error occurred

def retrieve_spn_url(access_key, secret_key, response, try_interval = 5, max_tries = 40):
    """
    Checks the status of an archive request several times (up to max_tries) and returns the
    archive.org URL if archive is successful. Note: given the various timeouts of SPN (see
    https://docs.google.com/document/d/1Nsv52MvSjbLb2PCpHlat0gkzw0EvtSgpKHu4mk0MnrA/), the
    product of try_interval and max_tries should be >= 3min to catch all successful archives.

    Args:
        access_key (str): Internet Archive S3-Like API access key (https://archive.org/account/s3.php).
        secret_key (str): Internet Archive S3-Like API secret key (https://archive.org/account/s3.php).
        response (requests.models.Response): Response generated from send_spn_request().
        try_interval (int): Number of seconds between status checks.
        max_tries (int): Number of times to try status check before failing.
    
    Returns:
        str: URL pointing to successful archive.org archive, or None if no success yet.
    """
    # if response from send_spn_request() was None, nothing to do
    if response is None:
        print("send_spn_request() returned None. Nothing to check.")
        return None
    
    # set headers with keys
    headers = {
        "Accept": "application/json",
        "Authorization": f"LOW {access_key}:{secret_key}"
    }

    # get status data, catch errors
    try:
        # extract status ID to build request url
        status_id = response.json()["job_id"]
        status_url = f"https://web.archive.org/save/status/{status_id}"

        for attempt in range(max_tries):
            r = requests.get(status_url, headers = headers, timeout = 30)
            r.raise_for_status()
            data = r.json()
            status = data["status"]
            if status == "success":
                # build the final archive URL
                archive_url = f"https://web.archive.org/web/{data["timestamp"]}/{data["original_url"]}"
                print(f"Successful archive at {archive_url}.")
                return archive_url
            # wait before the next try
            time.sleep(try_interval)
        # return None if maximum tries exceeded
        print(f"SPN Exceeded maximum tries. See status here: {status_url}.")
        return None
        
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred in send_spn_request(): {http_err}.")
        return None
    except requests.exceptions.Timeout:
        print("Request timed out in send_spn_request().")
        return None
    except Exception as err:
        print(f"Other error occurred in send_spn_request(): {err}.")
        return None

def save_page(access_key, secret_key, url):
    """
    Uses Internet Archive Save Page Now to archive a webpage and return its archive URL.

    Args:
        access_key (str): Internet Archive S3-Like API access key (https://archive.org/account/s3.php).
        secret_key (str): Internet Archive S3-Like API secret key (https://archive.org/account/s3.php).
        url (str): URL to attempt to archive.

    Returns:
        str: URL of successful archive, or None if failed.
    """
    print(f"Archiving URL: {url}")
    response = send_spn_request(access_key, secret_key, url)
    archive_url = retrieve_spn_url(access_key, secret_key, response)
    return archive_url