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
        key, value = part.split('=', 1)
        # Simple randomization: append a random number to the value
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

    # Prepare proxies
    proxies = {}
    if args.proxy:
        proxies = {'http': args.proxy, 'https': args.proxy}

    # Prepare headers
    headers = {'User-Agent': args.user_agent}
    for header in args.header:
      try:
        key, value = header.split(':', 1)
        headers[key.strip()] = value.strip()
      except ValueError:
        logging.warning(f"Invalid header format: {header}. Skipping.")

    # Start the attack simulation
    logging.info(f"Starting form flood simulation against: {args.url}")
    logging.info(f"Sending {args.num_requests} requests with a delay of {args.delay} seconds.")

    try:
        for i in range(args.num_requests):
            try:
                # Randomize data if requested
                data_to_send = args.data
                if args.randomize_data:
                    data_to_send = randomize_form_data(args.data)

                # Send the request
                response = requests.post(args.url, data=data_to_send, headers=headers, proxies=proxies, timeout=args.timeout)

                # Log the response status code
                logging.info(f"Request {i+1}: Status Code = {response.status_code}")

                # Check for errors (status code >= 400)
                if response.status_code >= 400:
                    logging.warning(f"Request {i+1}: Received error status code {response.status_code}")

                # Introduce delay
                time.sleep(args.delay)

            except requests.exceptions.RequestException as e:
                logging.error(f"Request {i+1}: An error occurred - {e}")

    except KeyboardInterrupt:
        logging.info("Attack simulation interrupted by user.")

    logging.info("Form flood simulation completed.")

# Example usage
if __name__ == "__main__":
    main()