import os
import datetime as dt
import json
import time

import requests
# python implementation of Google’s Encoded Polyline Algorithm Format:
import polyline

STRAVA_CLIENT_ID = os.environ["STRAVA_CLIENT_ID"]
print(f"STRAVA_CLIENT_ID={STRAVA_CLIENT_ID}")
STRAVA_CLIENT_SECRET = os.environ["STRAVA_CLIENT_SECRET"]
print(f"STRAVA_CLIENT_SECRET={STRAVA_CLIENT_SECRET}")

# don't actually need the app access token
# app_access_token = input(
#     "visit https://www.strava.com/settings/api and enter the access "
#     "token found there: "
# )

# need read-all acess for activities to download tracks
scope = ["activity:read_all"]
AUTH_URL = (
    f"http://www.strava.com/oauth/authorize?client_id={STRAVA_CLIENT_ID}"
            "&response_type=code&redirect_uri=http://localhost/exchange_token&"
            f"approval_prompt=force&scope={';'.join(scope)}"
)

auth_code = input(
    "Go to the following URL; it will redirect you to a Not Found page, but "
    "copy the 'code=' portion of the URL here.\n\nURL:" + AUTH_URL + "\ncode="
)
print(f"auth code: {auth_code}")

payload = {
    "client_id": STRAVA_CLIENT_ID,
    "client_secret": STRAVA_CLIENT_SECRET,
    "code": auth_code,
    "grant_type": "authorization_code",
}
r = requests.post('https://www.strava.com/oauth/token', data=payload)
if not r.ok:
    print(r.text)
    r.raise_for_status()
access_token = r.json()["access_token"]

before = str(int(dt.datetime.now().timestamp()))
after = str(int(dt.datetime(year=2019, month=8, day=1).timestamp()))
params = {
    "before": before,
    "after": after,
    "page": -1,
    "per_page": 30,
}
headers = {"Authorization": f"Bearer {access_token}"}
page_idx = 1
activity_list = []
while True:
    params["page"] = page_idx
    print(f"getting page {page_idx} of activities")
    r = requests.get(
        "https://www.strava.com/api/v3/athlete/activities",
        params=params,
        headers=headers,
    )
    if not r.ok:
        print(r.text)
        r.raise_for_status()
    cur_activities = r.json()
    print(f"retrieved {len(cur_activities)} activities")
    if not cur_activities:
        break
    activity_list.extend(r.json())
    page_idx += 1

print(f"found total of {len(activity_list)} activities")
full_activities = []
for activity in activity_list:
    print(f"retrieving {activity['name']} ({activity['start_date']})...")
    activity_id = activity["id"]
    while True:  # keep trying on rate limit error
        r = requests.get(
            f"https://www.strava.com/api/v3/activities/{activity_id}",
            headers=headers,
        )
        if r.ok:
            break  # got a result, don't retry
        else:
            print(r.text)
            if r.status_code == 429:  # rate limit
                now = dt.datetime.now()
                minutes_till_reset = 15 - (now.minute % 15)
                print(
                    "got a rate limit timeout, sleeping for "
                    f"{minutes_till_reset} minutes"
                )
                time.sleep(minutes_till_reset*60)
            else:
                r.raise_for_status()

    full_activities.append(r.json())

with open('activities.json', 'w') as fp:
    json.dump(full_activities, fp, indent=4)
    
routes = [
    polyline.decode(activity["map"]["polyline"])
    for activity in full_activities
]
with open('routes.json', 'w') as fp:
    json.dump(routes, fp, indent=4)
