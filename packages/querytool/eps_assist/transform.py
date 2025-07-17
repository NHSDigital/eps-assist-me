import duckdb
import os
from pathlib import Path

from langchain.embeddings.sentence_transformer import SentenceTransformerEmbeddings
from langchain.docstore.document import Document
from langchain_community.vectorstores import DuckDB
from semantic_text_splitter import MarkdownSplitter
from tokenizers import Tokenizer

# Set up the base directory and paths
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "eps_corpus.db"
CORPUS_PATH = BASE_DIR / "docs"

# Toggle this flag to control DB rebuilding
REBUILD_DB = True

# Set up embeddings
embedding_function = SentenceTransformerEmbeddings(model_name="all-mpnet-base-v2")

# Set up splitter
tokenizer = Tokenizer.from_pretrained("bert-base-uncased")
splitter = MarkdownSplitter.from_huggingface_tokenizer(tokenizer)


def connect_to_existing_vector_store():
    print(f"connecting to existing db ({DB_PATH})")
    conn = duckdb.connect(DB_PATH)
    vector_store = DuckDB(connection=conn, embedding=embedding_function)
    return vector_store


def create_vector_store_file():
    print(f"creating new database ({DB_PATH})")

    conn = duckdb.connect(DB_PATH)
    vector_store = DuckDB(connection=conn, embedding=embedding_function)

    for file in os.listdir(CORPUS_PATH):
        file_path = CORPUS_PATH / file

        with open(file_path) as doc:
            doc_text = doc.read()

            print(f"splitting source document ({file_path})...")

            # if "scal_" in file_path:
            #    chunks = doc_text.split("SCAL requirement")
            # else:
            chunks = splitter.chunks(doc_text, chunk_capacity=(200, 1000))
            docs = [Document(page_content=chunk) for chunk in chunks]

            print(f"adding {len(docs)} documents to vector store...")
            vector_store.add_documents(docs)


if __name__ == "__main__":

    if REBUILD_DB and os.path.exists(DB_PATH):
        print(f"removing existing db file ({DB_PATH})")
        os.remove(DB_PATH)

    if os.path.exists(DB_PATH):
        vector_store = connect_to_existing_vector_store()
    else:
        create_vector_store_file()
        vector_store = connect_to_existing_vector_store()

    test_query = (
        "1.6.5 “For eRD prescriptions, the dispenser must see:\n"
        "• the current issue\n"
        "• the total number of authorised issues for both the prescription and line items on the prescription.\n"
        "There is nothing we can see at prescription level that defines the current issue or the number of "
        "authorised issues (we can only see it at MedicationRequest level)\n"
        "Eg: Prescription number: 8F4A22-C81007-000012"
    )

    results = vector_store.similarity_search(test_query)

    for result in results:
        print("*" * 100)
        print(result)

    exit()
