import requests

# One-off helper for local development.
print("seeding")
requests.get("http://localhost:8000/seed")
