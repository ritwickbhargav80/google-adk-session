from google import genai
from dotenv import load_dotenv
from pathlib import Path
import os

PACKAGE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(PACKAGE_DIR / '.env')

c=genai.Client(api_key=os.environ['GOOGLE_API_KEY'])
r=c.models.embed_content(model='gemini-embedding-001', contents='test')

if r and r.embeddings:
    values = r.embeddings[0].values
    if values is not None:
        print(len(values))