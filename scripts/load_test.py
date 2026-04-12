import argparse
import json
import os
import time
import uuid 
import random
from datetime import datetime

# chose these imports because I need to handle HTTP requests, 
# work with JSON data for the summary, and manage file paths for the CSV output.
# I also need uuid to tag every single request with a unique ID for traceability.
import requests

# I decided to let this script run top-to-bottom without a main function 
# because it's a dedicated utility script and this makes it easier to read the flow.

parser = argparse.ArgumentParser()
parser.add_argument("url")
parser.add_argument("number_of_requests", type=int)
parser.add_argument("--output-csv", default=None)
parser.add_argument("--summary-json", default=None)
parser.add_argument("--scenario", default="unknown")
parser.add_argument("--run-id", default="run0")
parser.add_argument("--pace-ms", type=int, default=50)
parser.add_argument("--timeout", type=float, default=5.0)

args = parser.parse_args()

# Checking if the number of requests is valid. 
# If it's 0 or negative, there is no point in running the test.
if args.number_of_requests <= 0:
    print("You need to send more than 0 requests!")
    exit()

# Setting up the CSV filename. 
# If no name is provided, I use a timestamp so I don't overwrite my previous test data.
if args.output_csv:
    my_file_name = args.output_csv
else:
    now = datetime.now()
    date_string = now.strftime("%Y-%m-%d_%H-%M-%S")
    my_file_name = "test_results_" + date_string + ".csv"

# Making sure the folder exists before I try to write the file. 
# This os.path check handles cases where the results directory isn't created yet.
folder_path = os.path.dirname(my_file_name)
if folder_path != "" and not os.path.exists(folder_path):
    os.makedirs(folder_path)

# initializing these lists and dicts to collect all the raw data points.
# I'll use these at the very end to do the statistical math.
all_the_latencies = []
status_code_list = {}
fail_count = 0

print("Connecting to: " + str(args.url))
print("Sending " + str(args.number_of_requests) + " requests now...")

# Opening the file manually and writing the header row.
# I like using f.write here because it gives me total control over the CSV format.
f = open(my_file_name, "w")
f.write("timestamp,req_id,latency_ms,status\n")

for i in range(args.number_of_requests):
    # generating a UUID for every single request so I can correlate 
    # these logs with the server-side logs in app_logs.json.
    current_uuid = str(uuid.uuid4())
    
    # capturing the exact start time to calculate round-trip latency.
    start_point = time.time()
    
    # injecting my custom headers so the Flask app knows which 
    # experiment and run these requests belong to.
    headers_to_send = {
        "X-Request-Id": current_uuid,
        "X-Scenario": args.scenario,
        "X-Run-Id": args.run_id
    }

    try:
        # actually making the request. 
        # I added a timeout so the script doesn't hang forever if the server crashes.
        r = requests.get(args.url, timeout=args.timeout, headers=headers_to_send)
        code = r.status_code
    except Exception as e:
        # catching connection errors here so the loop doesn't break if the service is down.
        code = "CONNECTION_ERROR"
        print("Request number " + str(i + 1) + " failed because: " + str(e))

    # Calculating the latency by finding the time difference and converting to milliseconds.
    end_point = time.time()
    how_long = (end_point - start_point) * 1000
    
    all_the_latencies.append(how_long)
    
    # updating the status code counts so I can see the distribution of 200s vs 500s.
    s_code = str(code)
    if s_code in status_code_list:
        status_code_list[s_code] = status_code_list[s_code] + 1
    else:
        status_code_list[s_code] = 1

    # I count it as a failure if it's a connection error or a server-side 5xx error.
    if s_code == "CONNECTION_ERROR" or s_code.startswith("5"):
        fail_count = fail_count + 1

    # writing the raw data to the CSV. 
    # rounding latency to 2 decimals to keep the file clean and readable.
    row_data = str(datetime.now()) + "," + current_uuid + "," + str(round(how_long, 2)) + "," + s_code + "\n"
    f.write(row_data)

    # sleeping for a bit so I don't overwhelm the server too quickly.
    time.sleep(args.pace_ms / 1000.0)

# making sure to close the file handle at the end.
f.close()

# --- MATH SECTION ---
# I decided to do these calculations manually to avoid adding 
# extra library dependencies like numpy or pandas.

number_of_items = len(all_the_latencies)
sum_of_all = sum(all_the_latencies)
average_val = sum_of_all / number_of_items

# I need to sort the list to find the median and the 95th percentile (P95).
sorted_list = sorted(all_the_latencies)

# finding the middle value for the median.
mid_spot = int(number_of_items / 2)
median_val = sorted_list[mid_spot]

# Calculating P95 to show the "tail latency" for the slowest 5% of requests.
# This is a key metric for observability reports.
p95_spot = int(number_of_items * 0.95)
if p95_spot >= number_of_items:
    p95_spot = number_of_items - 1
p95_val = sorted_list[p95_spot]

# gathering all the final metrics into a dictionary for the report.
final_results = {
    "target_url": args.url,
    "total_sent": number_of_items,
    "avg_ms": round(average_val, 2),
    "median_ms": round(median_val, 2),
    "p95_ms": round(p95_val, 2),
    "failed_requests": fail_count,
    "error_rate": str(round((fail_count / number_of_items) * 100, 2)) + "%",
    "all_codes": status_code_list
}

# If a summary path was provided, I save the dictionary as a JSON file.
# This is used by the experiment runner to aggregate all the results.
if args.summary_json:
    json_file = open(args.summary_json, "w")
    json_file.write(json.dumps(final_results, indent=2))
    json_file.close()

# printing the JSON to the terminal so I can see the results immediately.
print(json.dumps(final_results, indent=2))