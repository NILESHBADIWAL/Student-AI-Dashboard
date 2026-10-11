import heapq


class ResultRanker:

    def __init__(self, top_k=100):
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
