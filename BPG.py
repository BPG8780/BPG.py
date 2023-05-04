import asyncio
from binance.client import AsyncClient, BinanceSocketManager
from binance.enums import *
import talib
import numpy as np

# 修改此处的API密钥和其他参数
API_KEY = 'your_api_key'
API_SECRET = 'your_api_secret'
SYMBOL = 'BTCUSDT'
QUANTITY = 0.001 # 下单数量
MAX_POSITION = 0.1 # 最大持仓量，以BTC为单位

# 初始化变量
entry_price_long = None
entry_price_short = None
enabled = False
max_retries = 5
retries = 0
take_profit_price = None

# 分段显示的函数
def split_text(text, limit):
    chunks = []
    words = text.split()
    current_chunk = ""

    for word in words:
        if len(current_chunk + word) <= limit:
            current_chunk += word + " "
        else:
            chunks.append(current_chunk.strip())
            current_chunk = word + " "

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks

# 补仓或开仓
async def open_position(prices, ma):
    global retries, entry_price_long, entry_price_short
    
    position_info = await client.futures_position_information(symbol=SYMBOL)
    current_qty_long = float(position_info[0]["positionAmt"])
    current_qty_short = float(position_info[1]["positionAmt"])

    if current_qty_long == 0 and retries < max_retries and prices[-1] < ma[-1]:
        retries += 1
        await asyncio.sleep(60) # 等待一段时间再尝试补仓
        await open_position(prices, ma)
        
    if entry_price_long is None and entry_price_short is None and rsi[-1] > 70 and prices[-1] > ma[-1]:
        order_long = await client.futures_create_order(
            symbol=SYMBOL,
            side=SIDE_BUY,
            type=ORDER_TYPE_MARKET,
            quantity=QUANTITY,
            reduceOnly=True,
            positionSide=POSITION_SIDE_LONG)
        entry_price_long = prices[-1]

        order_short = await client.futures_create_order(
            symbol=SYMBOL,
            side=SIDE_SELL,
            type=ORDER_TYPE_MARKET,
            quantity=QUANTITY,
            reduceOnly=True,
            positionSide=POSITION_SIDE_SHORT)
        entry_price_short = prices[-1]
        retries = 0
    elif entry_price_long is not None and entry_price_short is not None:
        # 更新持仓信息和止损/止盈价格
        position_info = await client.futures_position_information(symbol=SYMBOL)
        current_qty_long = float(position_info[0]["positionAmt"])
        current_qty_short = float(position_info[1]["positionAmt"])
        stop_loss_price_long = entry_price_long * 0.98
        stop_loss_price_short = entry_price_short * 1.02

        if current_qty_long < MAX_POSITION and prices[-1] > ma[-1]:
            qty = QUANTITY
            order_long = await client.futures_create_order(
                symbol=SYMBOL,
                side=SIDE_BUY,
                type=ORDER_TYPE_MARKET,
                quantity=qty,
                reduceOnly=True,
                positionSide=POSITION_SIDE_LONG)
            entry_price_long = (entry_price_long * (qty - 0.001) + prices[-1] * 0.001) / qty

            order_short = await client.futures_create_order(
                symbol=SYMBOL,
                side=SIDE_SELL,
                type=ORDER_TYPE_MARKET,
                quantity=qty,
                reduceOnly=True,
                positionSide=POSITION_SIDE_SHORT)
            entry_price_short = (entry_price_short * (qty - 0.001) + prices[-1] * 0.001) / qty

        elif current_qty_short < MAX_POSITION and prices[-1] < ma[-1]:
            qty = QUANTITY
            order_short = await client.futures_create_order(
                symbol=SYMBOL,
                side=SIDE_BUY,
                type=ORDER_TYPE_MARKET,
                quantity=qty,
                reduceOnly=True,
                positionSide=POSITION_SIDE_SHORT)
            entry_price_short = (entry_price_short * (qty - 0.001) + prices[-1] * 0.001) / qty

            order_long = await client.futures_create_order(
                symbol=SYMBOL,
                side=SIDE_SELL,
                type=ORDER_TYPE_MARKET,
                quantity=qty,
                reduceOnly
            positionSide=POSITION_SIDE_LONG)
            entry_price_long = (entry_price_long * (qty - 0.001) + prices[-1] * 0.001) / qty

# 更新止损/止盈价格
if entry_price_long is not None:
    if take_profit_price is None or prices[-1] > take_profit_price:
        take_profit_price = entry_price_long * 1.02 # 2%的利润率作为止盈价
    elif prices[-1] < stop_loss_price_long:
        order_long = await client.futures_create_order(
            symbol=SYMBOL,
            side=SIDE_SELL,
            type=ORDER_TYPE_MARKET,
            quantity=current_qty_long,
            reduceOnly=True,
            positionSide=POSITION_SIDE_LONG)
        entry_price_long = None
        take_profit_price = None

if entry_price_short is not None:
    if take_profit_price is None or prices[-1] < take_profit_price:
        take_profit_price = entry_price_short * 0.98 # 2%的利润率作为止盈价
    elif prices[-1] > stop_loss_price_short:
        order_short = await client.futures_create_order(
            symbol=SYMBOL,
            side=SIDE_BUY,
            type=ORDER_TYPE_MARKET,
            quantity=current_qty_short,
            reduceOnly=True,
            positionSide=POSITION_SIDE_SHORT)
        entry_price_short = None
        take_profit_price = None

async def main():
    global enabled, entry_price_long, entry_price_short
    print("正在连接Binance WebSocket...")
    bsm = BinanceSocketManager(client)
    klines_socket = bsm.kline_futures_socket(SYMBOL, interval=KLINE_INTERVAL_1MINUTE)
    rsi_socket = bsm.kline_futures_socket(SYMBOL, interval=KLINE_INTERVAL_5MINUTE)

    # 订阅K线数据
    klines_buffer = []
    def process_klines_message(msg):
        nonlocal klines_buffer
        klines_buffer.append(float(msg['k']['c']))
        if len(klines_buffer) > 20:
            klines_buffer = klines_buffer[-20:]
        if len(klines_buffer) == 20:
            ma = talib.SMA(np.array(klines_buffer), timeperiod=20)
            asyncio.ensure_future(open_position(klines_buffer, ma))

    conn_key_klines = klines_socket.__enter__()
    klines_socket.subscribe(conn_key_klines, process_klines_message)

    # 订阅RSI指标数据
    rsi_buffer = []
    def process_rsi_message(msg):
        nonlocal rsi_buffer
        kline = msg['k']
        if len(rsi_buffer) and kline['t'] == rsi_buffer[-1]['t']:
            rsi_buffer[-1] = kline
        else:
            rsi_buffer.append(kline)
        if len(rsi_buffer) > 14:
            rsi_buffer = rsi_buffer[-14:]
        if len(rsi_buffer) == 14:
            closes = [float(x['c']) for x in rsi_buffer]
            rsi = talib.RSI(np.array(closes), timeperiod=14)[-1]
            if rsi > 70:
                enabled = True
            elif rsi < 30:
                enabled = False

    conn_key_rsi = rsi_socket.__enter__()
    rsi_socket.subscribe(conn_key_rsi, process_rsi_message)

    while True:
        await asyncio.sleep(1)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    client = AsyncClient(API_KEY, API_SECRET)
    loop.run_until_complete(main())                