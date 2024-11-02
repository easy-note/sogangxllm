import requests
from datetime import datetime
import json

def set_params(nx, ny):
    with open('apis/config.json', 'r', encoding="utf-8") as f:
        config = json.load(f)


    params = {
        "serviceKey": config['weather']['key'],
        "numOfRows": "10",
        "pageNo": "1",
        "dataType": "JSON", # get_current_date()
        "base_date": "20241102", # get_current_hour()
        "base_time": "1100",
        "nx": str(nx),
        "ny": str(ny)
    }

    return params

def get_current_date():
    current_date = datetime.now().date()
    return current_date.strftime("%Y%m%d")


def get_current_hour():
    now = datetime.now()
    if now.hour==0:
        base_time = "2330"
    else:
        pre_hour = now.hour-1
        if pre_hour<10:
            base_time = "0" + str(pre_hour) + "30"
        else:
            base_time = str(pre_hour) + "30"

    return base_time


def run(nx, ny):
    url = 'http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst'    
    params = set_params(nx, ny)

    response = requests.get(url, params = params)

    if response.status_code == 200:
        res = response.json()
    else:
        return {"error": f"Request failed with status code {response.status_code}"}

    target_categories = {"SKY", "TMP", "POP"}
    korean_categories = {"SKY": "하늘", "TMP": "기온", "POP": "강수확률"}
    fcst_values = {korean_categories[item["category"]]: item["fcstValue"] for item in res["response"]["body"]["items"]["item"] if item["category"] in target_categories}

    if (int(fcst_values['하늘']) <= 5): 
        fcst_values['하늘'] = "맑음"
    elif (int(fcst_values['하늘']) <= 8): 
        fcst_values['하늘'] = "구름 많음"
    else: 
        fcst_values['하늘'] = "흐림"
    
    fcst_values['기온'] = fcst_values['기온'] + "℃"
    fcst_values['강수확률'] = fcst_values['강수확률'] + "%"

    return fcst_values

if __name__ == "__main__":
    data = run(60,127)
    print(json.dumps(data, indent=4))