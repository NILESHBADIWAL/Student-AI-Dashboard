import re


class QueryProcessor:

    def __init__(self):
        self.stopwords = {
            "what", "is", "the", "a", "an", "are", "of", "for",
            "to", "in", "on", "and", "or", "can", "i", "my", "me",
            "how", "do", "does", "tell", "please", "give", "show",
            "about", "available", "details", "information"
        }

    def preprocess(self, question):
        try:
            if not question:
                return ""

            question = question.lower()

            question = re.sub(
                r"[^a-zA-Z0-9\s]",
                " ",
                question
            )

            words = question.split()

            words = [
                word for word in words
                if word not in self.stopwords
            ]

            return " ".join(words)

        except (AttributeError, TypeError) as e:
            print("Query processing error:")
            print(e)
            return ""
