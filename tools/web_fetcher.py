
import requests
from typing import Dict, Any

def fetch_url_content(url: str) -> Dict[str, Any]:
    """
    Fetches and returns the text content of a given URL.
    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  

        # we will just focus on text content for now
        content_type = response.headers.get("content-type", "")
        if "text" not in content_type:
            return {"error": f"URL does not point to a text-based document (content-type: {content_type})"}

        return {
            "url": url,
            "content": response.text,
            "status_code": response.status_code
        }
    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to fetch URL: {str(e)}"}
