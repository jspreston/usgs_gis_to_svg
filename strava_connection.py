import os
import datetime as dt

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
AUTH_URL = f"http://www.strava.com/oauth/authorize?client_id={STRAVA_CLIENT_ID}&response_type=code&redirect_uri=http://localhost/exchange_token&approval_prompt=force&scope={';'.join(scope)}"

auth_code = input(
    "Go to the following URL; it will redirect you to a Not Found page, but "
    "copy the 'code=' portion of the URL here.\n\nURL:" + AUTH_URL + "\code="
)

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
after = str(int(dt.datetime(year=2020, month=5, day=1).timestamp()))
params = {
    "before": before,
    "after": after,
    "page": 1,
    "per_page": 30,
}
headers = {"Authorization": f"Bearer {access_token}"}
r = requests.get(
    "https://www.strava.com/api/v3/athlete/activities",
    params=params,
    headers=headers,
)
if not r.ok:
    print(r.text)
    r.raise_for_status()
    
activity_list = r.json()

full_activities = []
for activity in activity_list:
    print(f"retrieving {activity['name']} ({activity['start_date']})...")
    activity_id = activity["id"]
    r = requests.get(
        f"https://www.strava.com/api/v3/activities/{activity_id}",
        headers=headers,
    )
    if not r.ok:
        print(r.text)
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
