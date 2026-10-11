class ResponseBuilder:

    def format(self, results):
        try:
            if not results:
                return {
                    "answer": "No relevant information found.",
                    "sources": []
                }

            answer_parts = []
            sources = []

            for result in results:
                category = result["category"]
                title = result["title"]
                content = result["content"]
                source = result["source"]

                answer_parts.append(
                    f"[{category}] {title}\n{content}"
                )

                sources.append({
                    "category": category,
                    "title": title,
                    "source": source
                })

            return {
                "answer": "\n\n".join(answer_parts),
                "sources": sources
            }

        except Exception as e:
            print("Response building error:")
            print(e)

            return {
                "answer": "Unable to build response.",
                "sources": []
            }
