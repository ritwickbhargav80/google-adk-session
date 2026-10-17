import json
import os
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient
from google import genai

PACKAGE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(PACKAGE_DIR / ".env")

mongo = MongoClient(os.environ["MONGODB_URI"])
db = mongo[os.environ["MONGODB_DATABASE"]]
collection = db[os.environ["MONGODB_COLLECTION"]]

client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])


with open(PACKAGE_DIR / "data" / "weekend_data.json", encoding="utf-8") as f:
    documents = json.load(f)


collection.delete_many({})

for doc in documents:
    text = (
        f"{doc['name']}. "
        f"{doc['category']} in {doc['location']}. "
        f"{doc['description']} "
        f"Budget: {doc['budget']}. "
        f"Best time: {doc['best_time']}. "
        f"Interests: {', '.join(doc['interests'])}."
    )

    response = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text,
    )

    doc["text"] = text
    if response and response.embeddings:
        doc["embedding"] = response.embeddings[0].values

    collection.insert_one(doc)

print(f"Inserted {len(documents)} documents.")