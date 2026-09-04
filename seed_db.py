import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["ai_commerce"]
products_collection = db["products"]

# Load your local JSON
with open("products.json", "r") as file:
    data = json.load(file)

# Automatically adapt to the JSON format
docs = []
if isinstance(data, dict) and "products" in data:
    docs = data["products"]
elif isinstance(data, list):
    docs = data
elif isinstance(data, dict):
    for key, value in data.items():
        if isinstance(value, dict):
            value["_id"] = key
            docs.append(value)

# Insert into the live cloud database
if docs:
    collection.insert_many(docs)
    print(f"✅ Successfully inserted {len(docs)} products into MongoDB Atlas!")
else:
    print("⚠️ Could not find products to insert. Check your JSON format.")