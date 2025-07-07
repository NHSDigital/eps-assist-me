# LLM
from langchain.embeddings.sentence_transformer import SentenceTransformerEmbeddings
from langchain_community.vectorstores import DuckDB

# LLM
from langchain_openai import AzureChatOpenAI
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

# QA chain
from langchain.chains import RetrievalQA
from langchain import hub
from langchain.prompts import PromptTemplate

import duckdb
import os


embedding_function = SentenceTransformerEmbeddings(model_name="all-mpnet-base-v2")

DB_PATH = "./eps_corpus.db"

if os.path.exists(DB_PATH):
    print(f"connecting to existing db ({DB_PATH})")
    conn = duckdb.connect(DB_PATH)
    vector_store = DuckDB(connection=conn, embedding=embedding_function)

else:
    # load into database
    raise Exception(f"db was not found ({DB_PATH})")


prompt = hub.pull("rlm/rag-prompt")

llm = AzureChatOpenAI(
    openai_api_version="2023-08-01-preview",
    azure_deployment="eps-assistant-model",
    callback_manager=CallbackManager([StreamingStdOutCallbackHandler()]),
    model="gpt-4",
)


question = """Are Rate Limits applied to the EPS for Dispenser API or any part thereof? If so, what are they and where do they apply, please?"""

prompt = PromptTemplate.from_template(
    """[INST]<<SYS>> You are an assistant for question-answering tasks relating to the Electronic Prescribing Services EPS API.
    Use the following pieces of retrieved context to answer the question.
    Rate limits apply to all APIs (e.g. EPS dispensing, EPS prescribing, PDS)
    If you don't know the answer, just say that you don't know. keep the answer concise and include technical references where possible
    code samples should be used to support the answer where appropriate.<</SYS>> \nQuestion: {question} \nContext: {context} \n  Answer: [/INST]"""
)

qa_chain = RetrievalQA.from_chain_type(
    llm,
    retriever=vector_store.as_retriever(),
    chain_type_kwargs={"prompt": prompt},
)

result = qa_chain.invoke(question)


print(result["result"])
