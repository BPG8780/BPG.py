# 获取用户余额信息
def get_account_balance(symbol):
    endpoint = "/fapi/v2/balance"
    header = create_header()
    params = create_params(symbol=symbol)
    url = create_url(endpoint)
    return get_request(url=url, headers=header, params=params)

# 获取K线数据
def get_klines(symbol, interval):
    endpoint = "/fapi/v1/klines"
    header = create_header()
    params = create_params(symbol=symbol, interval=interval)
    url = create_url(endpoint)
    return get_request(url=url, headers=header, params=params)

# 计算移动平均线
def calculate_ma(klines, period):
    closes = [float(kline[4]) for kline in klines[-period:]]
    return sum(closes) / len(closes)

# 定义趋势指标策略
def trend_indicator_strategy(symbol, interval):
    # 获取当前K线数据
    klines = get_klines(symbol=symbol, interval=interval)

    # 计算5日和20日移动平均线
    ma5 = calculate_ma(klines, 5)
    ma20 = calculate_ma(klines, 20)

    # 根据移动平均线确定交易方向
    if ma5 > ma20:
        side = "BUY"
    else:
        side = "SELL"

    # 下单交易
    quantity = 0.001
    price = float(klines[-1][4])
    order_type = "LIMIT"
    result = create_order(symbol=symbol, side=side, quantity=quantity, price=price, order_type=order_type)

    return result

# 定义顺势而为策略
def trend_following_strategy(symbol, interval):
    # 获取当前K线数据
    klines = get_klines(symbol=symbol, interval=interval)
    current_price = float(klines[-1][4])
    previous_price = float(klines[-2][4])

    # 根据价格变化确定交易方向
    if current_price > previous_price:
        side = "BUY"
    else:
        side = "SELL"

    # 下单交易
    quantity = 0.001
    price = current_price
    order_type = "LIMIT"
    result = create_order(symbol=symbol, side=side, quantity=quantity, price=price, order_type=order_type)

    return result

# 示例代码
if __name__ == "__main__":
    # 设置参数
    symbol = "BTCUSDT"
    interval = "1m"
    use_trend_indicator = True
    use_trend_following_strategy = True

    if use_trend_indicator:
        # 使用趋势指标策略
        trend_indicator_strategy(symbol=symbol, interval=interval)
    elif use_trend_following_strategy:
        # 使用顺势而为策略
        trend_following_strategy(symbol=symbol, interval=interval)
    else:
        # 不使用任何策略
        print("未开启任何策略")

    # 获取用户余额信息
    account_balance = get_account_balance(symbol=symbol)
    print(f"当前余额: {account_balance}")

    # 下单交易
    quantity = 0.001
    price = 50000
    order_type = "LIMIT"
    result = create_order(symbol=symbol, side="BUY", quantity=quantity, price=price, order_type=order_type)
    print(f"下单交易结果: {result}")

    # 撤销订单
    order_id = result["orderId"]
    cancel_result = cancel_order(symbol=symbol, order_id=order_id)
    print(f"撤销订单结果: {cancel_result}")