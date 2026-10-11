import urllib.request
import json
import pandas as pd

api_key = "a36e0daf-61c0-43f1-bcea-564c19c621eb"

url = "https://api.quickcommerceapi.com/v1/search?q=milk&lat=12.9021&lon=77.6639&platform=BlinkIt"

request = urllib.request.Request(
    url,
    headers={"X-API-Key": api_key}
)

response = urllib.request.urlopen(request)

data = json.loads(response.read().decode())

products = data["data"]["products"]

df = pd.DataFrame(products)
# print(df.head())


popular_product = df.loc[df["rating_count"].idxmax(), "name"]
average_rating = df["rating"].mean()

print("-" * 40)
print("Most Popular Product:", popular_product)
print("Average Rating:", round(average_rating, 2))
print("Average Purchase Amount:", round(df["offer_price"].mean(), 2))
print(df[["name", "rating", "rating_count"]].sort_values(
    by="rating_count",
    ascending=False
))