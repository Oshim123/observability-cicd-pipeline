import requests
import time
import statistics
import sys
import csv
from datetime import datetime
#these imports are used for making HTTP requests, measuring time, 
# calculating statistics, handling command-line arguments, writing to CSV files, and working with dates and times.

if len(sys.argv) != 3:
    #this checks if the user has provided the correct number of command-line arguments (the URL and the number of requests).
    print("Usage: python load_test.py <URL> <number_of_requests>")
    #this prints a usage message if the arguments are not provided correctly.
    sys.exit(1)
    #this exits the program with a non-zero status code, indicating an error.

url = sys.argv[1]
num_requests = int(sys.argv[2]) #converts the second command-line argument to an integer, which represents the number of requests to send.
#now we have the URL and the number of requests, we can proceed with the load testing.

latencies = [] #stores the latency of each request, which will be used to calculate statistics later.
status_counts = {} #count the no of occurrences so can calc % of the status codes returned by the server.
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") #unique filename so that we can keep track of different test runs and their results.
csv_filename = f"load_test_results_{timestamp}.csv" #this will be the name of the CSV file where we will save the results of the load test.

with open(csv_filename, mode='w', newline='') as csv_file:
    fieldnames = ['Request Number', 'Latency (ms)', 'Status Code']
    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    writer.writeheader() #this writes the header row to the CSV file.

    for i in range(num_requests):
        start_time = time.time() #record the start time of the request.

        try:
            response = requests.get(url, timeout=5) 
            #timeout ensures the request doesn't hang forever if the service crashes
            status_code = response.status_code #get the HTTP status code from the response.

        except requests.exceptions.RequestException as e:
            #this handles cases where the service is down, unreachable, or times out
            end_time = time.time()
            latency = (end_time - start_time) * 1000 #calculate latency even for failed requests to understand the behaviour under failure conditions.
            latencies.append(latency)
            #this will let the load test continue and record the latency even when the service is not responding, 
            # which is important for understanding the behaviour under failure conditions.
            status_code = "ERROR"
            status_counts[status_code] = status_counts.get(status_code, 0) + 1

            writer.writerow({
                'Request Number': i + 1,
                'Latency (ms)': latency,
                'Status Code': status_code
            })

            print(f"Request {i + 1} failed: {e}")
            continue
            #continue ensures the script keeps running even if one request fails

        end_time = time.time() #record the end time of the request.
        latency = (end_time - start_time) * 1000 #calculate latency in milliseconds.
        latencies.append(latency) #store the latency for later analysis.

        status_counts[status_code] = status_counts.get(status_code, 0) + 1 #update the count for this status code.

        writer.writerow({'Request Number': i + 1, 'Latency (ms)': latency, 'Status Code': status_code}) 
        #write the details of this request to the CSV file.

        time.sleep(0.05)
        #small delay between requests to simulate more realistic user traffic


#after all requests complete, calculate summary statistics for evaluation
if latencies:
    avg_latency = statistics.mean(latencies)
    min_latency = min(latencies)
    max_latency = max(latencies)

    print("\n--- Load Test Summary ---")
    print(f"Total Requests: {num_requests}")
    print(f"Average Latency: {avg_latency:.2f} ms")
    print(f"Minimum Latency: {min_latency:.2f} ms")
    print(f"Maximum Latency: {max_latency:.2f} ms")
    print(f"Status Code Distribution: {status_counts}")
    #these printed results help quickly observe performance and error behaviour
    #the CSV file will be used later in the dissertation evaluation chapter
