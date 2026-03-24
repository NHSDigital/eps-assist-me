"""Ragas metrics factory.

Configures and returns the 4 core evaluation metrics:
    - Faithfulness: Is the response grounded in the retrieved source context?
    - Answer Relevancy: Does the response actually answer the question asked?
    - Semantic Similarity: How close is the response to the expected reference answer?
    - Answer Correctness: Is the response factually correct?
"""

from langchain_aws import ChatBedrock
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_aws import BedrockEmbeddings
from ragas.metrics import (
    Faithfulness,
    ResponseRelevancy,
    SemanticSimilarity,
    AnswerCorrectness,
)

from evaluation.config import EVALUATOR_MODEL_ID, EVALUATOR_EMBEDDING_MODEL_ID, AWS_REGION


def get_evaluator_llm() -> LangchainLLMWrapper:
    """Create the LLM wrapper used by Ragas to judge responses."""
    bedrock_llm = ChatBedrock(
        model_id=EVALUATOR_MODEL_ID,
        region_name=AWS_REGION,
    )
    return LangchainLLMWrapper(bedrock_llm)


def get_evaluator_embeddings() -> LangchainEmbeddingsWrapper:
    """Create the embeddings wrapper used by Ragas for similarity metrics."""
    bedrock_embeddings = BedrockEmbeddings(
        model_id=EVALUATOR_EMBEDDING_MODEL_ID,
        region_name=AWS_REGION,
    )
    return LangchainEmbeddingsWrapper(bedrock_embeddings)


def get_metrics() -> list:
    """
    Return the 4 evaluation metrics.

    All are single-turn metrics that evaluate individual question->answer pairs.
    """
    llm = get_evaluator_llm()
    embeddings = get_evaluator_embeddings()

    # Is the response grounded in the retrieved source context?
    faithfulness = Faithfulness(llm=llm)

    # Does the response actually answer the question asked?
    relevancy = ResponseRelevancy(llm=llm, embeddings=embeddings)

    # How close is the response to the expected reference answer?
    similarity = SemanticSimilarity(embeddings=embeddings)

    # Is the response factually correct? (combines faithfulness + similarity)
    correctness = AnswerCorrectness(llm=llm, embeddings=embeddings)

    return [faithfulness, relevancy, similarity, correctness]
