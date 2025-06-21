key = 'qJpvzuqAMY9uUu57MC1qoccXcveUD5MU'

import requests
import json

# Basic GET request
response = requests.get(f'https://app.ticketmaster.com/discovery/v2/events.json?keyword=music&countryCode=CZ&apikey={key}')

# Check if request was successful
if response.status_code == 200:
    data = response.json()  # Parse JSON response
    print(data)

    with open('ticketmaster_events.json', 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=4, ensure_ascii=False)
else:
    print(f"Error: {response.status_code}")