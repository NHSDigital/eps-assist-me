import duckdb
import os
from pathlib import Path

from langchain.embeddings.sentence_transformer import SentenceTransformerEmbeddings
from langchain_community.vectorstores import DuckDB
from langchain_community.chat_models import BedrockChat
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

# Load the model ID for Amazon Bedrock from
model_id = os.getenv("BEDROCK_MODEL_ID")
if not model_id:
    raise EnvironmentError("BEDROCK_MODEL_ID environment variable is not set.")

# Set up embeddings
embedding_function = SentenceTransformerEmbeddings(model_name="all-mpnet-base-v2")

# Connect to the local DuckDB vector store
DB_PATH = Path(__file__).resolve().parent / "eps_corpus.db"
if os.path.exists(DB_PATH):
    print(f"Connecting to existing db ({DB_PATH})")
    conn = duckdb.connect(DB_PATH)
    vector_store = DuckDB(connection=conn, embedding=embedding_function)

else:
    # Load into database
    raise FileNotFoundError(f"DB not found at ({DB_PATH})")

# Load Claude via Amazon Bedrock
llm = BedrockChat(
    model_id=model_id,
    callback_manager=CallbackManager([StreamingStdOutCallbackHandler()])
)

# Build the prompt
prompt = PromptTemplate.from_template(
    """[INST]<<SYS>> You are an assistant for question-answering tasks relating to the Electronic Prescribing
    Services EPS API. Use the following pieces of retrieved context to answer the question. Rate limits apply
    to all APIs (e.g. EPS dispensing, EPS prescribing, PDS). If you don't know the answer, just say that you
    don't know. Keep the answer concise and include technical references where possible. Code samples should
    be used to support the answer where appropriate.<</SYS>> \nQuestion: {question} \nContext: {context} \n
    Answer: [/INST]"""
)

# Create the Retrieval QA chain
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=vector_store.as_retriever(),
    chain_type_kwargs={"prompt": prompt}
)

# Define the question
question = (
    "Are Rate Limits applied to the EPS for Dispenser API or any part thereof? If so, what are they and "
    "where do they apply, please?"
)

# Run the chain
result = qa_chain.invoke(question)

# Output the result
print(result["result"])
