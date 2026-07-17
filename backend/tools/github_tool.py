from langchain_core.tools import tool
import requests


@tool(description="""
    Search GitHub repositories.
    """)
def search_github(query: str):
    try:

        url = "https://api.github.com/search/repositories"

        response = requests.get(
            url,
            params={
                "q": query,
                "sort": "stars",
                "order": "desc",
                "per_page": 10
            },
            timeout=15
        )

        response.raise_for_status()

        data = response.json()

        repos = []

        for repo in data.get("items", []):

            repos.append({
                "name": repo["name"],
                "full_name": repo["full_name"],
                "description": repo["description"],
                "stars": repo["stargazers_count"],
                "forks": repo["forks_count"],
                "language": repo["language"],
                "url": repo["html_url"],
                "updated": repo["updated_at"]
            })

        return {
            "success": True,
            "type": "github",
            "mode": "repository",
            "repositories": repos
        }

    except Exception as e:

        # return {
        #     "success": False,
        #     "message": str(e)
        # }
        return f"Github Error: {e}"