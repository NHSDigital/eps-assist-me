import duckdb
import os

from langchain.embeddings.sentence_transformer import SentenceTransformerEmbeddings
from langchain.docstore.document import Document
from langchain_community.vectorstores import DuckDB
from semantic_text_splitter import MarkdownSplitter
from tokenizers import Tokenizer

tokenizer = Tokenizer.from_pretrained("bert-base-uncased")
splitter = MarkdownSplitter.from_huggingface_tokenizer(tokenizer)

embedding_function = SentenceTransformerEmbeddings(model_name="all-mpnet-base-v2")

DB_PATH = "./eps_corpus.db"
CORPUS_PATH = "./querytool/eps_assist/docs/"


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

        file_path = f"{CORPUS_PATH}{file}"

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

    # normally we just want to recreate the file, remove this if you want to test queries
    if True and os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    if os.path.exists(DB_PATH):
        vector_store = connect_to_existing_vector_store()
    else:
        create_vector_store_file()
        vector_store = connect_to_existing_vector_store()

    results = vector_store.similarity_search(
        """1.6.5 “For eRD prescriptions, the dispenser must see:
• the current issue
• the total number of authorised issues for both the prescription and line items on the prescription.
There is nothing we can see at prescription level that defines the current issue or the number of authorised issues (we can only see it at MedicationRequest level) Eg: Prescription number: 8F4A22-C81007-000012"""
    )

    for result in results:
        print("*" * 100)
        print(result)

    exit()
