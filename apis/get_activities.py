import re
import json
import urllib.request
import requests
from urllib.parse import quote

def set_params():
    with open('apis/config.json', 'r', encoding="utf-8") as f:
        config = json.load(f)
    
    client_id = config['naver']['id']
    client_secret = config['naver']['key']

    return client_id, client_secret

def get_area_name(area_code):
    with open('config.json', 'r', encoding="utf-8") as f:
        config = json.load(f)
        return config['area_code_map'][area_code]
    
def get_blog(area_name, keyword):
    client_id, client_secret = set_params()
    query = area_name + " " + keyword

    print(query)

    encText = quote(query)
    url = "https://openapi.naver.com/v1/search/blog?query=" + encText
    request = urllib.request.Request(url)
    request.add_header("X-Naver-Client-Id", client_id)
    request.add_header("X-Naver-Client-Secret", client_secret)

    response = urllib.request.urlopen(request)
    rescode = response.getcode()

    if rescode == 200:
        response_body = response.read()
        return json.loads(response_body.decode('utf-8'))
    else:
        raise Exception(f"Error Code: {rescode}")

def get_map(area_name, keyword):
    client_id, client_secret = set_params()
    query = area_name + " " + keyword
    url = f"https://openapi.naver.com/v1/search/local.json?query={query}" 

    params = {
        'display': 5,
        'sort':'comment'
    }

    headers = {
        'X-Naver-Client-Id' : client_id,
        'X-Naver-Client-Secret' : client_secret,
    }

    response = requests.get(url, params, headers = headers)
    # print(response.text)
    if response.status_code == 200:
        data = response.json()
        top5 = [re.sub(r"<.*?>", "", item['title']) for item in data['items']]
        return top5
    else:
        return {"error": f"Request failed with status code {response.status_code}"}

def run(area_name):
    food = get_map(area_name, "맛집")
    date = get_map(area_name, "명소")
    activity = get_map(area_name, "액티비티")
    
    return {"맛집": food, "명소": date, "액티비티": activity}

if __name__ == "__main__":
    print(run("마포"))
    print(run("강남"))
    print(run("종로"))