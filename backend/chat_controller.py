import logging

from query_processor import QueryProcessor
from document_retriever import DocumentRetriever
from result_ranker import ResultRanker
from response_builder import ResponseBuilder


logger = logging.getLogger(__name__)

EMPTY_QUESTION_MESSAGE = "Please enter a question."
UNCLEAR_QUESTION_MESSAGE = "Please enter a meaningful question."
NO_ANSWER_MESSAGE = (
    "I couldn't find that in the student information. "
    "Try rephrasing your question."
)


class ChatController:
    """Runs a question through the pipeline and returns the API's response shape.

    ask() always returns:
        {
            "answer": "<non-empty text>",
            "sources": [{"category": str, "title": str, "source": str}, ...]
        }

    It raises RuntimeError only when the database cannot be searched, which
    the API turns into a 503 message for the dashboard.
    """

    def __init__(self):
        self.query_processor = QueryProcessor()
        self.document_retriever = DocumentRetriever()
        self.result_ranker = ResultRanker(top_k=5)
        self.response_builder = ResponseBuilder()

    def ask(self, question):
        if not question or not question.strip():
            return self._reply(EMPTY_QUESTION_MESSAGE)

        processed_query = self.query_processor.preprocess(question)

        if not processed_query:
            return self._reply(UNCLEAR_QUESTION_MESSAGE)

        # Only the database search is treated as "database unavailable".
        # A bug in ranking or formatting should surface as a normal error.
        try:
            results = self.document_retriever.search(processed_query)
        except Exception as error:
            logger.exception("Searching the student database failed")
            raise RuntimeError("The chatbot database is unavailable.") from error

        top_results = self.result_ranker.get_top_k(results)

        response = self.response_builder.format(top_results)
        return self._normalize(response)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _reply(answer, sources=None):
        return {"answer": answer, "sources": sources or []}

    @staticmethod
    def _text(value):
        return "" if value is None else str(value).strip()

    @staticmethod
    def _read(item, name):
        if isinstance(item, dict):
            return item.get(name)
        return getattr(item, name, None)

    @classmethod
    def _normalize(cls, response):
        """Turn whatever ResponseBuilder returns into {"answer", "sources"}."""
        if isinstance(response, str):
            answer, sources = response, None
        else:
            answer = cls._read(response, "answer")
            sources = cls._read(response, "sources")

        answer = cls._text(answer) or NO_ANSWER_MESSAGE
        return cls._reply(answer, cls._normalize_sources(sources))

    @classmethod
    def _normalize_sources(cls, sources):
        if not isinstance(sources, (list, tuple)):
            return []

        normalized = []
        for item in sources:
            if item is None:
                continue
            if isinstance(item, str):
                normalized.append({"category": "", "title": item.strip(), "source": ""})
                continue
            normalized.append(
                {
                    "category": cls._text(cls._read(item, "category")),
                    "title": cls._text(cls._read(item, "title")),
                    "source": cls._text(cls._read(item, "source")),
                }
            )
        return normalized