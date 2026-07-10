import requests


BASE_URL = "https://blinkit.com/v1/layout/search"


class BlinkitAPI:

    def __init__(self):
        self.session = requests.Session()

    def search(self, query: str):

        response = self.session.post(
            BASE_URL,
            params={
                "q": query,
                "search_type": "auto_suggest"
            }
        )

        print(response.status_code)

        return response
