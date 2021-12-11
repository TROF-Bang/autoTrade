import time
import ccxt
import datetime
import pandas as pd
#prophet 불러옴
from fbprophet import Prophet, forecaster
import json
import requests

def get_target_price(ticker, k):
    """변동성 돌파 전략으로 매수 목표가 조회"""
    bnb_ohlcv = binance.fetch_ohlcv(ticker, timeframe='1d', limit=2)
    df = pd.DataFrame(bnb_ohlcv, columns=['datetime','open','high','low','close','volume'])
    df['datetime'] = pd.to_datetime(df['datetime'],unit='ms')
    df.set_index('datetime', inplace=True)
    target_price = df.iloc[0]['close'] + (df.iloc[0]['high'] - df.iloc[0]['low']) * k
    return target_price

def get_start_time(ticker):
    """시작 시간 조회"""
    bnb_ohlcv = binance.fetch_ohlcv(ticker, timeframe='1m', limit=1)
    df = pd.DataFrame(bnb_ohlcv, columns=['datetime','open','high','low','close','volume'])
    df['datetime'] = pd.to_datetime(df['datetime'],unit='ms')
    df.set_index('datetime', inplace=True)
    start_time = df.index[0]
    return start_time

def get_balance(ticker):
    """잔고 조회"""
    balances = binance.fetch_balances()
    for b in balances:
        if b['currency'] == ticker:
            if b['balance'] is not None:
                return float(b['balance'])
            else:
                return 0
    return 0

def get_current_price(ticker):
    """현재가 조회"""
    ticker = binance.fetch_ticker(ticker)
    return ticker['close']

def get_ma15(ticker):
    """15일 이동 평균선 조회"""
    bnb_ohlcv = binance.fetch_ohlcv(ticker, timeframe='1d', limit=15)
    df = pd.DataFrame(bnb_ohlcv, columns=['datetime','open','high','low','close','volume'])
    df['datetime'] = pd.to_datetime(df['datetime'],unit='ms')
    df.set_index('datetime', inplace=True)
    ma15 = df['close'].rolling(15).mean().iloc[-1]
    return ma15

# 손절가 함수
def get_sell_price(ticker, k):
    bnb_ohlcv = binance.fetch_ohlcv(ticker, timeframe='1d', limit=2)
    df = pd.DataFrame(bnb_ohlcv, columns=['datetime','open','high','low','close','volume'])
    df['datetime'] = pd.to_datetime(df['datetime'],unit='ms')
    df.set_index('datetime', inplace=True)
    sell_price = df.iloc[0]['close'] - (df.iloc[0]['high'] - df.iloc[0]['low']) * k
    return sell_price

# 로그인
binance = ccxt.binance()
print("autotrade start")
count_signul = 0
fee = 0.001
ror = 0
df_coin = 0
coin = "BNB/USDT"

# 자동매매 시작
while True:
    try:
        # 현재 시간 조회
        now = datetime.datetime.now()
        
        # 현재가 조회
        current_price = get_current_price(coin)
        
        if count_signul == 0:
                target_price = get_target_price(coin, 0.3)
                bnb_ohlcv = binance.fetch_ohlcv(coin, timeframe='1h', limit=1000)

                df = pd.DataFrame(bnb_ohlcv, columns=['datetime','open','high', 'low', 'close', 'volume'])
                df['datetime'] = pd.to_datetime(df['datetime'], unit='ms')

                df['ds'] = df['datetime']
                df['y'] = df['close']
                data = df[['ds','y']]

                model = Prophet()
                model.fit(data)

                future = model.make_future_dataframe(periods=50, freq='H')
                forecast = model.predict(future)

                df_coin = forecast['trend'][1049] - forecast['trend'][1000]

                if target_price < current_price and df_coin > 0:
                    print(now, '매수 신호', current_price)
                    ror += current_price / target_price - fee - 1
                    count_signul = 1
                    
                    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
                    headers = {"Authorization": "Bearer " + "2eXBtXGmRElxjNr42rLClzlSuZOGvJuuUtFxvworDSAAAAF9qYTPkQ"}
                    data = {"template_object" : json.dumps({ "object_type" : "text", 
                                                            "text" : "매수 신호 BTC : " + str(current_price),
                                                            "link" : {"web_url" : "https://www.google.co.kr/search?q=drone&source=lnms&tbm=nws",
                                                                      "mobile_web_url" : "https://www.google.co.kr/search?q=drone&source=lnms&tbm=nws"}
                                                           })
                           }

                    response = requests.post(url, headers=headers, data=data)
                    if response.json().get('result_code') == 0:
                        print('메시지를 성공적으로 보냈습니다.')
                    else:
                        print('메시지를 성공적으로 보내지 못했습니다. 오류메시지 : ' + str(response.json()))

        
        if count_signul == 1:
            sell_price = get_sell_price(coin, 0.3)
            
            bnb_ohlcv = binance.fetch_ohlcv(coin, timeframe='1h', limit=1000)

            df = pd.DataFrame(bnb_ohlcv, columns=['datetime','open','high', 'low', 'close', 'volume'])
            df['datetime'] = pd.to_datetime(df['datetime'], unit='ms')

            df['ds'] = df['datetime']
            df['y'] = df['close']
            data = df[['ds','y']]

            model = Prophet()
            model.fit(data)

            future = model.make_future_dataframe(periods=50, freq='H')
            forecast = model.predict(future)

            df_coin = forecast['trend'][1049] - forecast['trend'][1000]

        # 손절가 매도
            if sell_price > current_price and df_coin < 0:
                print(now, '손절 매도 신호 :', get_current_price(coin) / target_price)
                ror += current_price / target_price - fee - 1
                count_signul = 0

                url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
                headers = {"Authorization": "Bearer " + "2eXBtXGmRElxjNr42rLClzlSuZOGvJuuUtFxvworDSAAAAF9qYTPkQ"}
                data = {"template_object" : json.dumps({ "object_type" : "text", 
                                                        "text" : "매도 신호 BTC : " + str(current_price),
                                                        "link" : {"web_url" : "https://www.google.co.kr/search?q=drone&source=lnms&tbm=nws",
                                                                  "mobile_web_url" : "https://www.google.co.kr/search?q=drone&source=lnms&tbm=nws"}
                                                        })
                           }

                response = requests.post(url, headers=headers, data=data)
                if response.json().get('result_code') == 0:
                    print('메시지를 성공적으로 보냈습니다.')
                else:
                    print('메시지를 성공적으로 보내지 못했습니다. 오류메시지 : ' + str(response.json()))
        
        print('현재시간 : ', now)
        print('기울기 : ', df_coin)
        print('현재가 : ', current_price)
        
        if count_signul == 0:
            print('매수가 : ', target_price)
            print('수익율 : ', ror)
        else:
            print('매수가 : ', target_price)
            print('손절가 : ', sell_price)
            print('실시간 수익율 : ', ror + current_price / target_price - 1)
            print('수익율 : ', ror)
        
        time.sleep(10)
    except Exception as e:
        print(e)
        time.sleep(1)
