import os
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from loredata import ITEMS, CHARACTERS

PERSIST_DIR = "./dungeon_lore_db"
GOOGLE_API_KEY = os.environ["GOOGLE_API_KEY"]

def buildvectorstore():
    embeddings = GoogleGenerativeAIEmbeddings(
        model = "gemini-embedding-2",
        google_api_key=GOOGLE_API_KEY
    )

    db_exists = os.path.exists(PERSIST_DIR)

    vectorstore = Chroma(
        embedding_function=embeddings,
        persist_directory=PERSIST_DIR,
    )

    if not db_exists:
        item_texts = []
        item_metadats = []
        for item in ITEMS:
            item_texts.append(item["lore"])
            item_metadats.append({"id": item["id"], "type": "item", "name": item["name"]})

        char_texts = []
        char_metadatas = []
        for char in CHARACTERS:
            char_texts.append(char["backstory"])
            char_metadatas.append({"id": char["id"], "type": "character", "name": char["name"]})

        all_texts = item_texts + char_texts
        all_metadatas = item_metadats + char_metadatas

        vectorstore.add_texts(texts=all_texts, metadatas=all_metadatas)
        print("Vectorstore built and persisted.")
    else:
        print("Loaded existing vectorstore from disk.")

    return vectorstore

def querylore(vectorstore, query_text, k=1):
    results = vectorstore.similarity_search(query_text, k=k)
    if not results:
        return None
    return results[0].page_content

