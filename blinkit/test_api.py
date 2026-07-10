from curl_cffi import requests

url = "https://blinkit.com/v1/layout/product/771901"

cookies = {
    'gr_1_deviceId': '2cd8fd3e-1a34-43fa-9419-1179a78ffbd0',
    'city': 'Diu',
    '_cfuvid': 'qQqk4bTfmR4YoZFoqvJQluZIbdkGxYL1HMeL7VD6RKk-1783695175.2771702-1.0.1.1-YKXChJrirFcXwVFs16bIjcdH26WpTAq_JIE1xpLLJFM',
    '_gid': 'GA1.2.600104375.1783695173',
    '_fbp': 'fb.1.1783695174149.843913447978989849',
    '_ga': 'GA1.2.516962137.1783695173',
    '_gcl_au': '1.2.1822092170.1783695173',
    'gr_1_lat': '18.6566489',
    'gr_1_lon': '73.80808689999999',
    'gr_1_locality': 'Pune',
    'gr_1_landmark': 'Shahunagar%2C%20MIDC%2C%20Chinchwad%2C%20Pimpri-Chinchwad%2C%20Maharashtra%20411019%2C%20India',
    '__cf_bm': 'ezJGN0y5kauUdejozv4Yi8sRA.1H7YawXCiPe9mpYaY-1783696397.8509915-1.0.1.1-VfeLFy_rfUGA7nNdfUfXpbnrfzEkeSuA911KCu0vLLTWs1J4LEE9BhJA3cnf0iDUzBHQn9amCxe5WUzgAv5nLEzvuvUK5AYOzGf2JTMmpcmhTk8b_nURnUBQMXDmtoSM',
    '_gat_UA-85989319-1': '1',
    '_ga_DDJ0134H6Z': 'GS2.2.s1783695174$o1$g1$t1783696419$j56$l0$h0',
    '_ga_JSMJG966C7': 'GS2.1.s1783695173$o1$g1$t1783696419$j56$l0$h0',
}

headers = {
    'accept': '*/*',
    'accept-language': 'en-US,en;q=0.9,hi;q=0.8',
    'access_token': 'null',
    'app_client': 'consumer_web',
    'app_version': '1010101011',
    'auth_key': 'c761ec3633c22afad934fb17a66385c1c06c5472b4898b866b7306186d0bb477',
    'content-type': 'application/json',
    'device_id': '434c884729a2826b',
    'dnt': '1',
    'is-response-compression-enabled': 'false',
    'lat': '18.6566489',
    'lon': '73.80808689999999',
    'origin': 'https://blinkit.com',
    'priority': 'u=1, i',
    'referer': 'https://blinkit.com/prn/hot-wheels-classic-tv-series-batmobile-die-cast-car/prid/771901',
    'rn_bundle_version': '1009003012',
    'sec-ch-ua': '"Not;A=Brand";v="8", "Chromium";v="150", "Google Chrome";v="150"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'session_uuid': 'ca60b8c9-9dab-485e-b88b-f0724d8e048e',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36',
    'web_app_version': '1008010016',
    'x-age-consent-granted': 'false',
}

response = requests.post(
    url,
    cookies=cookies,
    headers=headers,
    impersonate="chrome"
)

print("Status Code:", response.status_code)
print(response.text[:500])
