import argparse
import requests
import logging
import sys
import time
import random
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def setup_argparse():
    """
    Sets up the argument parser for the command-line interface.
    """
    parser = argparse.ArgumentParser(description="Simulates form flood attacks to test rate limiting and resource exhaustion.")
    parser.add_argument("url", help="The URL of the target form.")
    parser.add_argument("-d", "--data", help="The data to be sent in the form (e.g., 'field1=value1&field2=value2').", required=True)
    parser.add_argument("-n", "--num_requests", type=int, default=100, help="The number of requests to send (default: 100).")
    parser.add_argument("-t", "--delay", type=float, default=0, help="Delay in seconds between requests (default: 0).")
    parser.add_argument("-r", "--randomize_data", action="store_true", help="Randomize data values in each request to bypass simple rate limiting.")
    parser.add_argument("-u", "--user_agent", type=str, default="VulnFormFloodSimulator/1.0", help="Custom User-Agent header to use. (default: VulnFormFloodSimulator/1.0)")
    parser.add_argument("-x", "--proxy", type=str, help="Proxy server to use (e.g., http://proxy.example.com:8080).")
    parser.add_argument("-H", "--header", type=str, action='append', help="Custom headers to include (e.g., 'Content-Type: application/json'). Can be specified multiple times.", default=[])
    parser.add_argument("--timeout", type=int, default=10, help="Timeout in seconds for each request. (default: 10)")
    parser.add_argument("--max-requests", type=int, default=1000, help="Ceiling on the number of requests in one run (default: 1000). Raise it explicitly to run a larger simulation; -n above the ceiling is refused.")
    
    return parser.parse_args()

def validate_url(url):
    """
    Validates the given URL.
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def randomize_form_data(data):
    """
    Randomizes form data values to bypass simple rate limiting.
    """
    data_parts = data.split('&')
    randomized_parts = []
    for part in data_parts:
        # A field with no '=' is a field with an empty value, not a crash.
        key, _, value = part.partition('=')
        # Simple randomization: append a random number to the value. Every
        # field gets one, including fields whose value was meant to stay
        # fixed, like a form type marker. There is no way to exempt one.
        random_value = value + str(random.randint(1000, 9999))
        randomized_parts.append(f"{key}={random_value}")
    return '&'.join(randomized_parts)

def main():
    """
    Main function to simulate form flood attacks.
    """
    args = setup_argparse()

    # Input validation
    if not validate_url(args.url):
        logging.error("Invalid URL provided.")
        sys.exit(1)

    if args.num_requests <= 0:
        logging.error("Number of requests must be a positive integer.")
        sys.exit(1)

    if args.delay < 0:
        logging.error("Delay must be a non-negative number.")
        sys.exit(1)

    if args.max_requests <= 0:
        logging.error("The --max-requests ceiling must be a positive integer.")
        sys.exit(1)

    if args.num_requests > args.max_requests:
        logging.error(f"Refusing to send {args.num_requests} requests: the ceiling for one run is {args.max_requests}. Raise it with --max-requests if that count is really intended.")
        sys.exit(1)

    # Prepare proxies
    proxies = {}
    if args.proxy:
        proxies = {'http': args.proxy, 'https': args.proxy}

    # Prepare headers
    headers = {'User-Agent': args.user_agent}
    # Custom headers are applied after the defaults, so a -H User-Agent
    # replaces mine instead of sending both. Same for Content-Type.
    for header in args.header:
      try:
        key, value = header.split(':', 1)
        headers[key.strip()] = value.strip()
      except ValueError:
        logging.warning(f"Invalid header format: {header}. Skipping.")

    # Start the attack simulation
    logging.info(f"Starting form flood simulation against: {args.url}")
    logging.info(f"Sending {args.num_requests} requests with a delay of {args.delay} seconds.")

    tally = {"accepted": 0, "rate_limited": 0, "rejected": 0, "server_error": 0, "failed": 0}
    interrupted = False
    try:
        for i in range(args.num_requests):
            try:
                # Randomize data if requested
                data_to_send = args.data
                if args.randomize_data:
                    data_to_send = randomize_form_data(args.data)

                # Send the request
                response = requests.post(args.url, data=data_to_send, headers=headers, proxies=proxies, timeout=args.timeout)

                # Tally the response class: this tally is the point of the
                # tool, since it is what rate limiting looks like in numbers.
                if response.status_code == 429:
                    tally["rate_limited"] += 1
                elif 200 <= response.status_code < 300:
                    tally["accepted"] += 1
                elif 400 <= response.status_code < 500:
                    tally["rejected"] += 1
                elif response.status_code >= 500:
                    tally["server_error"] += 1
                # A 3xx answer lands in no bucket at all. It was sent and
                # answered, but the answered total below leaves it out, so
                # a redirecting form makes the summary undercount quietly.

                # Log the response status code
                logging.info(f"Request {i+1}: Status Code = {response.status_code}")

                if response.status_code >= 400:
                    logging.warning(f"Request {i+1}: Received error status code {response.status_code}")

                # Introduce delay. The sleep sits inside the success path,
                # so a request that raises gets no delay before the next
                # attempt, and the last request still sleeps before ending.
                time.sleep(args.delay)

            except requests.exceptions.RequestException as e:
                tally["failed"] += 1
                logging.error(f"Request {i+1}: An error occurred - {e}")

    except KeyboardInterrupt:
        interrupted = True
        logging.info("Attack simulation interrupted by user.")

    answered = tally["accepted"] + tally["rate_limited"] + tally["rejected"] + tally["server_error"]
    logging.info(
        "Summary: {sent} attempted, {answered} answered (accepted 2xx: {accepted}, "
        "rate limited 429: {rate_limited}, rejected 4xx: {rejected}, server error 5xx: "
        "{server_error}), {failed} failed to send.".format(
            sent=sum(tally.values()), answered=answered, **tally))

    if answered == 0:
        logging.error("Simulation did not complete: no request reached the target. No completed claim is reported.")
        sys.exit(1)

    if tally["rate_limited"]:
        logging.info(f"The target rate limited {tally['rate_limited']} of {answered} answered requests.")
    elif tally["accepted"] == answered:
        logging.info("The target accepted every request that reached it; no rate limiting was observed.")

    logging.info("Form flood simulation completed." + (" (interrupted early)" if interrupted else ""))

# Example usage
if __name__ == "__main__":
    main()