# Play Console – foreground service "location" declaration (DRAFT)

**Which task?** Pardal warns while driving, with sound and voice, about speed cameras,
average-speed (section) controls, traffic alerts and the speed limit, and gives route directions.
That has to keep working when the screen is off or the driver is using another app (e.g.
music).

**Why a foreground service of type location?** The warnings depend on the
current GPS position and speed, every second. Without a foreground service Android stops the
location updates and the driver misses warnings.

**User-started and visible:** the service only starts once the user opens the
app, continuously shows the "Pardal trip" notification and stops via that notification or the app.
No ACCESS_BACKGROUND_LOCATION: the app only requests location "while in use".

**Video (required):** a short recording (30–60 s): open app → start trip → to home screen /
another app → a warning sounds → "Pardal trip" notification visible → stop.
