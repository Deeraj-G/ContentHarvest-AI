import os

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)


# Scrape the URL and return the text
# Scrape based on bolded words (these are the most important words)
def scrape_url(url: str) -> str:
    """
    This function scrapes a URL and returns the text.
    """
    try:
        response = requests.get(url, timeout=10)  # 10 second timeout
        soup = BeautifulSoup(response.text, "html.parser")
        # Clean the text and limit length
        text = " ".join(soup.get_text().split())  # Remove extra whitespace
        text = text[:4000]  # Limit to 4000 characters
        return text
    except Exception as e:
        return f"Error during web scraping: {e}"


# Query to LLM to identify the relevant information based on the text
def identify_keywords(text: str) -> str:
    """
    This function identifies the keywords in the text and returns the information associated with each keyword.
    """
    # Static keywords for now
    keywords = ["History", "Components", "Features"]

    examples = [
        {
            "History": "The history of the company is that it started in 1990 and is a software company.",
            "Components": "The components of the product are HTML, CSS, and JavaScript built on Monolithic architecture.",
            "Features": "The features of the product are that it is lightweight, fast, and scalable.",
        },
        {
            "Images": ["https://upload.wikimedia.org/wikipedia/commons/thumb/6/64/Dall-e_3_%28jan_%2724%29_artificial_intelligence_icon.png/200px-Dall-e_3_%28jan_%2724%29_artificial_intelligence_icon.png", "https://en.wikipedia.org/wiki/File:General_Formal_Ontology.svg"],
            "Links": ["https://en.wikipedia.org/wiki/Knowledge_engineering", "https://en.wikipedia.org/wiki/Markov_decision_process"],
            "Tags": ["h1", "h2", "h3", "h4", "h5", "h6"],
        }
    ]

    system_prompt = "You are a helpful assistant that identifies the information associated with given keywords."

    user_prompt = f"""
        Identify the information associate with each keyword: ```{keywords}``` from the following text: ```{text}```.
        Return the information in a json with the format: ```keyword: relevant_information```.
        Use the examples as a guide: {examples}
    """

    messages = [
        {"role": "user", "content": user_prompt},
        {"role": "system", "content": system_prompt},
    ]

    headers = {
        "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
        "Content-Type": "application/json",
    }

    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers=headers,
        json={"model": "gpt-3.5-turbo", "messages": messages},
        timeout=30  # 30 second timeout for AI response
    )

    response = response.json()

    return response["choices"][0]["message"]["content"]
