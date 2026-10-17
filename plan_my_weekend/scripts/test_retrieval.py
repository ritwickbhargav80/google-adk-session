from pymongo import MongoClient
from google import genai
from pathlib import Path
from dotenv import load_dotenv
import os

PACKAGE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(PACKAGE_DIR / '.env')

mongo = MongoClient(os.environ["MONGODB_URI"])

db = mongo[os.environ["MONGODB_DATABASE"]]
collection = db[os.environ["MONGODB_COLLECTION"]]

client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

query = "I want a good sunset photography place in Jaipur"

response = client.models.embed_content(
    model="gemini-embedding-001",
    contents=query,
)

if response and response.embeddings:
    query_embedding = response.embeddings[0].values
else:
    query_embedding = []

results = collection.aggregate([
    {
        "$vectorSearch": {
            "index": "vector_index",
            "path": "embedding",
            "queryVector": query_embedding,
            "numCandidates": 20,
            "limit": 3,
        }
    },
    {
        "$project": {
            "_id": 0,
            "name": 1,
            "category": 1,
            "description": 1,
            "budget": 1,
            "best_time": 1,
            "score": {"$meta": "vectorSearchScore"},
        }
    }
])

for result in results:
    print(result)