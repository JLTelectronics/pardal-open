# Pardal Privacy Statement (DRAFT)

*Last updated: [fill in date]*

Pardal is an open-source app that warns about speed cameras, traffic alerts and
speed limits, and that can navigate to a destination. There is no account, no
ads and no third-party tracking or analytics.

## Which data and what for

| Data | What for | Where it goes | How long |
|---|---|---|---|
| Your location (GPS) | Nearby warnings and limits, map, navigation | Stays on your device, except as below | – |
| Location + speed (every minute during use) | Fetching nearby reports, the "online" counter, checking that a reporter is really driving (against fake reports) | Pardal server | In memory only, a few minutes |
| A random device ID (hashed on the server) | One vote per device for reports | Pardal server | 90 days after your last use |
| Reports you make (type, location, direction of travel) | Sharing with other drivers | Pardal server, visible to everyone once 3 devices report the same thing | Up to a day after the report has expired |
| Search text when navigating | Finding an address or place | Pardal server, which searches at PDOK (Kadaster) and Photon (OpenStreetMap) **on behalf of the server** – they do not see your IP address | Not stored |
| Start and end point of a route | Calculating a route | Pardal server (its own route planner) | Not stored |
| IP address | Limiting abuse (one confirmation per internet connection) | Pardal server, hashed only (with a secret salt) | In memory; with a report or vote for as long as that report lasts (up to a day after it expires) |

The app also fetches public data without sharing your location or with only
a broad area: NDW traffic data, OpenStreetMap (Overpass) and PDOK sign maps.

## What we don't do
- No selling or sharing of data with advertisers or other parties.
- No trip history: where you have driven is not stored.
- Location in the background only while the trip is running (the "Pardal trip" notification is visible);
  you can always stop it.

## Your rights
Because there is no account, data is not linked to you as a person. If you want your
device ID forgotten right away, delete the app or the app's data, or email us.

## Contact
[fill in name / email address]

Source code: [link to the public repository, if one is published]
