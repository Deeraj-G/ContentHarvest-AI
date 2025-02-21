import os

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from loguru import logger
from openai import OpenAI

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)


# Scrape the URL and return the HTML
def scrape_url(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        # Clean the text and limit length
        text = " ".join(soup.get_text().split())  # Remove extra whitespace
        text = text[:4000]  # Limit to 4000 characters
        return text
    except:
        return "Error fetching URL"


# Query to LLM to identify the relevant information based on the text
def identify_keywords(text: str):
    # Static keywords for now
    keywords = ["History", "Components", "Features"]

    examples = [
        {
            "History": "The history of the company is that it started in 1990 and is a software company.",
            "Components": "The components of the product are HTML, CSS, and JavaScript built on Monolithic architecture.",
            "Features": "The features of the product are that it is lightweight, fast, and scalable.",
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
    )

    response = response.json()

    return response["choices"][0]["message"]["content"]
