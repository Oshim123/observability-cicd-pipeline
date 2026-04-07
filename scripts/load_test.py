import argparse
import json
import os
import time
import uuid 
import random
from datetime import datetime

# I had to run 'pip install requests' to make this part work
import requests

# I am not using a main function because I just want the script to run top-to-bottom
# My tutor said this is fine for simple scripts

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

# Checking if the user put in a negative number by mistake
if args.number_of_requests <= 0:
    print("You need to send more than 0 requests!")
    exit()

# Setting up the filename for the results
if args.output_csv:
    my_file_name = args.output_csv
else:
    # I'm just using the date and time so I don't overwrite my old tests
    now = datetime.now()
    date_string = now.strftime("%Y-%m-%d_%H-%M-%S")
    my_file_name = "test_results_" + date_string + ".csv"

# I searched how to make a folder if it doesn't exist yet
# This os.path stuff was the easiest way I found
folder_path = os.path.dirname(my_file_name)
if folder_path != "" and not os.path.exists(folder_path):
    os.makedirs(folder_path)

# Creating some empty lists to hold all the numbers I'm going to collect
all_the_latencies = []
status_code_list = {}
fail_count = 0

print("Connecting to: " + str(args.url))
print("Sending " + str(args.number_of_requests) + " requests now...")

# I am opening the file manually here
# I'm using f.write and adding commas myself because I find it easier to control
f = open(my_file_name, "w")
f.write("timestamp,req_id,latency_ms,status\n")

for i in range(args.number_of_requests):
    # I'm using a UUID here so every request has a totally unique name
    # I need this for my report so I can prove the server saw this specific request
    current_uuid = str(uuid.uuid4())
    
    # Recording the exact second I start the request
    start_point = time.time()
    
    # I'm putting the ID into the headers
    # My app.py script is programmed to look for these specifically
    headers_to_send = {
        "X-Request-Id": current_uuid,
        "X-Scenario": args.scenario,
        "X-Run-Id": args.run_id
    }

    try:
        # Actually hitting the website
        r = requests.get(args.url, timeout=args.timeout, headers=headers_to_send)
        code = r.status_code
    except Exception as e:
        # If the internet fails or the server is dead, I catch the error here
        code = "CONNECTION_ERROR"
        print("Request number " + str(i + 1) + " failed because: " + str(e))

    # Calculating the time difference
    end_point = time.time()
    how_long = (end_point - start_point) * 1000
    
    # Saving it to my list for the math later
    all_the_latencies.append(how_long)
    
    # Counting how many of each status code I get
    s_code = str(code)
    if s_code in status_code_list:
        status_code_list[s_code] = status_code_list[s_code] + 1
    else:
        status_code_list[s_code] = 1

    # I count it as a fail if it's an error or a 500 server crash
    if s_code == "CONNECTION_ERROR" or s_code.startswith("5"):
        fail_count = fail_count + 1

    # Manually writing the row with commas
    # I round the latency to 2 decimals so it doesn't look messy in Excel
    row_data = str(datetime.now()) + "," + current_uuid + "," + str(round(how_long, 2)) + "," + s_code + "\n"
    f.write(row_data)

    # I don't want to spam the server too fast so I sleep for a bit
    time.sleep(args.pace_ms / 1000.0)

# Always remember to close the file!
f.close()

# --- MATH SECTION ---
# I'm doing all of this manually because I don't want to rely on extra libraries

number_of_items = len(all_the_latencies)
sum_of_all = sum(all_the_latencies)
average_val = sum_of_all / number_of_items

# I need to sort the list to find the median and p95
sorted_list = sorted(all_the_latencies)

# The median is the middle one
mid_spot = int(number_of_items / 2)
median_val = sorted_list[mid_spot]

# I am calculating the 95th percentile (P95)
# This is for my evaluation to show the slowest 5% of users
# I'm just picking the index at 95% of the list length
p95_spot = int(number_of_items * 0.95)
if p95_spot >= number_of_items:
    p95_spot = number_of_items - 1
p95_val = sorted_list[p95_spot]

# Putting everything into a final dictionary
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

# If I need to save it as a JSON for the other scripts
if args.summary_json:
    json_file = open(args.summary_json, "w")
    json_file.write(json.dumps(final_results, indent=2))
    json_file.close()

# Print it out so I can see it in the console
print(json.dumps(final_results, indent=2))