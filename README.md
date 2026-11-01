# vuln-Form-Flood-Attacks-Simulator

I use this to answer one question about a form I am allowed to test: when I send it a burst of submissions, where does it start pushing back? It posts the data you give it to the one URL you name (an optional proxy is also yours to name), and at the end it reports the tally that actually answers the question: how many requests were accepted (2xx), rejected (4xx), rate limited (429, counted on its own), answered with a server error (5xx), or failed to send at all.

If no request reaches the target, the run exits non-zero and does not claim completion. A run that a target rate limited perfectly and a run that a target accepted completely no longer look alike in the output.

There is a ceiling on one run: 1000 requests by default. A count above the ceiling is refused before anything is sent, so a typo in -n cannot turn into thousands of full speed posts. If you really mean a larger run, raise the ceiling on purpose with `--max-requests`.

## Install
`git clone https://github.com/ShadowGuard-AI/vuln-form-flood-attacks-simulator`

## Usage
`python main.py <url> -d <form-data> [params]`

Example: `python main.py http://127.0.0.1:8080/form -d "name=test&comment=hi" -n 50`

## Parameters
- `-h`: Show help message and exit
- `-d`: The data to send in the form (e.g., 'field1=value1&field2=value2'). Required.
- `-n`: Number of requests to send (default: 100).
- `-t`: Delay in seconds between requests (default: 0).
- `-r`: Randomize data values in each request. A field with no value is treated as an empty value.
- `-u`: Custom User-Agent header.
- `-x`: Proxy server to use.
- `-H`: Custom headers, can be given multiple times.
- `--timeout`: Timeout in seconds for each request (default: 10).
- `--max-requests`: Ceiling on requests in one run (default: 1000). -n above it is refused.

## License
Copyright (c) ShadowGuard-AI
