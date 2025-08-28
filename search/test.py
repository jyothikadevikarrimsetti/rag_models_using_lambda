from openai import AzureOpenAI
import os
from dotenv import load_dotenv
load_dotenv("../injestion/config/.env")

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)
deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

def get_openai_embedding(text):
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

if __name__ == "__main__":
    text = "education of jimson"
    embedding = get_openai_embedding(text)
    print(embedding)