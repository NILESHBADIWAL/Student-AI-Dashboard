import re
import heapq
import mysql.connector
from mysql.connector import Error


# ============================================================
# DATABASE CONFIGURATION
# ============================================================

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "samsunggalaxya13@@@!!",
    "database": "student_ai_dashboard"
}


# ============================================================
# DATABASE CLASS
# ============================================================

class Database:

    def __init__(self):
        self.connection = None

    def connect(self):

        try:

            self.connection = mysql.connector.connect(
                host=DB_CONFIG["host"],
                user=DB_CONFIG["user"],
                password=DB_CONFIG["password"],
                database=DB_CONFIG["database"]
            )

            if self.connection.is_connected():

                print("MySQL connected successfully!")

                return True

        except Error as e:

            print("MySQL connection error:")
            print(e)

        return False

    def get_connection(self):

        if (
            self.connection is None
            or not self.connection.is_connected()
        ):
            self.connect()

        return self.connection

    def close(self):

        try:

            if (
                self.connection
                and self.connection.is_connected()
            ):

                self.connection.close()

                print("MySQL connection closed.")

        except Error as e:

            print("Error closing MySQL connection:")
            print(e)


# ============================================================
# QUERY PROCESSOR
# ============================================================

class QueryProcessor:

    def __init__(self):

        self.stopwords = {
            "what",
            "is",
            "the",
            "a",
            "an",
            "are",
            "of",
            "for",
            "to",
            "in",
            "on",
            "and",
            "or",
            "can",
            "i",
            "my",
            "me",
            "how",
            "do",
            "does",
            "tell",
            "please",
            "give",
            "show"
        }

    def preprocess(self, question):

        try:

            if not question:
                return ""

            # Convert to lowercase
            question = question.lower()

            # Remove special characters
            question = re.sub(
                r"[^a-zA-Z0-9\s]",
                " ",
                question
            )

            # Split into words
            words = question.split()

            # Remove stopwords
            words = [
                word
                for word in words
                if word not in self.stopwords
            ]

            # Join words
            return " ".join(words)

        except (AttributeError, TypeError) as e:

            print("Query processing error:")
            print(e)

            return ""


# ============================================================
# DOCUMENT RETRIEVER
# ============================================================

class DocumentRetriever:

    def __init__(self):

        self.database = Database()

    def search(self, query):

        try:

            connection = self.database.get_connection()

            if connection is None:
                return []

            results = []

            cursor = connection.cursor(dictionary=True)

            search_value = "%" + query + "%"


            # =================================================
            # ATTENDANCE RULES
            # =================================================

            sql = """
                SELECT
                    rule_id AS id,
                    'Attendance Rules' AS category,
                    title,
                    content,
                    source,
                    1.0 AS score
                FROM attendance_rules
                WHERE title LIKE %s
                   OR content LIKE %s
            """

            cursor.execute(
                sql,
                (search_value, search_value)
            )

            results.extend(cursor.fetchall())


            # =================================================
            # FEES
            # =================================================

            sql = """
                SELECT
                    fee_id AS id,
                    'Fees' AS category,
                    fee_type AS title,
                    description AS content,
                    academic_year AS source,
                    1.0 AS score
                FROM fees
                WHERE branch LIKE %s
                   OR fee_type LIKE %s
                   OR description LIKE %s
            """

            cursor.execute(
                sql,
                (
                    search_value,
                    search_value,
                    search_value
                )
            )

            results.extend(cursor.fetchall())


            # =================================================
            # NOTICES
            # =================================================

            sql = """
                SELECT
                    notice_id AS id,
                    'Notice' AS category,
                    title,
                    content,
                    department AS source,
                    1.0 AS score
                FROM notices
                WHERE title LIKE %s
                   OR content LIKE %s
                   OR department LIKE %s
                ORDER BY notice_date DESC
            """

            cursor.execute(
                sql,
                (
                    search_value,
                    search_value,
                    search_value
                )
            )

            results.extend(cursor.fetchall())


            # =================================================
            # PYQs
            # =================================================

            sql = """
                SELECT
                    pyq_id AS id,
                    'PYQ' AS category,
                    subject_name AS title,
                    question AS content,
                    CONCAT(
                        year,
                        ' - ',
                        branch,
                        ' - Semester ',
                        semester
                    ) AS source,
                    1.0 AS score
                FROM pyqs
                WHERE subject_name LIKE %s
                   OR question LIKE %s
                   OR branch LIKE %s
                   OR subject_code LIKE %s
            """

            cursor.execute(
                sql,
                (
                    search_value,
                    search_value,
                    search_value,
                    search_value
                )
            )

            results.extend(cursor.fetchall())


            # =================================================
            # COURSES
            # =================================================

            sql = """
                SELECT
                    course_id AS id,
                    'Course' AS category,
                    course_name AS title,
                    description AS content,
                    course_code AS source,
                    1.0 AS score
                FROM courses
                WHERE course_name LIKE %s
                   OR description LIKE %s
                   OR course_code LIKE %s
                   OR branch LIKE %s
            """

            cursor.execute(
                sql,
                (
                    search_value,
                    search_value,
                    search_value,
                    search_value
                )
            )

            results.extend(cursor.fetchall())


            # =================================================
            # EXAM RULES
            # =================================================

            sql = """
                SELECT
                    rule_id AS id,
                    'Exam Rules' AS category,
                    title,
                    content,
                    source,
                    1.0 AS score
                FROM exam_rules
                WHERE title LIKE %s
                   OR content LIKE %s
            """

            cursor.execute(
                sql,
                (search_value, search_value)
            )

            results.extend(cursor.fetchall())


            # =================================================
            # FAQ
            # =================================================

            sql = """
                SELECT
                    faq_id AS id,
                    'FAQ' AS category,
                    question AS title,
                    answer AS content,
                    category AS source,
                    1.0 AS score
                FROM faqs
                WHERE question LIKE %s
                   OR answer LIKE %s
                   OR category LIKE %s
            """

            cursor.execute(
                sql,
                (
                    search_value,
                    search_value,
                    search_value
                )
            )

            results.extend(cursor.fetchall())


            # =================================================
            # LIBRARY RULES
            # =================================================

            sql = """
                SELECT
                    rule_id AS id,
                    'Library Rules' AS category,
                    title,
                    content,
                    source,
                    1.0 AS score
                FROM library_rules
                WHERE title LIKE %s
                   OR content LIKE %s
            """

            cursor.execute(
                sql,
                (search_value, search_value)
            )

            results.extend(cursor.fetchall())


            # =================================================
            # HOSTEL RULES
            # =================================================

            sql = """
                SELECT
                    rule_id AS id,
                    'Hostel Rules' AS category,
                    title,
                    content,
                    source,
                    1.0 AS score
                FROM hostel_rules
                WHERE title LIKE %s
                   OR content LIKE %s
            """

            cursor.execute(
                sql,
                (search_value, search_value)
            )

            results.extend(cursor.fetchall())


            cursor.close()

            return results

        except Exception as e:

            print("Document retrieval error:")
            print(e)

            return []


# ============================================================
# RESULT RANKER
# ============================================================

class ResultRanker:

    def __init__(self, top_k=5):

        self.top_k = top_k

    def get_top_k(self, results):

        try:

            if not results:
                return []

            return heapq.nlargest(
                self.top_k,
                results,
                key=lambda result: result["score"]
            )

        except Exception as e:

            print("Result ranking error:")
            print(e)

            return []


# ============================================================
# RESPONSE BUILDER
# ============================================================

class ResponseBuilder:

    def format(self, results):

        if not results:

            return {
                "answer": "No relevant information found.",
                "sources": []
            }


        answer_parts = []

        sources = []


        for result in results:

            category = result.get(
                "category",
                "Unknown"
            )

            title = result.get(
                "title",
                "Untitled"
            )

            content = result.get(
                "content",
                ""
            )

            source = result.get(
                "source",
                ""
            )


            answer_parts.append(
                f"[{category}] {title}\n{content}"
            )


            sources.append(
                {
                    "category": category,
                    "title": title,
                    "source": source
                }
            )


        answer = "\n\n".join(answer_parts)


        return {
            "answer": answer,
            "sources": sources
        }


# ============================================================
# CHAT CONTROLLER
# ============================================================

class ChatController:

    def __init__(self):

        self.query_processor = QueryProcessor()

        self.document_retriever = DocumentRetriever()

        self.result_ranker = ResultRanker(
            top_k=5
        )

        self.response_builder = ResponseBuilder()


    def ask(self, question):

        try:

            # ---------------------------------------------
            # Validate question
            # ---------------------------------------------

            if not question or not question.strip():

                return {
                    "answer": "Please enter a question.",
                    "sources": []
                }


            print("\n" + "-" * 60)

            print("Original question:")
            print(question)


            # ---------------------------------------------
            # Query Processing
            # ---------------------------------------------

            processed_query = (
                self.query_processor.preprocess(
                    question
                )
            )


            print("\nProcessed query:")
            print(processed_query)


            if not processed_query:

                return {
                    "answer":
                    "Please enter a meaningful question.",
                    "sources": []
                }


            # ---------------------------------------------
            # Document Retrieval
            # ---------------------------------------------

            results = (
                self.document_retriever.search(
                    processed_query
                )
            )


            print(
                "\nDocuments found:",
                len(results)
            )


            # ---------------------------------------------
            # Ranking
            # ---------------------------------------------

            top_results = (
                self.result_ranker.get_top_k(
                    results
                )
            )


            print(
                "Top results:",
                len(top_results)
            )


            # ---------------------------------------------
            # Build Response
            # ---------------------------------------------

            return self.response_builder.format(
                top_results
            )


        except Exception as e:

            print("\nChatController error:")
            print(e)

            return {
                "answer":
                "An error occurred while processing your question.",
                "sources": []
            }


# ============================================================
# MAIN PROGRAM
# ============================================================

def main():

    print("=" * 60)

    print(
        "              STUDENT AI DASHBOARD"
    )

    print("=" * 60)

    print(
        "Type 'exit' to stop the program."
    )


    # Create controller
    controller = ChatController()


    while True:

        print("\n")

        question = input(
            "Ask your question: "
        )


        # Exit
        if question.lower().strip() == "exit":

            print(
                "\nThank you for using Student AI Dashboard!"
            )

            break


        # Ask controller
        response = controller.ask(
            question
        )


        # ---------------------------------------------
        # DISPLAY ANSWER
        # ---------------------------------------------

        print("\n================ ANSWER ================")

        print(
            response["answer"]
        )


        # ---------------------------------------------
        # DISPLAY SOURCES
        # ---------------------------------------------

        print("\n================ SOURCES ================")


        if response["sources"]:

            for source in response["sources"]:

                print(
                    f"- {source['category']} | "
                    f"{source['title']} | "
                    f"{source['source']}"
                )

        else:

            print(
                "No sources found."
            )


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()