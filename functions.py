import requests
import os
import smtplib

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
GMAIL_ACCOUNT = os.environ.get("GMAIL_ACCOUNT")
GMAIL_PASSWORD = os.environ.get("GMAIL_PASSWORD")


# Send a Search Request for Place ID to Google Maps
def find_place_id(shop):
    search_params = {
        "key": GOOGLE_API_KEY,
        "input": f"Pret {shop}",
        "inputtype": "textquery",
        "fields": "place_id"
    }
    google_search_response = requests.get("https://maps.googleapis.com/maps/api/place/findplacefromtext/json",
                                          params=search_params)
    place_id = google_search_response.json()["candidates"][0]["place_id"]
    return place_id


def send_email(recipient, message):
    with smtplib.SMTP("smtp.gmail.com") as connection:
        connection.starttls()
        connection.login(GMAIL_ACCOUNT, GMAIL_PASSWORD)
        connection.sendmail(
            from_addr=GMAIL_ACCOUNT,
            to_addrs=recipient,
            msg=message)
