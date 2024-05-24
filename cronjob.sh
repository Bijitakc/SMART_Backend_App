#!/bin/bash

while true; do
    # Get the current datetime
    current_time=$(date +"%Y-%m-%d %H:%M:%S")
    # Send a GET request to the endpoint, log the current datetime, the response, and add a new line
    echo "Datetime: $current_time" >> /app/cronjob.log
    echo "Response:" >> /app/cronjob.log
    curl -X GET http://flask:5000/send_email >> /app/cronjob.log
    echo "" >> /app/cronjob.log
    sleep 86400
done
