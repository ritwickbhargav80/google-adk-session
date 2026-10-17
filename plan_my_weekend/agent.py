import os

from pymongo import MongoClient
from google import genai
from google.adk.agents import Agent


# -----------------------------
# MongoDB connection
# -----------------------------

mongo_client = MongoClient(os.environ["MONGODB_URI"])

db = mongo_client[os.environ["MONGODB_DATABASE"]]
knowledge_collection = db[os.environ["MONGODB_COLLECTION"]]


# -----------------------------
# Gemini client
# -----------------------------

gemini_client = genai.Client(
    api_key=os.environ["GOOGLE_API_KEY"]
)


# -----------------------------
# RAG tool
# -----------------------------

def search_weekend_knowledge(query: str) -> dict:
    """
    Search the MongoDB vector knowledge base for relevant
    activities, places and food recommendations.
    """

    # Convert the user's query into an embedding
    embedding_response = gemini_client.models.embed_content(
        model="gemini-embedding-001",
        contents=query,
    )

    if embedding_response and embedding_response.embeddings:
        query_embedding = embedding_response.embeddings[0].values
    else:
        query_embedding = []

    # Perform MongoDB Vector Search
    results = knowledge_collection.aggregate(
        [
            {
                "$vectorSearch": {
                    "index": "vector_index",
                    "path": "embedding",
                    "queryVector": query_embedding,
                    "numCandidates": 20,
                    "limit": 5,
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "name": 1,
                    "category": 1,
                    "location": 1,
                    "description": 1,
                    "budget": 1,
                    "best_time": 1,
                    "interests": 1,
                    "score": {
                        "$meta": "vectorSearchScore"
                    },
                }
            },
        ]
    )

    return {
        "results": list(results)
    }


# -----------------------------
# ADK Agent
# -----------------------------

root_agent = Agent(
    model="gemini-3.5-flash",
    name="weekend_planner",
    description="Plans personalized weekends using a MongoDB knowledge base.",
    instruction="""
You are Plan My Weekend, a personalized weekend planning assistant.

Your job is to create a practical weekend itinerary based on:

- location
- available days and times
- interests
- budget
- number of people

IMPORTANT:
Before making recommendations, ALWAYS use the
search_weekend_knowledge tool.

Use the retrieved MongoDB knowledge as the source of truth.

Do not invent activities, places, restaurants or cafes
that are not supported by the retrieved knowledge.

Consider the user's:
- location
- available time
- interests
- budget

Organize your response into:

1. Activities
2. Places to Visit
3. Food & Cafes
4. Suggested Timeline
5. Estimated Budget

For every recommendation, briefly explain why it matches
the user's preferences.

Keep the response practical and concise.
""",
    tools=[search_weekend_knowledge],
)