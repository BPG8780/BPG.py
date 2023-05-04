import requests
import time
import hashlib
import hmac
import urllib.parse
import json
import websocket
import getpass

# Get API key and secret key from user input
api_key = getpass.getpass(prompt="Enter your API Key: ")
secret_key = getpass.getpass(prompt="Enter your Secret Key: ")

base_url = 'https://fapi.binance.com'
symbol = 'BTCUSD_210625'

def generate_signature(params):
    query_string = '&'.join(["{}={}".format(d, params[d]) for d in params])
    return hmac.new(secret_key.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

def get_headers(querystring):
    headers = {
        'X-MBX-APIKEY': api_key,
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    return headers

def get_mark_price(symbol):
    endpoint = '/fapi/v1/premiumIndex'
    url = f'{base_url}{endpoint}?symbol={symbol}'
    response = requests.get(url, headers=get_headers({}))
    return response.json()

def create_order(symbol, side, quantity, price):
    endpoint = '/fapi/v1/order'
    params = {
        'symbol': symbol,
        'side': side,
        'type': 'LIMIT',
        'timeInForce': 'GTC',
        'quantity': quantity,
        'price': price,
        'recvWindow': 5000,
        'timestamp': int(time.time() * 1000)
    }
    signature = generate_signature(params)
    headers = get_headers({'signature': signature})
    url = f'{base_url}{endpoint}?{urllib.parse.urlencode(params)}&signature={signature}'
    response = requests.post(url, headers=headers)
    return response.json()

def on_open(ws):
    print('Connection opened')

    # Subscribe to price updates for U-contracts
    subscribe_msg = {
        'method': 'SUBSCRIBE',
        'params': [
            f'{symbol.lower()}@markPrice'
        ],
        'id': 1
    }
    ws.send(json.dumps(subscribe_msg))

def on_close(ws):
    print('Connection closed')

def on_message(ws, message):
    data = json.loads(message)
    if 'result' not in data:
        mark_price = float(data['p'])
        quantity = 10
        buy_price = round(mark_price * 0.95, 2) # Place order at 95% of current mark price
        order = create_order(symbol, 'BUY', quantity, buy_price)
        print(f"New Buy Order: {order}")
    
socket = f"wss://fstream.binance.com/ws"
ws = websocket.WebSocketApp(socket,
                            on_open=on_open,
                            on_close=on_close,
                            on_message=on_message)
ws.run_forever()
