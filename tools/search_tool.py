import os
import pandas as pd
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


def search(query, max_results=10):
    response = client.search(
        query=query,
        max_results=max_results
    )

    return response["results"]


def save_results(results, filename="database/backlink_sites.csv"):

    rows = []

    for r in results:

        rows.append({
            "Title": r.get("title"),
            "URL": r.get("url"),
            "Content": r.get("content", "")
        })

    df = pd.DataFrame(rows)

    df.to_csv(filename, index=False)

    print(f"\nSaved {len(df)} websites to {filename}")