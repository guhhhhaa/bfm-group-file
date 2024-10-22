# 作者：千千量化
# 说明：这是一个曾经实盘月化3-5%以上的套利策略，策略特点：稳健、高收益、低风险、容量大。
# 关注微信公众号：千千的量化世界 回复：搬砖之王， 下载源代码，欢迎进群讨论
# 策略包含：三角套利、跨市双边、跨市三角。
# 需要熟悉无风险套利原理的朋友可以查看公众号内历史文章
# 无风险套利的核心是对下单细节的处理和执行速度的优化 这是猴版 视频中我会告诉大家哪里有提高空间
 
import ccxt       # 导入ccxt开源库，封装了各交易所rest api，通过 pip install ccxt安装
import time       # 导入time库，用于获取计时和定时睡眠
import logging    # 导入logging库，用于记录日志
import threading  # 导入threading库，用于多线程询价和下单

class MyThread(threading.Thread):   # 创建一个多线程调用类，便于后续进行多线程询价和下单
    def __init__(self,func,args=()):
        super(MyThread,self).__init__()
        self.func = func
        self.args = args

    def run(self):
        self.result = self.func(*self.args)

    def get_result(self):   # 这个方法用于返回多线程运行结果
        try:
            return self.result  # 如果子线程不使用join方法，此处可能会报没有self.result的错误
        except Exception as e:
            return e

class BanZhuanKing:   # 套利策略主类库
    def __init__(self, exchange_name,api_key,seceret_key,passphrase,check_box,ratio=0.5,fee_ratio_box=[1,1,1]):
        self.exchange_name = exchange_name   #存放交易所名称
        self.api_key = api_key  # 存放  apikey
        self.seceret_key= seceret_key  #存放 seceretkey
        self.passphrase = passphrase  #存放password
        self.check_box = check_box  #存放搜索的币对
        self.ratio = ratio   # 吃单比例不能为1，否则补单的时候需要溢价补单 ，钱不够就出错了
        self.fee_ratio_box = fee_ratio_box
        self.num = 0  #记录循环次数
        self.signal_num = 0  #记录发现开仓信号次数
        self.open_num  = 0  #记录开仓次数
        self.open_fail = 0  #记录下单错误次数
        self.maker_fail = 0   #记录补单次数（如果限价单下单后没有全部成交，则需要进行补单）
        self.error_num = 0  # 出错次数
        self.handle_open = 1 #是否处理未成交订单
        self.wait_time = 6  #每次下单后的等待时间，一般5~10秒
        self.win = {}   # 存储盈利信息
        self.win['BTC']  = 0
        self.win['USDT'] = 0
        self.version = 'V1.2.0'
        self.init_total = {}  # 存放初始币量

    def ChooseExchange(self):
        # 根据运行次数自动选择两个交易所进行套利机会检测 因为是先选交易所后进行rest询价
        # 升级方法：1、随机检查 2、根据套利机会出现频率动态调整 3、改成ws获取行情，同时检测全部交易所
        mode = self.num % 3
        if mode == 0:
            self.box = self.check_box[0]
            self.exchange_name_1 = self.exchange_name[0]
            self.exchange_name_2 = self.exchange_name[1]
            self.exchange_name_3 = self.exchange_name[2]
            self.api_key_1 = self.api_key[0]
            self.api_key_2 = self.api_key[1]
            self.api_key_3 = self.api_key[2]
            self.seceret_key_1 = self.seceret_key[0]
            self.seceret_key_2 = self.seceret_key[1]
            self.seceret_key_3 = self.seceret_key[2]
            self.passphrase_1 = self.passphrase[0]
            self.passphrase_2 = self.passphrase[1]
            self.passphrase_3 = self.passphrase[2]
            self.fee_ratio_1 = self.fee_ratio_box[0]
            self.fee_ratio_2 = self.fee_ratio_box[1]
        if mode == 1:
            self.box = self.check_box[1]
            self.exchange_name_1 = self.exchange_name[0]
            self.exchange_name_2 = self.exchange_name[2]
            self.exchange_name_3 = self.exchange_name[1]
            self.api_key_1 = self.api_key[0]
            self.api_key_2 = self.api_key[2]
            self.api_key_3 = self.api_key[1]
            self.seceret_key_1 = self.seceret_key[0]
            self.seceret_key_2 = self.seceret_key[2]
            self.seceret_key_3 = self.seceret_key[1]
            self.passphrase_1 = self.passphrase[0]
            self.passphrase_2 = self.passphrase[2]
            self.passphrase_3 = self.passphrase[1]
            self.fee_ratio_1 = self.fee_ratio_box[0]
            self.fee_ratio_2 = self.fee_ratio_box[2]
        if mode == 2:
            self.box = self.check_box[2]
            self.exchange_name_1 = self.exchange_name[1]
            self.exchange_name_2 = self.exchange_name[2]
            self.exchange_name_3 = self.exchange_name[0]
            self.api_key_1 = self.api_key[1]
            self.api_key_2 = self.api_key[2]
            self.api_key_3 = self.api_key[0]
            self.seceret_key_1 = self.seceret_key[1]
            self.seceret_key_2 = self.seceret_key[2]
            self.seceret_key_3 = self.seceret_key[0]
            self.passphrase_1 = self.passphrase[1]
            self.passphrase_2 = self.passphrase[2]
            self.passphrase_3 = self.passphrase[0]
            self.fee_ratio_1 = self.fee_ratio_box[1]
            self.fee_ratio_2 = self.fee_ratio_box[2]
        self.log.debug('====================')
        self.log.debug("eat ratio :%f" % self.ratio)
        self.log.debug("fee ratio 1 :%f" % self.fee_ratio_1)
        self.log.debug("fee ratio 2 :%f" % self.fee_ratio_2)
        self.log.debug("exchange1: %s" % self.exchange_name_1)
        self.log.debug("exchange2: %s" % self.exchange_name_2)
        self.log.debug(self.box)
        self.log.debug('====================')
        # 实例化ccxt
        exchange_name = self.exchange_name_1
        if exchange_name == 'okex': self.exchange_1 = ccxt.okex(
            {"apiKey": self.api_key_1, "secret": self.seceret_key_1, "password": self.passphrase_1})
        if exchange_name == 'okex3': self.exchange_1 = ccxt.okex3(
            {"apiKey": self.api_key_1, "secret": self.seceret_key_1, "password": self.passphrase_1})
        if exchange_name == 'huobi': self.exchange_1 = ccxt.huobipro(
            {"apiKey": self.api_key_1, "secret": self.seceret_key_1})
        if exchange_name == 'binance': self.exchange_1 = ccxt.binance(
            {"apiKey": self.api_key_1, "secret": self.seceret_key_1})
        if exchange_name == 'gateio': self.exchange_1 = ccxt.gateio(
            {"apiKey": self.api_key_1, "secret": self.seceret_key_1})
        if exchange_name == 'fcoin': self.exchange_1 = ccxt.fcoin(
            {"apiKey": self.api_key_1, "secret": self.seceret_key_1})
        exchange_name = self.exchange_name_2
        if exchange_name == 'okex': self.exchange_2 = ccxt.okex(
            {"apiKey": self.api_key_2, "secret": self.seceret_key_2, "password": self.passphrase_2})
        if exchange_name == 'okex3': self.exchange_2 = ccxt.okex3(
            {"apiKey": self.api_key_2, "secret": self.seceret_key_2, "password": self.passphrase_2})
        if exchange_name == 'huobi': self.exchange_2 = ccxt.huobipro(
            {"apiKey": self.api_key_2, "secret": self.seceret_key_2})
        if exchange_name == 'binance': self.exchange_2 = ccxt.binance(
            {"apiKey": self.api_key_2, "secret": self.seceret_key_2})
        if exchange_name == 'gateio': self.exchange_2 = ccxt.gateio(
            {"apiKey": self.api_key_2, "secret": self.seceret_key_2})
        if exchange_name == 'fcoin': self.exchange_2 = ccxt.fcoin(
            {"apiKey": self.api_key_2, "secret": self.seceret_key_2})
        exchange_name = self.exchange_name_3   #实例化另一个交易所，用来计算总资产
        if exchange_name == 'okex': self.exchange_3 = ccxt.okex(
            {"apiKey": self.api_key_3, "secret": self.seceret_key_3, "password": self.passphrase_3})
        if exchange_name == 'okex3': self.exchange_3 = ccxt.okex3(
            {"apiKey": self.api_key_3, "secret": self.seceret_key_3, "password": self.passphrase_3})
        if exchange_name == 'huobi': self.exchange_3 = ccxt.huobipro(
            {"apiKey": self.api_key_3, "secret": self.seceret_key_3})
        if exchange_name == 'binance': self.exchange_3 = ccxt.binance(
            {"apiKey": self.api_key_3, "secret": self.seceret_key_3})
        if exchange_name == 'gateio': self.exchange_3 = ccxt.gateio(
            {"apiKey": self.api_key_3, "secret": self.seceret_key_3})
        if exchange_name == 'fcoin': self.exchange_3 = ccxt.fcoin(
            {"apiKey": self.api_key_3, "secret": self.seceret_key_3})
        self.exchange_1.load_markets()
        self.exchange_2.load_markets()

    def InitLog(self):
        self.log = logging.getLogger(__name__)
        self.log.setLevel(logging.DEBUG)
        # log to txt
        formatter = logging.Formatter('[%(asctime)s] %(message)s')
        handler = logging.FileHandler("log_%s.txt" % time.strftime("%Y-%m-%d %H-%M-%S"))
        # handler = logging.handlers.RotatingFileHandler("log_%s.txt" % time.strftime("%Y-%m-%d %H-%M-%S"),maxBytes=1024*1024,backupCount=50)
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(formatter)
        # log to console
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        self.log.addHandler(handler)
        self.log.addHandler(console)
        self.log.debug("搬砖之王%s"%self.version)

    def GetLimit(self,symbol,mode):
        base = symbol.split('/')[0]
        quote = symbol.split('/')[1]
        if mode == 1:
            markets = self.markets_1
            exchange_name = self.exchange_name_1
        if mode == 2:
            markets = self.markets_2
            exchange_name = self.exchange_name_2
        for i in markets:
            if i['symbol'] == symbol:
                min_amt   = i['limits']['amount']['min'] if 'amount' in i['limits'] else 0
                min_price = i['limits']['price']['min']  if 'price'  in i['limits'] else 0
                min_cost  = i['limits']['cost']['min']   if 'cost'   in i['limits'] else 0
        if exchange_name == 'okex3': min_amt = min_cost
        if exchange_name == 'fcoin' and base == 'TRX': min_amt = 50
        if exchange_name == 'fcoin' and base == 'XLM': min_amt = 5
        if exchange_name == 'fcoin' and base == 'ETH' and quote == 'BTC': min_amt = 0.001
        if exchange_name == 'fcoin' and base == 'ETC' and quote == 'BTC': min_amt = 0.001
        if exchange_name == 'fcoin' and base == 'LTC' : min_amt = 0.01
        if exchange_name == 'fcoin' and base == 'EOS' : min_amt = 0.1
        if exchange_name == 'fcoin' and base == 'XRP' : min_amt = 1
        if exchange_name == 'gateio' and base == 'ETH': min_amt = 0.005
        if exchange_name == 'gateio' and base == 'TRX': min_amt = 60
        if exchange_name == 'gateio' and base == 'XLM': min_amt = 15
        if exchange_name == 'gateio' and base == 'EOS': min_amt = 0.3
        if exchange_name == 'gateio' and base == 'ETC': min_amt = 0.6
        return float(min_amt)*1.05,float(min_price),float(min_cost)

    def GetOrderBook(self,symbol,exchange):
        if exchange == 1:result = self.exchange_1.fetch_order_book(symbol=symbol,limit=None)
        if exchange == 2:result = self.exchange_2.fetch_order_book(symbol=symbol,limit=None)
        return result['bids'][0][0],result['bids'][0][1],result['asks'][0][0],result['asks'][0][1]

    def CreatOrder(self,symbol,exchange,type,side,amount,price):
        try:
            if exchange == 1: result = self.exchange_1.create_order(symbol, type, side, amount, price)
            if exchange == 2: result = self.exchange_2.create_order(symbol, type, side, amount, price)
        except Exception as e:
            self.log.debug("下单出错!")
            self.log.debug(e)
            self.open_fail += 1
        return result

    def CheckBalance(self):
        pass

    def HandleOpenFailBilateral(self, result,mode, min_amt):
        order_results = []
        if mode == 1:exchange = self.exchange_1
        if mode == 2:exchange = self.exchange_2
        for i in result:
            if i is not None and self.handle_open == 1:
                self.maker_fail += 1
                self.log.debug('处理未成交订单')
                self.log.debug('取消订单%s' % i['id'])
                exchange.cancel_order(i['id'], i['symbol'])
                time.sleep(2)
                self.log.debug('交易所%d按市价补单,交易对为%s，方向为%s，数量为%f'%(mode,i['symbol'],i['side'],i['remaining']))
                if i['side'] == 'buy' and i['remaining'] > min_amt: order_result = self.CreatOrder(
                    i['symbol'], mode, 'limit', i['side'], i['remaining'], i['price'] * 1.01)
                if i['side'] == 'sell' and i['remaining'] > min_amt: order_result = self.CreatOrder(
                    i['symbol'], mode, 'limit', i['side'], i['remaining'], i['price'] * 0.99)
                if 'id' in order_result:
                    self.log.debug('补单成功！')
                order_results.append(order_result)
        return order_results

    def CheckOpenBilateral(self,symbol,min_amt_1,min_amt_2):
        time.sleep(self.wait_time)
        result = []
        result_ = []
        t = []
        t.append(MyThread(self.exchange_1.fetch_open_orders, args=(symbol,)))
        t.append(MyThread(self.exchange_2.fetch_open_orders, args=(symbol,)))
        for i in t:
            i.setDaemon(True)
            i.start()
        for i in t:
            i.join()
            result.append(i.get_result())
        t = []
        t.append(MyThread(self.HandleOpenFailBilateral, args=(result[0],1,min_amt_1)))
        t.append(MyThread(self.HandleOpenFailBilateral, args=(result[1],2,min_amt_2)))
        for i in t:
            i.setDaemon(True)
            i.start()
        for i in t:
            i.join()
            result_.append(i.get_result())
        time.sleep(2)

    def HandleOpenFail(self,result,mode,min_amt):
        order_results = []
        if mode == 1:exchange = self.exchange_1
        if mode == 2:exchange = self.exchange_2
        for i in result:
            if i is not None and self.handle_open == 1:
                self.maker_fail += 1
                self.log.debug('取消未完成订单%s' % i['id'])
                exchange.cancel_order(i['id'], i['symbol'])
                time.sleep(2)
                self.log.debug('交易所%d按市价补单,交易对为%s，方向为%s，数量为%f'%(mode,i['symbol'],i['side'],i['remaining']))
                if i['side'] == 'buy' and i['remaining'] > min_amt: order_result = self.CreatOrder(
                    i['symbol'], mode, 'limit', i['side'], i['remaining'], i['price'] * 1.01)  # 有些交易对没法按市价下单
                if i['side'] == 'sell' and i['remaining'] > min_amt: order_result = self.CreatOrder(
                    i['symbol'], mode, 'limit', i['side'], i['remaining'], i['price'] * 0.99)  # 如果溢价太多，可能因为余钱不够导致下单失败
                if 'id' in order_result:
                    self.log.debug('补单成功！')
                order_results.append(order_result)
        return order_results

    def CheckOpen(self,mode1,mode2,mode3,symbol_A,symbol_B,symbol_C,min_amt_A,min_amt_B,min_amt_C):
        time.sleep(self.wait_time)
        result = []
        result_ = []
        t = []
        if mode1 == 1:
            exchange1 = self.exchange_1
        else:
            exchange1 = self.exchange_2
        if mode2 == 1:
            exchange2 = self.exchange_1
        else:
            exchange2 = self.exchange_2
        if mode3 == 1:
            exchange3 = self.exchange_1
        else:
            exchange3 = self.exchange_2
        t.append(MyThread(exchange1.fetch_open_orders, args=(symbol_A,)))
        t.append(MyThread(exchange2.fetch_open_orders, args=(symbol_B,)))
        t.append(MyThread(exchange3.fetch_open_orders, args=(symbol_C,)))
        for i in t:
            i.setDaemon(True)
            i.start()
        for i in t:
            i.join()
            result.append(i.get_result())
        self.log.debug(result)
        t = []
        t.append(MyThread(self.HandleOpenFail, args=(result[0],mode1,min_amt_A)))
        t.append(MyThread(self.HandleOpenFail, args=(result[1],mode2,min_amt_B)))
        t.append(MyThread(self.HandleOpenFail, args=(result[2],mode3,min_amt_C)))
        for i in t:
            i.setDaemon(True)
            i.start()
        for i in t:
            i.join()
            result_.append(i.get_result())
        time.sleep(2)

    def GetTotalBalance(self):
        self.log.info('====================')
        balance1 = self.exchange_1.fetch_balance()
        balance2 = self.exchange_2.fetch_balance()
        balance3 = self.exchange_3.fetch_balance()
        total_btc  = balance1['BTC']['total']+balance2['BTC']['total']+balance3['BTC']['total']
        total_eth  = balance1['ETH']['total']+balance2['ETH']['total']+balance3['ETH']['total']
        total_usdt = balance1['USDT']['total']+balance2['USDT']['total']+balance3['USDT']['total']
        if self.num == 0:
            self.init_total['USDT'] = total_usdt
            self.init_total['BTC'] = total_btc
            self.init_total['ETH'] = total_eth
        # 资产配置：
        # 持有 90% 计价币 基础币 usdx btc eth 10% 持有小币 为了确保同时下单  持有最小下单量3-5倍 xrp eos ltc
        # 改进方法：
        # 均仓策略 时间 价格 如果btc涨了 卖出btc usdt
        # 用合约对计价币进行对冲 （期现套利、季度交割、期权）
        self.log.info('        当前总资产  初始总资产')
        self.log.info('USDT：%f  %f'%(total_usdt ,self.init_total['USDT']))
        self.log.info( 'BTC：%f  %f'%(total_btc ,self.init_total['BTC']))
        self.log.info( 'ETH：%f  %f'%(total_eth ,self.init_total['ETH']))

    def GetBalance(self,X,Y,Z):
        balance1 = self.exchange_1.fetch_balance()
        balance2 = self.exchange_2.fetch_balance()
        cur_size_11 = balance1[X]['free'] if X in balance1 else 0
        cur_size_12 = balance1[Y]['free'] if Y in balance1 else 0
        cur_size_13 = balance1[Z]['free'] if Z in balance1 else 0
        cur_size_21 = balance2[X]['free'] if X in balance2 else 0
        cur_size_22 = balance2[Y]['free'] if Y in balance2 else 0
        cur_size_23 = balance2[Z]['free'] if Z in balance2 else 0
        return cur_size_11,cur_size_12,cur_size_13,cur_size_21,cur_size_22,cur_size_23

    def CheckTraingle(self,X,Y,Z):
        time.sleep(0.2)
        self.log.debug('--------------------')
        self.log.debug('当前检测三角对：%s %s %s'%(X,Y,Z))
        cur_size_11,cur_size_12,cur_size_13,cur_size_21,cur_size_22,cur_size_23 = self.GetBalance(X,Y,Z)
        self.log.debug('交易所1当前币量：%f %f %f' % (cur_size_11, cur_size_12, cur_size_13))
        self.log.debug('交易所2当前币量：%f %f %f' % (cur_size_21, cur_size_22, cur_size_23))
        symbol_A = Y + '/' + X
        symbol_B = Y + '/' + Z
        symbol_C = Z + '/' + X
        # 获取最小交易量
        min_amt_A1, min_price_A1, min_cost_A1 = self.GetLimit(symbol_A, 1)   # 获取交易对的限制
        min_amt_B1, min_price_B1, min_cost_B1 = self.GetLimit(symbol_B, 1)   # 获取交易对的限制
        min_amt_C1, min_price_C1, min_cost_C1 = self.GetLimit(symbol_C, 1)   # 获取交易对的限制
        min_amt_A2, min_price_A2, min_cost_A2 = self.GetLimit(symbol_A, 2)   # 获取交易对的限制
        min_amt_B2, min_price_B2, min_cost_B2 = self.GetLimit(symbol_B, 2)   # 获取交易对的限制
        min_amt_C2, min_price_C2, min_cost_C2 = self.GetLimit(symbol_C, 2)   # 获取交易对的限制
        t = []
        data = []
        # 多线程获取行情 两个交易所各三个币对的行情 能够组成3组双边套利 2组三角 2组跨市三角
        t.append(MyThread(self.GetOrderBook, args=(symbol_A,1,)))
        t.append(MyThread(self.GetOrderBook, args=(symbol_B,1,)))
        t.append(MyThread(self.GetOrderBook, args=(symbol_C,1,)))
        t.append(MyThread(self.GetOrderBook, args=(symbol_A,2,)))
        t.append(MyThread(self.GetOrderBook, args=(symbol_B,2,)))
        t.append(MyThread(self.GetOrderBook, args=(symbol_C,2,)))
        begin = time.time()
        for i in t:
            i.setDaemon(True)
            i.start()
        for i in t:
            i.join()
            # 用已经封装好的方法获取多线程询价的结果
            data.append(i.get_result())
        end = time.time()
        delay = float((end - begin) // 0.001)
        # 将行情存放在局部变量中
        A_bestbid_1, A_bestbid_size_1, A_bestask_1, A_bestask_size_1 = data[0][0], data[0][1], data[0][2], data[0][3]
        B_bestbid_1, B_bestbid_size_1, B_bestask_1, B_bestask_size_1 = data[1][0], data[1][1], data[1][2], data[1][3]
        C_bestbid_1, C_bestbid_size_1, C_bestask_1, C_bestask_size_1 = data[2][0], data[2][1], data[2][2], data[2][3]
        A_bestbid_2, A_bestbid_size_2, A_bestask_2, A_bestask_size_2 = data[3][0], data[3][1], data[3][2], data[3][3]
        B_bestbid_2, B_bestbid_size_2, B_bestask_2, B_bestask_size_2 = data[4][0], data[4][1], data[4][2], data[4][3]
        C_bestbid_2, C_bestbid_size_2, C_bestask_2, C_bestask_size_2 = data[5][0], data[5][1], data[5][2], data[5][3]
        # 同市三角
        Surplus_1 = C_bestbid_1 * B_bestbid_1 / A_bestask_1 - 3 * self.fee_1['trading']['maker'] * self.fee_ratio_1  # usdt 2 trx 2 eth 2 usdt
        Deficit_1 = A_bestbid_1 / B_bestask_1 / C_bestask_1 - 3 * self.fee_1['trading']['maker'] * self.fee_ratio_1  # usdt 2 eth 2 trx 2 usdt
        Surplus_2 = C_bestbid_2 * B_bestbid_2 / A_bestask_2 - 3 * self.fee_2['trading']['maker'] * self.fee_ratio_2  # usdt 2 trx 2 eth 2 usdt
        Deficit_2 = A_bestbid_2 / B_bestask_2 / C_bestask_2 - 3 * self.fee_2['trading']['maker'] * self.fee_ratio_2  # usdt 2 eth 2 trx 2 usdt
        # 跨市三角 顺1：A1  B1  C2    逆1： C2  B1  A1  顺2： A2 B2 C1  逆2： C1  B2  A2
        Surplus_112 = C_bestbid_2 * B_bestbid_1 / A_bestask_1 - 2 * self.fee_1['trading']['maker']*self.fee_ratio_1 + self.fee_2['trading']['maker']*self.fee_ratio_2  # usdt 2 trx 2 eth 2 usdt
        Deficit_211 = A_bestbid_1 / B_bestask_1 / C_bestask_2 - 2 * self.fee_1['trading']['maker']*self.fee_ratio_1 + self.fee_2['trading']['maker']*self.fee_ratio_2  # usdt 2 trx 2 eth 2 usdt
        Surplus_221 = C_bestbid_1 * B_bestbid_2 / A_bestask_2 - 2 * self.fee_2['trading']['maker']*self.fee_ratio_2 + self.fee_1['trading']['maker']*self.fee_ratio_1  # usdt 2 eth 2 trx 2 usdt
        Deficit_122 = A_bestbid_2 / B_bestask_2 / C_bestask_1 - 2 * self.fee_2['trading']['maker']*self.fee_ratio_2 + self.fee_1['trading']['maker']*self.fee_ratio_1  # usdt 2 eth 2 trx 2 usdt
        # 跨市双边  symbol_A 顺：1卖2买  逆：2买1卖  symbol_B  顺：1卖 2买  逆  1买  2卖   symbol_C: 顺：1卖  2买  逆 ： 1买  2卖
        Surplus_A = A_bestbid_1 - A_bestask_2 - A_bestbid_1 * self.fee_1['trading']['maker'] * self.fee_ratio_1 - A_bestask_2 * self.fee_2['trading']['maker'] * self.fee_ratio_2
        Deficit_A = A_bestbid_2 - A_bestask_1 - A_bestbid_2 * self.fee_2['trading']['maker'] * self.fee_ratio_2 - A_bestask_1 * self.fee_1['trading']['maker'] * self.fee_ratio_1
        Surplus_B = B_bestbid_1 - B_bestask_2 - B_bestbid_1 * self.fee_1['trading']['maker'] * self.fee_ratio_1 - B_bestask_2 * self.fee_2['trading']['maker'] * self.fee_ratio_2
        Deficit_B = B_bestbid_2 - B_bestask_1 - B_bestbid_2 * self.fee_2['trading']['maker'] * self.fee_ratio_2 - B_bestask_1 * self.fee_1['trading']['maker'] * self.fee_ratio_1
        Surplus_C = C_bestbid_1 - C_bestask_2 - C_bestbid_1 * self.fee_1['trading']['maker'] * self.fee_ratio_1 - C_bestask_2 * self.fee_2['trading']['maker'] * self.fee_ratio_2
        Deficit_C = C_bestbid_2 - C_bestask_1 - C_bestbid_2 * self.fee_2['trading']['maker'] * self.fee_ratio_2 - C_bestask_1 * self.fee_1['trading']['maker'] * self.fee_ratio_1
        # 这里采用的同步并发的方法去执行下单，更理想的方法应该是异步并发去执行下单
        # 处理信号 如果下单成功就改为False
        signal = True
        if Surplus_1 > 1 and Surplus_1 < 1.01 : # 交易所1内顺三角  加上上限是为了防止极端行情下出现损失
            # 计算下单量
            size_1 = min(cur_size_11, cur_size_12 * A_bestask_1, cur_size_13 * C_bestbid_1, A_bestask_size_1 / A_bestask_1,
                             B_bestbid_size_1 * A_bestask_1, C_bestbid_size_1 * C_bestbid_1) * self.ratio
            size_2 = size_1 / A_bestask_1
            size_3 = size_2 * B_bestbid_1
            amt_A = float(self.exchange_1.amount_to_precision(symbol_A,size_2))
            amt_B = float(self.exchange_1.amount_to_precision(symbol_B,size_2))
            amt_C = float(self.exchange_1.amount_to_precision(symbol_C,size_3))
            price_A = float(self.exchange_1.price_to_precision(symbol_A,A_bestask_1))
            price_B = float(self.exchange_1.price_to_precision(symbol_B,B_bestbid_1))
            price_C = float(self.exchange_1.price_to_precision(symbol_C,C_bestbid_1))
            # 计算预期盈利
            win = size_3 * C_bestbid_1 - size_1
            # 当深度满足下单条件时 执行下单 rest > ws
            if size_2 > min_amt_A1 and size_2 > min_amt_B1 and size_3 > min_amt_C1\
                and win > 0 and delay <= 95\
                and amt_A > 0 and amt_B > 0 and amt_C > 0 and price_A > 0 and price_B > 0 and price_C > 0:
                t = []
                order_result = []
                t.append(MyThread(self.CreatOrder, args=(symbol_A,1,'limit','buy' ,size_2,A_bestask_1,)))
                t.append(MyThread(self.CreatOrder, args=(symbol_B,1,'limit','sell',size_2,B_bestbid_1,)))
                t.append(MyThread(self.CreatOrder, args=(symbol_C,1,'limit','sell',size_3,C_bestbid_1,)))
                begin = time.time()
                for i in t:
                    i.setDaemon(True)
                    i.start()
                for i in t:
                    i.join()
                    order_result.append(i.get_result())
                end = time.time()
                delay_ = float((end - begin) // 0.001)
                self.log.debug("%s发现正循环信号！"%self.exchange_name_1)
                self.log.debug("预估交易数量: %f  %f  %f" % (size_1, size_2, size_3))
                self.log.debug('in : %f  out : %f  win : %f' % (size_1,size_3 * C_bestbid_1, win))  # 先1 3  后2
                self.log.debug("价差比率:%f" % (Surplus_1))
                self.log.debug('询价延迟: %f ms' % delay )
                self.log.debug('下单延迟: %f ms' % delay_)
                self.log.debug('下单参数：')
                self.log.debug('A: %f %f %f %f' % (size_2, A_bestask_1,amt_A,price_A))
                self.log.debug('B: %f %f %f %f' % (size_2, B_bestbid_1,amt_B,price_B))
                self.log.debug('C: %f %f %f %f' % (size_3, C_bestbid_1,amt_C,price_C))
                self.log.debug('下单结果：')
                for i in order_result:
                    if 'id' not in i:
                        # self.log.debug('下单出错!')
                        # self.open_fail += 1
                        signal = False
                    else:
                        self.log.debug(i)
                self.CheckOpen(1,1,1,symbol_A,symbol_B,symbol_C,min_amt_A1,min_amt_B1,min_amt_C1)
                if signal:#判断是否按限价单成交，如果不是，则扯单后补市价单
                    self.open_num += 1
                self.log.debug('套利前币量之总和： %f %f %f' % (
                    cur_size_11 + cur_size_21, cur_size_12 + cur_size_22, cur_size_13 + cur_size_23))
                total = (cur_size_11 + cur_size_21) + (cur_size_12 + cur_size_22)*(
                        0.5*A_bestbid_1+0.5*A_bestask_1) + (cur_size_13 + cur_size_23)*(0.5*C_bestask_1+0.5*C_bestbid_1)
                self.log.debug('币量相当于%f个%s'%(total,X))
                cur_size_11, cur_size_12, cur_size_13, cur_size_21, cur_size_22, cur_size_23 = self.GetBalance(X, Y, Z)
                self.log.debug('套利后币量之总和： %f %f %f' % (
                    cur_size_11 + cur_size_21, cur_size_12 + cur_size_22, cur_size_13 + cur_size_23))
                total_= (cur_size_11 + cur_size_21) + (cur_size_12 + cur_size_22) * (
                            0.5 * A_bestbid_1 + 0.5 * A_bestask_1) + (cur_size_13 + cur_size_23) * (
                                    0.5 * C_bestask_1 + 0.5 * C_bestbid_1)
                self.log.debug('币量相当于%f个%s' % (total_, X))
                # 计算实际收益 套利前减去套利后
                self.win[X] += total_ - total
                return
            else:
                # 如果不满足套利条件 进行提醒
                self.log.debug('%s有正循环信号，但不符合条件！'%self.exchange_name_1)
                # self.log.debug('币1：%f 币2：%f 币3：%f A盘口：%f B盘口：%f C盘口：%f'%(cur_size_11, \
                #     cur_size_12 * A_bestask_1, cur_size_13 * C_bestbid_1, A_bestask_size_1 / A_bestask_1, \
                #     B_bestbid_size_1 * A_bestask_1, C_bestbid_size_1 * C_bestbid_1))
                hand = [cur_size_11, cur_size_12 * A_bestask_1, cur_size_13 * C_bestbid_1, \
                        A_bestask_size_1 / A_bestask_1, B_bestbid_size_1 * A_bestask_1, C_bestbid_size_1 * C_bestbid_1]
                n = hand.index(min(hand))
                if n == 0:
                    self.log.info('提示：交易所%s缺少%s'%(self.exchange_name_1,X))
                    self.signal_num += 1
                elif n == 1:
                    self.log.info('提示：交易所%s缺少%s'%(self.exchange_name_1,Y))
                    self.signal_num += 1
                elif n == 2:
                    self.log.info('提示：交易所%s缺少%s'%(self.exchange_name_1,Z))
                    self.signal_num += 1
                else:
                    self.log.debug('盘口深度不够')
                self.log.debug('size: %f %f %f' % (size_2, size_2, size_3))
                self.log.debug('min_amt: %f %f %f' % (min_amt_A1, min_amt_B1, min_amt_C1))
                self.log.debug('amt: %f %f %f price: %f %f %f' % (amt_A, amt_B, amt_C, price_A, price_B, price_C))
                if win <= 0: self.log.debug('预估盈利太低')
                if delay > 95: self.log.debug('询价延迟过高!  %f ms' % delay)
                return
        if Deficit_1 > 1 and Deficit_1 < 1.01:
            size_1 = min(cur_size_11, cur_size_13 * C_bestask_1, cur_size_12 * A_bestbid_1, C_bestask_size_1 * C_bestask_1,
                             B_bestask_size_1 * B_bestask_1 * C_bestask_1, A_bestbid_1 * A_bestbid_size_1) * self.ratio
            size_2 = size_1 / C_bestask_1
            size_3 = size_2 / B_bestask_1
            amt_A = float(self.exchange_1.amount_to_precision(symbol_A,size_3))
            amt_B = float(self.exchange_1.amount_to_precision(symbol_B,size_3))
            amt_C = float(self.exchange_1.amount_to_precision(symbol_C,size_2))
            price_A = float(self.exchange_1.price_to_precision(symbol_A,A_bestbid_1))
            price_B = float(self.exchange_1.price_to_precision(symbol_B,B_bestask_1))
            price_C = float(self.exchange_1.price_to_precision(symbol_C,C_bestask_1))
            win = size_3 * A_bestbid_1 - size_1
            if size_3 > min_amt_A1 and size_3 > min_amt_B1 and size_2 > min_amt_C1\
                and win > 0 and delay <= 95\
                and amt_A > 0 and amt_B>0 and amt_C>0 and price_A>0 and price_B>0 and price_C>0:
                t = []
                order_result = []
                t.append(MyThread(self.CreatOrder, args=(symbol_C,1, 'limit', 'buy' , size_2, C_bestask_1,)))
                t.append(MyThread(self.CreatOrder, args=(symbol_B,1, 'limit', 'buy' , size_3, B_bestask_1,)))
                t.append(MyThread(self.CreatOrder, args=(symbol_A,1, 'limit', 'sell', size_3, A_bestbid_1,)))
                begin = time.time()
                for i in t:
                    i.setDaemon(True)
                    i.start()
                for i in t:
                    i.join()
                    order_result.append(i.get_result())
                end = time.time()
                delay_ = float((end - begin) // 0.001)
                self.log.debug("%s发现逆循环信号！"%self.exchange_name_1)
                self.log.debug("预估交易数量: %f  %f  %f" % (size_1, size_2, size_3))
                self.log.debug('in : %f  out : %f   win : %f' % (size_1, size_3 * A_bestbid_1,win))
                self.log.debug("价差比率:%f" % (Deficit_1))
                self.log.debug('询价延迟: %f ms' % delay )
                self.log.debug('下单延迟: %f ms' % delay_)
                self.log.debug('下单参数：')
                self.log.debug('C: %f %f %f %f' % (size_2, C_bestask_1, amt_C, price_C))
                self.log.debug('B: %f %f %f %f' % (size_3, B_bestask_1, amt_B, price_B))
                self.log.debug('A: %f %f %f %f' % (size_3, A_bestbid_1, amt_A, price_A))
                self.log.debug('下单结果：')
                for i in order_result:
                    if 'id' not in i:
                        # self.log.debug('下单出错!')
                        # self.open_fail += 1
                        signal = False
                    else:
                        self.log.debug(i)
                self.CheckOpen(1,1,1,symbol_C,symbol_B,symbol_A,min_amt_C1,min_amt_B1,min_amt_A1)
                if signal: #判断是否按市价单成交
                    self.open_num += 1
                self.log.debug('套利前币量之总和： %f %f %f' % (
                    cur_size_11 + cur_size_21, cur_size_12 + cur_size_22, cur_size_13 + cur_size_23))
                total = (cur_size_11 + cur_size_21) + (cur_size_12 + cur_size_22) * (
                            0.5 * A_bestbid_1 + 0.5 * A_bestask_1) + (cur_size_13 + cur_size_23) * (
                                    0.5 * C_bestask_1 + 0.5 * C_bestbid_1)
                self.log.debug('币量相当于%f个%s' % (total, X))
                cur_size_11, cur_size_12, cur_size_13, cur_size_21, cur_size_22, cur_size_23 = self.GetBalance(X, Y, Z)
                self.log.debug('套利后币量之总和： %f %f %f' % (
                    cur_size_11 + cur_size_21, cur_size_12 + cur_size_22, cur_size_13 + cur_size_23))
                total_ = (cur_size_11 + cur_size_21) + (cur_size_12 + cur_size_22) *(
                            0.5 * A_bestbid_1 + 0.5 * A_bestask_1) + (cur_size_13 + cur_size_23) * (
                                    0.5 * C_bestask_1 + 0.5 * C_bestbid_1)
                self.log.debug('币量相当于%f个%s' % (total_, X))
                self.win[X] += total_ - total
                return
            else:
                self.log.debug('%s有逆循环信号，但不符合条件!'%self.exchange_name_1)
                # self.log.debug('币1：%f 币2：%f 币3：%f C盘口：%f B盘口：%f A盘口：%f'%(cur_size_11, cur_size_13 * C_bestask_1, cur_size_12 * A_bestbid_1, C_bestask_size_1 * C_bestask_1,
                #              B_bestask_size_1 * B_bestask_1 * C_bestask_1, A_bestbid_1 * A_bestbid_size_1))
                hand = [cur_size_11, cur_size_12 * A_bestbid_1, cur_size_13 * C_bestask_1, C_bestask_size_1 * C_bestask_1,
                             B_bestask_size_1 * B_bestask_1 * C_bestask_1, A_bestbid_1 * A_bestbid_size_1]
                n = hand.index(min(hand))
                if n == 0:
                    self.log.info('提示：交易所%s缺少%s' % (self.exchange_name_1, X))
                    self.signal_num += 1
                elif n == 1:
                    self.log.info('提示：交易所%s缺少%s' % (self.exchange_name_1, Y))
                    self.signal_num += 1
                elif n == 2:
                    self.log.info('提示：交易所%s缺少%s' % (self.exchange_name_1, Z))
                    self.signal_num += 1
                else:
                    self.log.debug('盘口深度不够')
                self.log.debug('size: %f %f %f'%(size_3,size_3,size_2))
                self.log.debug('min_amt: %f %f %f'%(min_amt_A1,min_amt_B1,min_amt_C1))
                self.log.debug('amt: %f %f %f price: %f %f %f'%(amt_A,amt_B,amt_C,price_A,price_B,price_C))
                if win <= 0: self.log.debug('预估盈利太低')
                if delay > 95: self.log.debug('询价延迟过高!  %f ms' % delay)
                return
        if Surplus_2 > 1 and Surplus_2 < 1.01:
            size_1 = min(cur_size_21, cur_size_22 * A_bestask_2, cur_size_23 * C_bestbid_2, A_bestask_size_2 / A_bestask_2,
                             B_bestbid_size_2 * A_bestask_2, C_bestbid_size_2 * C_bestbid_2) * self.ratio
            size_2 = size_1 / A_bestask_2
            size_3 = size_2 * B_bestbid_2
            amt_A = float(self.exchange_2.amount_to_precision(symbol_A,size_2))
            amt_B = float(self.exchange_2.amount_to_precision(symbol_B,size_2))
            amt_C = float(self.exchange_2.amount_to_precision(symbol_C,size_3))
            price_A = float(self.exchange_2.price_to_precision(symbol_A,A_bestask_2))
            price_B = float(self.exchange_2.price_to_precision(symbol_B,B_bestbid_2))
            price_C = float(self.exchange_2.price_to_precision(symbol_C,C_bestbid_2))
            win = size_3 * C_bestbid_2 - size_1
            if size_2 > min_amt_A2 and size_2 > min_amt_B2 and size_3 > min_amt_C2\
                and win > 0 and delay <= 95\
                and amt_A > 0 and amt_B > 0 and amt_C > 0 and price_A > 0 and price_B > 0 and price_C > 0:
                t = []
                order_result = []
                t.append(MyThread(self.CreatOrder, args=(symbol_A,2,'limit','buy' ,size_2,A_bestask_2,)))
                t.append(MyThread(self.CreatOrder, args=(symbol_B,2,'limit','sell',size_2,B_bestbid_2,)))
                t.append(MyThread(self.CreatOrder, args=(symbol_C,2,'limit','sell',size_3,C_bestbid_2,)))
                begin = time.time()
                for i in t:
                    i.setDaemon(True)
                    i.start()
                for i in t:
                    i.join()
                    order_result.append(i.get_result())
                end = time.time()
                delay_ = float((end - begin) // 0.001)
                self.log.debug("%s发现正循环信号！"%self.exchange_name_2)
                self.log.debug("预估交易数量: %f  %f  %f" % (size_1, size_2, size_3))
                self.log.debug('in : %f  out : %f  win : %f' % (size_1,size_3 * C_bestbid_2, win))  # 先1 3  后2
                self.log.debug("价差比率:%f" % (Surplus_2))
                self.log.debug('询价延迟: %f ms' % delay )
                self.log.debug('下单延迟: %f ms' % delay_)
                self.log.debug('下单参数：')
                self.log.debug('A: %f %f %f %f' % (size_2, A_bestask_2,amt_A,price_A))
                self.log.debug('B: %f %f %f %f' % (size_2, B_bestbid_2,amt_B,price_B))
                self.log.debug('C: %f %f %f %f' % (size_3, C_bestbid_2,amt_C,price_C))
                self.log.debug('下单结果：')
                for i in order_result:
                    if 'id' not in i:
                        # self.log.debug('下单出错!')
                        # self.open_fail += 1
                        signal = False
                    else:
                        self.log.debug(i)
                self.CheckOpen(2,2,2,symbol_A,symbol_B,symbol_C,min_amt_A2, min_amt_B2, min_amt_C2)
                if signal:#判断是否按限价单成交，如果不是，则扯单后补市价单
                    self.open_num += 1
                self.log.debug('套利前币量之总和： %f %f %f' % (cur_size_11 + cur_size_21, cur_size_12 + cur_size_22, cur_size_13 + cur_size_23))
                total = (cur_size_11 + cur_size_21) + (cur_size_12 + cur_size_22) * (
                            0.5 * A_bestbid_1 + 0.5 * A_bestask_1) + (cur_size_13 + cur_size_23) * (
                                    0.5 * C_bestask_1 + 0.5 * C_bestbid_1)
                self.log.debug('币量相当于%f个%s' % (total, X))
                cur_size_11, cur_size_12, cur_size_13, cur_size_21, cur_size_22, cur_size_23 = self.GetBalance(X, Y, Z)
                self.log.debug('套利后币量之总和： %f %f %f' % (cur_size_11 + cur_size_21, cur_size_12 + cur_size_22, cur_size_13 + cur_size_23))
                total_ = (cur_size_11 + cur_size_21) + (cur_size_12 + cur_size_22) * (
                            0.5 * A_bestbid_1 + 0.5 * A_bestask_1) + (cur_size_13 + cur_size_23) * (
                                    0.5 * C_bestask_1 + 0.5 * C_bestbid_1)
                self.log.debug('币量相当于%f个%s' % (total_, X))
                self.win[X] += total_ - total
                return
            else:
                self.log.debug('%s有正循环信号，但不符合条件！'%self.exchange_name_2)
                # self.log.debug('币1：%f 币2：%f 币3：%f A盘口：%f B盘口：%f C盘口：%f'%(cur_size_21, cur_size_22 * A_bestask_2, cur_size_23 * C_bestbid_2, A_bestask_size_2 / A_bestask_2,
                #              B_bestbid_size_2 * A_bestask_2, C_bestbid_size_2 * C_bestbid_2))
                hand = [cur_size_21, cur_size_22 * A_bestask_2, cur_size_23 * C_bestbid_2, A_bestask_size_2 / A_bestask_2,
                             B_bestbid_size_2 * A_bestask_2, C_bestbid_size_2 * C_bestbid_2]
                n = hand.index(min(hand))
                if n == 0:
                    self.log.info('提示：交易所%s缺少%s' % (self.exchange_name_2, X))
                    self.signal_num += 1
                elif n == 1:
                    self.log.info('提示：交易所%s缺少%s' % (self.exchange_name_2, Y))
                    self.signal_num += 1
                elif n == 2:
                    self.log.info('提示：交易所%s缺少%s' % (self.exchange_name_2, Z))
                    self.signal_num += 1
                else:
                    self.log.debug('盘口深度不够')
                self.log.debug('size: %f %f %f' % (size_2, size_2, size_3))
                self.log.debug('min_amt: %f %f %f' % (min_amt_A2, min_amt_B2, min_amt_C2))
                self.log.debug('amt: %f %f %f price: %f %f %f' % (amt_A, amt_B, amt_C, price_A, price_B, price_C))
                if win <= 0: self.log.debug('预估盈利太低')
                if delay > 95: self.log.debug('询价延迟过高!  %f ms' % delay)
                return
        if Deficit_2 > 1 and Deficit_2 < 1.01:
            size_1 = min(cur_size_21, cur_size_23 * C_bestask_2, cur_size_22 * A_bestbid_2, C_bestask_size_2 * C_bestask_2,
                             B_bestask_size_2 * B_bestask_2 * C_bestask_2, A_bestbid_2 * A_bestbid_size_2) * self.ratio
            size_2 = size_1 / C_bestask_2
            size_3 = size_2 / B_bestask_2
            amt_A = float(self.exchange_2.amount_to_precision(symbol_A,size_3))
            amt_B = float(self.exchange_2.amount_to_precision(symbol_B,size_3))
            amt_C = float(self.exchange_2.amount_to_precision(symbol_C,size_2))
            price_A = float(self.exchange_2.price_to_precision(symbol_A,A_bestbid_2))
            price_B = float(self.exchange_2.price_to_precision(symbol_B,B_bestask_2))
            price_C = float(self.exchange_2.price_to_precision(symbol_C,C_bestask_2))
            win = size_3 * A_bestbid_2 - size_1
            if size_3 > min_amt_A2 and size_3 > min_amt_B2 and size_2 > min_amt_C2\
                and win > 0 and delay <= 95\
                and amt_A > 0 and amt_B>0 and amt_C>0 and price_A>0 and price_B>0 and price_C>0:
                t = []
                order_result = []
                t.append(MyThread(self.CreatOrder, args=(symbol_C,2, 'limit', 'buy' , size_2, C_bestask_2,)))
                t.append(MyThread(self.CreatOrder, args=(symbol_B,2, 'limit', 'buy' , size_3, B_bestask_2,)))
                t.append(MyThread(self.CreatOrder, args=(symbol_A,2, 'limit', 'sell', size_3, A_bestbid_2,)))
                begin = time.time()
                for i in t:
                    i.setDaemon(True)
                    i.start()
                for i in t:
                    i.join()
                    order_result.append(i.get_result())
                end = time.time()
                delay_ = float((end - begin) // 0.001)
                self.log.debug("%s发现逆循环信号！"%self.exchange_name_2)
                self.log.debug("预估交易数量: %f  %f  %f" % (size_1, size_2, size_3))
                self.log.debug('in : %f  out : %f   win : %f' % (size_1, size_3 * A_bestbid_2,win))
                self.log.debug("价差比率:%f" % (Deficit_2))
                self.log.debug('询价延迟: %f ms' % delay )
                self.log.debug('下单延迟: %f ms' % delay_)
                self.log.debug('下单参数：')
                self.log.debug('C: %f %f %f %f' % (size_2, C_bestask_2, amt_C, price_C))
                self.log.debug('B: %f %f %f %f' % (size_3, B_bestask_2, amt_B, price_B))
                self.log.debug('A: %f %f %f %f' % (size_3, A_bestbid_2, amt_A, price_A))
                self.log.debug('下单结果：')
                for i in order_result:
                    if 'id' not in i:
                        # self.log.debug('下单出错!')
                        # self.open_fail += 1
                        signal = False
                    else:
                        self.log.debug(i)
                self.CheckOpen(2,2,2,symbol_C,symbol_B,symbol_A,min_amt_C2, min_amt_B2, min_amt_A2)
                if signal: #判断是否按市价单成交
                    self.open_num += 1
                self.log.debug('套利前币量之总和： %f %f %f' % (cur_size_11 + cur_size_21, cur_size_12 + cur_size_22, cur_size_13 + cur_size_23))
                total = (cur_size_11 + cur_size_21) + (cur_size_12 + cur_size_22) * (
                        0.5 * A_bestbid_1 + 0.5 * A_bestask_1) + (cur_size_13 + cur_size_23) * (
                                0.5 * C_bestask_1 + 0.5 * C_bestbid_1)
                self.log.debug('币量相当于%f个%s' % (total, X))
                cur_size_11, cur_size_12, cur_size_13, cur_size_21, cur_size_22, cur_size_23 = self.GetBalance(X, Y, Z)
                self.log.debug('套利后币量之总和： %f %f %f' % (cur_size_11 + cur_size_21, cur_size_12 + cur_size_22, cur_size_13 + cur_size_23))
                total_ = (cur_size_11 + cur_size_21) + (cur_size_12 + cur_size_22) * (
                        0.5 * A_bestbid_1 + 0.5 * A_bestask_1) + (cur_size_13 + cur_size_23) * (
                                0.5 * C_bestask_1 + 0.5 * C_bestbid_1)
                self.log.debug('币量相当于%f个%s' % (total_, X))
                self.win[X] += total_ - total
                return
            else:
                self.log.debug('%s有逆循环信号，但不符合条件!'%self.exchange_name_2)
                # self.log.debug('币1：%f 币2：%f 币3：%f C盘口：%f B盘口：%f A盘口：%f'%(cur_size_21, cur_size_23 * C_bestask_2, cur_size_22 * A_bestbid_2, C_bestask_size_2 * C_bestask_2,
                #              B_bestask_size_2 * B_bestask_2 * C_bestask_2, A_bestbid_2 * A_bestbid_size_2))
                hand = [cur_size_21, cur_size_22 * A_bestbid_2, cur_size_23 * C_bestask_2, C_bestask_size_2 * C_bestask_2,
                             B_bestask_size_2 * B_bestask_2 * C_bestask_2, A_bestbid_2 * A_bestbid_size_2]
                n = hand.index(min(hand))
                if n == 0:
                    self.log.info('提示：交易所%s缺少%s' % (self.exchange_name_2, X))
                    self.signal_num += 1
                elif n == 1:
                    self.log.info('提示：交易所%s缺少%s' % (self.exchange_name_2, Y))
                    self.signal_num += 1
                elif n == 2:
                    self.log.info('提示：交易所%s缺少%s' % (self.exchange_name_2, Z))
                    self.signal_num += 1
                else:
                    self.log.debug('盘口深度不够')
                self.log.debug('size: %f %f %f'%(size_3,size_3,size_2))
                self.log.debug('min_amt: %f %f %f'%(min_amt_A2,min_amt_B2,min_amt_C2))
                self.log.debug('amt: %f %f %f price: %f %f %f'%(amt_A,amt_B,amt_C,price_A,price_B,price_C))
                if win <= 0: self.log.debug('预估盈利太低')
                if delay > 95: self.log.debug('询价延迟过高!  %f ms' % delay)
                return
        if Surplus_112 > 1 and Surplus_112 < 1.01:# 跨市三角 顺1：A1  B1  C2
            size_1 = min(cur_size_11, cur_size_12 * A_bestask_1, cur_size_23 * C_bestbid_2, A_bestask_size_1 / A_bestask_1,
                             B_bestbid_size_1 * A_bestask_1, C_bestbid_size_2 * C_bestbid_2) * self.ratio
            size_2 = size_1 / A_bestask_1
            size_3 = size_2 * B_bestbid_1
            amt_A = float(self.exchange_1.amount_to_precision(symbol_A,size_2))
            amt_B = float(self.exchange_1.amount_to_precision(symbol_B,size_2))
            amt_C = float(self.exchange_2.amount_to_precision(symbol_C,size_3))
            price_A = float(self.exchange_1.price_to_precision(symbol_A,A_bestask_1))
            price_B = float(self.exchange_1.price_to_precision(symbol_B,B_bestbid_1))
            price_C = float(self.exchange_2.price_to_precision(symbol_C,C_bestbid_2))
            win = size_3 * C_bestbid_2 - size_1
            if size_2 > min_amt_A1 and size_2 > min_amt_B1 and size_3 > min_amt_C2 and win > 0 and delay <= 95\
                and amt_A > 0 and amt_B > 0 and amt_C > 0 and price_A > 0 and price_B > 0 and price_C > 0:
                t = []
                order_result = []
                t.append(MyThread(self.CreatOrder, args=(symbol_A,1,'limit','buy' ,size_2,A_bestask_1,)))
                t.append(MyThread(self.CreatOrder, args=(symbol_B,1,'limit','sell',size_2,B_bestbid_1,)))
                t.append(MyThread(self.CreatOrder, args=(symbol_C,2,'limit','sell',size_3,C_bestbid_2,)))
                begin = time.time()
                for i in t:
                    i.setDaemon(True)
                    i.start()
                for i in t:
                    i.join()
                    order_result.append(i.get_result())
                end = time.time()
                delay_ = float((end - begin) // 0.001)
                self.log.debug("发现跨市112正循环信号！")
                self.log.debug("预估交易数量: %f  %f  %f" % (size_1, size_2, size_3))
                self.log.debug('in : %f  out : %f  win : %f' % (size_1,size_3 * C_bestbid_2, win))  # 先1 3  后2
                self.log.debug("价差比率:%f" % (Surplus_112))
                self.log.debug('询价延迟: %f ms' % delay )
                self.log.debug('下单延迟: %f ms' % delay_)
                self.log.debug('下单参数：')
                self.log.debug('A: %f %f %f %f' % (size_2, A_bestask_1, amt_A, price_A))
                self.log.debug('B: %f %f %f %f' % (size_2, B_bestbid_1, amt_B, price_B))
                self.log.debug('C: %f %f %f %f' % (size_3, C_bestbid_2, amt_C, price_C))
                self.log.debug('下单结果：')
                for i in order_result:
                    if 'id' not in i:
                        # self.log.debug('下单出错!')   # 对下单出错要进行相应处理
                        # self.open_fail += 1
                        signal = False
                    else:
                        self.log.debug(i)
                self.CheckOpen(1,1,2,symbol_A,symbol_B,symbol_C,min_amt_A1, min_amt_B1, min_amt_C2)
                if signal:#判断是否按限价单成交，如果不是，则扯单后补市价单
                    self.open_num += 1
                self.log.debug('套利前币量之总和： %f %f %f' % (cur_size_11 + cur_size_21, cur_size_12 + cur_size_22, cur_size_13 + cur_size_23))
                total = (cur_size_11 + cur_size_21) + (cur_size_12 + cur_size_22) * (
                        0.5 * A_bestbid_1 + 0.5 * A_bestask_1) + (cur_size_13 + cur_size_23) * (
                                0.5 * C_bestask_1 + 0.5 * C_bestbid_1)
                self.log.debug('币量相当于%f个%s' % (total, X))
                cur_size_11, cur_size_12, cur_size_13, cur_size_21, cur_size_22, cur_size_23 = self.GetBalance(X, Y, Z)
                self.log.debug('套利后币量之总和： %f %f %f' % (cur_size_11 + cur_size_21, cur_size_12 + cur_size_22, cur_size_13 + cur_size_23))
                total_ = (cur_size_11 + cur_size_21) + (cur_size_12 + cur_size_22) * (
                        0.5 * A_bestbid_1 + 0.5 * A_bestask_1) + (cur_size_13 + cur_size_23) * (
                                0.5 * C_bestask_1 + 0.5 * C_bestbid_1)
                self.log.debug('币量相当于%f个%s' % (total_, X))
                self.win[X] += total_ - total
                return
            else:
                self.log.debug('有跨市112正循环信号，但不符合条件！')
                # self.log.debug('币1：%f 币2：%f 币3：%f A盘口：%f B盘口：%f C盘口：%f'%(cur_size_11, \
                #     cur_size_12 * A_bestask_1, cur_size_23 * C_bestbid_2, A_bestask_size_1 / A_bestask_1, \
                #     B_bestbid_size_1 * A_bestask_1, C_bestbid_size_2 * C_bestbid_2))
                hand = [cur_size_11, cur_size_12 * A_bestask_1, cur_size_23 * C_bestbid_2, A_bestask_size_1 / A_bestask_1, \
                    B_bestbid_size_1 * A_bestask_1, C_bestbid_size_2 * C_bestbid_2]
                n = hand.index(min(hand))
                if n == 0:
                    self.log.info('提示：交易所%s缺少%s' % (self.exchange_name_1, X))
                    self.signal_num += 1
                elif n == 1:
                    self.log.info('提示：交易所%s缺少%s' % (self.exchange_name_1, Y))
                    self.signal_num += 1
                elif n == 2:
                    self.log.info('提示：交易所%s缺少%s' % (self.exchange_name_2, Z))
                    self.signal_num += 1
                else:
                    self.log.debug('盘口深度不够')
                if win <= 0: self.log.debug('预估盈利太低')
                if delay > 95: self.log.debug('询价延迟过高!  %f ms' % delay)
                return
        if Deficit_211 > 1 and Deficit_211 < 1.01:# 跨市三角 逆1： C2  B1  A1
            size_1 = min(cur_size_21, cur_size_13 * C_bestask_2, cur_size_12 * A_bestbid_1, C_bestask_size_2 * C_bestask_2,
                             B_bestask_size_1 * B_bestask_1 * C_bestask_2, A_bestbid_1 * A_bestbid_size_1) * self.ratio
            size_2 = size_1 / C_bestask_2
            size_3 = size_2 / B_bestask_1
            amt_A = float(self.exchange_1.amount_to_precision(symbol_A,size_3))
            amt_B = float(self.exchange_1.amount_to_precision(symbol_B,size_3))
            amt_C = float(self.exchange_2.amount_to_precision(symbol_C,size_2))
            price_A = float(self.exchange_1.price_to_precision(symbol_A,A_bestbid_1))
            price_B = float(self.exchange_1.price_to_precision(symbol_B,B_bestask_1))
            price_C = float(self.exchange_2.price_to_precision(symbol_C,C_bestask_2))
            win = size_3 * A_bestbid_1 - size_1
            if size_3 > min_amt_A1 and size_3 > min_amt_B1 and size_2 > min_amt_C2 and win > 0 and delay <= 95\
                and amt_A > 0 and amt_B>0 and amt_C>0 and price_A>0 and price_B>0 and price_C>0:
                t = []
                order_result = []
                t.append(MyThread(self.CreatOrder, args=(symbol_C,2, 'limit', 'buy' , size_2, C_bestask_2,)))
                t.append(MyThread(self.CreatOrder, args=(symbol_B,1, 'limit', 'buy' , size_3, B_bestask_1,)))
                t.append(MyThread(self.CreatOrder, args=(symbol_A,1, 'limit', 'sell', size_3, A_bestbid_1,)))
                begin = time.time()
                for i in t:
                    i.setDaemon(True)
                    i.start()
                for i in t:
                    i.join()
                    order_result.append(i.get_result())
                end = time.time()
                delay_ = float((end - begin) // 0.001)
                self.log.debug("发现跨市211逆循环信号！")
                self.log.debug("预估交易数量: %f  %f  %f" % (size_1, size_2, size_3))
                self.log.debug('in : %f  out : %f   win : %f' % (size_1, size_3 * A_bestbid_1,win))
                self.log.debug("价差比率:%f" %(Deficit_211))
                self.log.debug('询价延迟: %f ms' % delay )
                self.log.debug('下单延迟: %f ms' % delay_)
                self.log.debug('下单参数：')
                self.log.debug('C: %f %f %f %f' % (size_2, C_bestask_2, amt_C, price_C))
                self.log.debug('B: %f %f %f %f' % (size_3, B_bestask_1, amt_B, price_B))
                self.log.debug('A: %f %f %f %f' % (size_3, A_bestbid_1, amt_A, price_A))
                self.log.debug('下单结果：')
                for i in order_result:
                    if 'id' not in i:
                        # self.log.debug('下单出错!')
                        # self.open_fail += 1
                        signal = False
                    else:
                        self.log.debug(i)
                self.CheckOpen(2,1,1,symbol_C,symbol_B,symbol_A,min_amt_C2, min_amt_B1, min_amt_A1)
                if signal: #判断是否按市价单成交
                    self.open_num += 1
                self.log.debug('套利前币量之总和： %f %f %f' % (cur_size_11 + cur_size_21, cur_size_12 + cur_size_22, cur_size_13 + cur_size_23))
                total = (cur_size_11 + cur_size_21) + (cur_size_12 + cur_size_22) * (
                        0.5 * A_bestbid_1 + 0.5 * A_bestask_1) + (cur_size_13 + cur_size_23) * (
                                0.5 * C_bestask_1 + 0.5 * C_bestbid_1)
                self.log.debug('币量相当于%f个%s' % (total, X))
                cur_size_11, cur_size_12, cur_size_13, cur_size_21, cur_size_22, cur_size_23 = self.GetBalance(X, Y, Z)
                self.log.debug('套利后币量之总和： %f %f %f' % (cur_size_11 + cur_size_21, cur_size_12 + cur_size_22, cur_size_13 + cur_size_23))
                total_ = (cur_size_11 + cur_size_21) + (cur_size_12 + cur_size_22) * (
                        0.5 * A_bestbid_1 + 0.5 * A_bestask_1) + (cur_size_13 + cur_size_23) * (
                                0.5 * C_bestask_1 + 0.5 * C_bestbid_1)
                self.log.debug('币量相当于%f个%s' % (total_, X))
                self.win[X] += total_ - total
                return
            else:
                self.log.debug('有跨市211逆循环信号，但不符合条件!')
                # self.log.debug('币1：%f 币2：%f 币3：%f C盘口：%f B盘口：%f A盘口：%f'%(cur_size_21, \
                #     cur_size_12 * A_bestbid_1, cur_size_13 * C_bestask_2, C_bestask_size_2 * C_bestask_2, \
                #     B_bestask_size_1 * B_bestask_1 * C_bestask_2, A_bestbid_1 * A_bestbid_size_1))
                hand = [cur_size_21, cur_size_12 * A_bestbid_1, cur_size_13 * C_bestask_2, C_bestask_size_2 * C_bestask_2, \
                    B_bestask_size_1 * B_bestask_1 * C_bestask_2, A_bestbid_1 * A_bestbid_size_1]
                n = hand.index(min(hand))
                if n == 0:
                    self.log.info('提示：交易所%s缺少%s' % (self.exchange_name_2, X))
                    self.signal_num += 1
                elif n == 1:
                    self.log.info('提示：交易所%s缺少%s' % (self.exchange_name_1, Y))
                    self.signal_num += 1
                elif n == 2:
                    self.log.info('提示：交易所%s缺少%s' % (self.exchange_name_1, Z))
                    self.signal_num += 1
                else:
                    self.log.debug('盘口深度不够')
                if win <= 0: self.log.debug('预估盈利太低')
                if delay > 95: self.log.debug('询价延迟过高!  %f ms' % delay)
                return
        if Surplus_221 > 1 and Surplus_221 < 1.01:# 顺2： A2 B2 C1
            size_1 = min(cur_size_21, cur_size_22 * A_bestask_2, cur_size_13 * C_bestbid_1, A_bestask_size_2 / A_bestask_2,
                             B_bestbid_size_2 * A_bestask_2, C_bestbid_size_1 * C_bestbid_1) * self.ratio
            size_2 = size_1 / A_bestask_2
            size_3 = size_2 * B_bestbid_2
            amt_A = float(self.exchange_2.amount_to_precision(symbol_A,size_2))
            amt_B = float(self.exchange_2.amount_to_precision(symbol_B,size_2))
            amt_C = float(self.exchange_1.amount_to_precision(symbol_C,size_3))
            price_A = float(self.exchange_2.price_to_precision(symbol_A,A_bestask_2))
            price_B = float(self.exchange_2.price_to_precision(symbol_B,B_bestbid_2))
            price_C = float(self.exchange_1.price_to_precision(symbol_C,C_bestbid_1))
            win = size_3 * C_bestbid_1 - size_1
            if size_2 > min_amt_A2 and size_2 > min_amt_B2 and size_3 > min_amt_C1 and win > 0 and delay <= 95\
                and amt_A > 0 and amt_B > 0 and amt_C > 0 and price_A > 0 and price_B > 0 and price_C > 0:
                t = []
                order_result = []
                t.append(MyThread(self.CreatOrder, args=(symbol_A,2,'limit','buy' ,size_2,A_bestask_2,)))
                t.append(MyThread(self.CreatOrder, args=(symbol_B,2,'limit','sell',size_2,B_bestbid_2,)))
                t.append(MyThread(self.CreatOrder, args=(symbol_C,1,'limit','sell',size_3,C_bestbid_1,)))
                begin = time.time()
                for i in t:
                    i.setDaemon(True)
                    i.start()
                for i in t:
                    i.join()
                    order_result.append(i.get_result())
                end = time.time()
                delay_ = float((end - begin) // 0.001)
                self.log.debug("发现跨市221正循环信号！")
                self.log.debug("预估交易数量: %f  %f  %f" % (size_1, size_2, size_3))
                self.log.debug('in : %f  out : %f  win : %f' % (size_1,size_3 * C_bestbid_1, win))  # 先1 3  后2
                self.log.debug("价差比率:%f" % (Surplus_221))
                self.log.debug('询价延迟: %f ms' % delay )
                self.log.debug('下单延迟: %f ms' % delay_)
                self.log.debug('下单参数：')
                self.log.debug('A: %f %f %f %f' % (size_2, A_bestask_2, amt_A, price_A))
                self.log.debug('B: %f %f %f %f' % (size_2, B_bestbid_2, amt_B, price_B))
                self.log.debug('C: %f %f %f %f' % (size_3, C_bestbid_1, amt_C, price_C))
                self.log.debug('下单结果：')
                for i in order_result:
                    if 'id' not in i:
                        # self.log.debug('下单出错!')
                        # self.open_fail += 1
                        signal = False
                    else:
                        self.log.debug(i)
                self.CheckOpen(2,2,1,symbol_A,symbol_B,symbol_C,min_amt_A2, min_amt_B2, min_amt_C1)
                if signal:#判断是否按限价单成交，如果不是，则扯单后补市价单
                    self.open_num += 1
                self.log.debug('套利前币量之总和： %f %f %f' % (cur_size_11 + cur_size_21, cur_size_12 + cur_size_22, cur_size_13 + cur_size_23))
                total = (cur_size_11 + cur_size_21) + (cur_size_12 + cur_size_22) * (
                        0.5 * A_bestbid_1 + 0.5 * A_bestask_1) + (cur_size_13 + cur_size_23) * (
                                0.5 * C_bestask_1 + 0.5 * C_bestbid_1)
                self.log.debug('币量相当于%f个%s' % (total, X))
                cur_size_11, cur_size_12, cur_size_13, cur_size_21, cur_size_22, cur_size_23 = self.GetBalance(X, Y, Z)
                self.log.debug('套利后币量之总和： %f %f %f' % (cur_size_11 + cur_size_21, cur_size_12 + cur_size_22, cur_size_13 + cur_size_23))
                total_ = (cur_size_11 + cur_size_21) + (cur_size_12 + cur_size_22) * (
                        0.5 * A_bestbid_1 + 0.5 * A_bestask_1) + (cur_size_13 + cur_size_23) * (
                                0.5 * C_bestask_1 + 0.5 * C_bestbid_1)
                self.log.debug('币量相当于%f个%s' % (total_, X))
                self.win[X] += total_ - total
                return
            else:
                self.log.debug('有跨市221正循环信号，但不符合条件！')
                # self.log.debug('币1：%f 币2：%f 币3：%f A盘口：%f B盘口：%f C盘口：%f'%(cur_size_21, \
                #     cur_size_22 * A_bestask_2, cur_size_13 * C_bestbid_1, A_bestask_size_2 / A_bestask_2, \
                #     B_bestbid_size_2 * A_bestask_2, C_bestbid_size_1 * C_bestbid_1))
                hand = [cur_size_21, cur_size_22 * A_bestask_2, cur_size_13 * C_bestbid_1, A_bestask_size_2 / A_bestask_2, \
                    B_bestbid_size_2 * A_bestask_2, C_bestbid_size_1 * C_bestbid_1]
                n = hand.index(min(hand))
                if n == 0:
                    self.log.info('提示：交易所%s缺少%s' % (self.exchange_name_2, X))
                    self.signal_num += 1
                elif n == 1:
                    self.log.info('提示：交易所%s缺少%s' % (self.exchange_name_2, Y))
                    self.signal_num += 1
                elif n == 2:
                    self.log.info('提示：交易所%s缺少%s' % (self.exchange_name_1, Z))
                    self.signal_num += 1
                else:
                    self.log.debug('盘口深度不够')
                if win <= 0: self.log.debug('预估盈利太低')
                if delay > 95: self.log.debug('询价延迟过高!  %f ms' % delay)
                return
        if Deficit_122 > 1 and Deficit_122 < 1.01:# 逆2： C1  B2  A2
            size_1 = min(cur_size_11, cur_size_23 * C_bestask_1, cur_size_22 * A_bestbid_2, C_bestask_size_1 * C_bestask_1,
                             B_bestask_size_2 * B_bestask_2 * C_bestask_1, A_bestbid_2 * A_bestbid_size_2) * self.ratio
            size_2 = size_1 / C_bestask_1
            size_3 = size_2 / B_bestask_2
            amt_A = float(self.exchange_2.amount_to_precision(symbol_A,size_3))
            amt_B = float(self.exchange_2.amount_to_precision(symbol_B,size_3))
            amt_C = float(self.exchange_1.amount_to_precision(symbol_C,size_2))
            price_A = float(self.exchange_2.price_to_precision(symbol_A,A_bestbid_2))
            price_B = float(self.exchange_2.price_to_precision(symbol_B,B_bestask_2))
            price_C = float(self.exchange_1.price_to_precision(symbol_C,C_bestask_1))
            win = size_3 * A_bestbid_2 - size_1
            if size_3 > min_amt_A2 and size_3 > min_amt_B2 and size_2 > min_amt_C1 and win > 0 and delay <= 95\
                and amt_A > 0 and amt_B>0 and amt_C>0 and price_A>0 and price_B>0 and price_C>0:
                t = []
                order_result = []
                t.append(MyThread(self.CreatOrder, args=(symbol_C,1, 'limit', 'buy' , size_2, C_bestask_1,)))
                t.append(MyThread(self.CreatOrder, args=(symbol_B,2, 'limit', 'buy' , size_3, B_bestask_2,)))
                t.append(MyThread(self.CreatOrder, args=(symbol_A,2, 'limit', 'sell', size_3, A_bestbid_2,)))
                begin = time.time()
                for i in t:
                    i.setDaemon(True)
                    i.start()
                for i in t:
                    i.join()
                    order_result.append(i.get_result())
                end = time.time()
                delay_ = float((end - begin) // 0.001)
                self.log.debug("发现跨市122逆循环信号！")
                self.log.debug("预估交易数量: %f  %f  %f" % (size_1, size_2, size_3))
                self.log.debug('in : %f  out : %f   win : %f' % (size_1, size_3 * A_bestbid_2,win))
                self.log.debug("价差比率:%f" % (Deficit_122))
                self.log.debug('询价延迟: %f ms' % delay )
                self.log.debug('下单延迟: %f ms' % delay_)
                self.log.debug('下单参数：')
                self.log.debug('C: %f %f %f %f' % (size_2, C_bestask_1, amt_C, price_C))
                self.log.debug('B: %f %f %f %f' % (size_3, B_bestask_2, amt_B, price_B))
                self.log.debug('A: %f %f %f %f' % (size_3, A_bestbid_2, amt_A, price_A))
                self.log.debug('下单结果：')
                for i in order_result:
                    if 'id' not in i:
                        # self.log.debug('下单出错!')
                        # self.open_fail += 1
                        signal = False
                    else:
                        self.log.debug(i)
                self.CheckOpen(1,2,2,symbol_C,symbol_B,symbol_A,min_amt_C1, min_amt_B2, min_amt_A2)
                if signal: #判断是否按市价单成交
                    self.open_num += 1
                self.log.debug('套利前币量之总和： %f %f %f' % (cur_size_11 + cur_size_21, cur_size_12 + cur_size_22, cur_size_13 + cur_size_23))
                total = (cur_size_11 + cur_size_21) + (cur_size_12 + cur_size_22) * (
                        0.5 * A_bestbid_1 + 0.5 * A_bestask_1) + (cur_size_13 + cur_size_23) * (
                                0.5 * C_bestask_1 + 0.5 * C_bestbid_1)
                self.log.debug('币量相当于%f个%s' % (total, X))
                cur_size_11, cur_size_12, cur_size_13, cur_size_21, cur_size_22, cur_size_23 = self.GetBalance(X, Y, Z)
                self.log.debug('套利后币量之总和： %f %f %f' % (cur_size_11 + cur_size_21, cur_size_12 + cur_size_22, cur_size_13 + cur_size_23))
                total_ = (cur_size_11 + cur_size_21) + (cur_size_12 + cur_size_22) * (
                        0.5 * A_bestbid_1 + 0.5 * A_bestask_1) + (cur_size_13 + cur_size_23) * (
                                0.5 * C_bestask_1 + 0.5 * C_bestbid_1)
                self.log.debug('币量相当于%f个%s' % (total_, X))
                self.win[X] += total_ - total
                return
            else:
                self.log.debug('有跨市122逆循环信号，但不符合条件!')
                # self.log.debug('币1：%f 币2：%f 币3：%f C盘口：%f B盘口：%f A盘口：%f'%(cur_size_11, \
                #     cur_size_22 * A_bestbid_2, cur_size_23 * C_bestask_1, C_bestask_size_1 * C_bestask_1, \
                #     B_bestask_size_2 * B_bestask_2 * C_bestask_1, A_bestbid_2 * A_bestbid_size_2))
                hand = [cur_size_11, cur_size_22 * A_bestbid_2, cur_size_23 * C_bestask_1, C_bestask_size_1 * C_bestask_1, \
                    B_bestask_size_2 * B_bestask_2 * C_bestask_1, A_bestbid_2 * A_bestbid_size_2]
                n = hand.index(min(hand))
                if n == 0:
                    self.log.info('提示：交易所%s缺少%s' % (self.exchange_name_1, X))
                    self.signal_num += 1
                elif n == 1:
                    self.log.info('提示：交易所%s缺少%s' % (self.exchange_name_2, Y))
                    self.signal_num += 1
                elif n == 2:
                    self.log.info('提示：交易所%s缺少%s' % (self.exchange_name_2, Z))
                    self.signal_num += 1
                else:
                    self.log.debug('盘口深度不够')
                if win <= 0: self.log.debug('预估盈利太低')
                if delay > 95: self.log.debug('询价延迟过高!  %f ms' % delay)
                return
        if Surplus_A > 0 and Surplus_A < 0.01: # symbol A  1卖 2买     卖出主币 需要主币数量足够，买入主币需要计价货币足够，对于symbol_A主币是2，计价币是1
            size = min(cur_size_12, cur_size_21/A_bestask_2, A_bestbid_size_1, A_bestask_size_2) * self.ratio
            amt_1 = float(self.exchange_1.amount_to_precision(symbol_A,size))
            amt_2 = float(self.exchange_2.amount_to_precision(symbol_A,size))
            price_1 = float(self.exchange_1.price_to_precision(symbol_A, A_bestbid_1))
            price_2 = float(self.exchange_2.price_to_precision(symbol_A, A_bestask_2))
            win = size * Surplus_A
            if size > min_amt_A1 and size > min_amt_A2 and amt_1>0 and amt_2>0 and price_1>0 and price_2>0 and win > 0 and delay <= 95:
                t = []
                order_result = []
                t.append(MyThread(self.CreatOrder, args=(symbol_A,1,'limit','sell',size,A_bestbid_1,)))
                t.append(MyThread(self.CreatOrder, args=(symbol_A,2,'limit','buy' ,size,A_bestask_2,)))
                begin = time.time()
                for i in t:
                    i.setDaemon(True)
                    i.start()
                for i in t:
                    i.join()
                    order_result.append(i.get_result())
                end = time.time()
                delay_ = float((end - begin) // 0.001)
                self.log.debug("symbol_A发现正循环信号！")
                self.log.debug("预估交易数量: %f  %f" % (size,size))
                self.log.debug("预估交易价格: %f  %f" % (A_bestbid_1,A_bestask_2))
                self.log.debug('sell cost : %f  buy cost : %f  win : %f' %(size*A_bestbid_1,size*A_bestask_2,win))
                self.log.debug("价差比率:%f" % (Surplus_A))
                self.log.debug('询价延迟: %f ms' % delay )
                self.log.debug('下单延迟: %f ms' % delay_)
                self.log.debug('下单参数：')
                self.log.debug('A: %f %f %f %f' % (size, A_bestbid_1, amt_1, price_1))
                self.log.debug('B: %f %f %f %f' % (size, A_bestask_2, amt_2, price_2))
                self.log.debug('下单结果：')
                for i in order_result:
                    if 'id' not in i:
                        # self.log.debug('下单出错!')
                        # self.open_fail += 1
                        signal = False
                    else:
                        self.log.debug(i)
                self.CheckOpenBilateral(symbol_A,min_amt_A1,min_amt_A2)
                if signal:
                    self.open_num += 1
                self.log.debug('套利前币量之总和： %f %f %f' % (cur_size_11 + cur_size_21, cur_size_12 + cur_size_22, cur_size_13 + cur_size_23))
                total = (cur_size_11 + cur_size_21) + (cur_size_12 + cur_size_22) * (
                        0.5 * A_bestbid_1 + 0.5 * A_bestask_1) + (cur_size_13 + cur_size_23) * (
                                0.5 * C_bestask_1 + 0.5 * C_bestbid_1)
                self.log.debug('币量相当于%f个%s' % (total, X))
                cur_size_11, cur_size_12, cur_size_13, cur_size_21, cur_size_22, cur_size_23 = self.GetBalance(X, Y, Z)
                self.log.debug('套利后币量之总和： %f %f %f' % (cur_size_11 + cur_size_21, cur_size_12 + cur_size_22, cur_size_13 + cur_size_23))
                total_ = (cur_size_11 + cur_size_21) + (cur_size_12 + cur_size_22) * (
                        0.5 * A_bestbid_1 + 0.5 * A_bestask_1) + (cur_size_13 + cur_size_23) * (
                                0.5 * C_bestask_1 + 0.5 * C_bestbid_1)
                self.log.debug('币量相当于%f个%s' % (total_, X))
                self.win[X] += total_ - total
                return
            else:
                self.log.debug('symbol_A有正循环信号，但不符合条件！')
                # self.log.debug('余币：%f 余钱：%f 卖一量：%f 买一量：%f'%(cur_size_12, cur_size_21/A_bestask_2, A_bestbid_size_1, A_bestask_size_2))
                hand = [cur_size_12, cur_size_21/A_bestask_2, A_bestbid_size_1, A_bestask_size_2]
                n = hand.index(min(hand))
                if n == 0:
                    self.log.info('提示：交易所%s缺少%s' % (self.exchange_name_1, Y))
                    self.signal_num += 1
                elif n == 1:
                    self.log.info('提示：交易所%s缺少%s' % (self.exchange_name_2, X))
                    self.signal_num += 1
                else:
                    self.log.debug('盘口深度不够')
                self.log.debug('size: %f %f' % (size, size))
                self.log.debug('min_amt: %f %f' % (min_amt_A1, min_amt_A2))
                self.log.debug('amt: %f %f price: %f %f' % (amt_1, amt_2, price_1, price_2))
                if win <= 0: self.log.debug('预估盈利太低')
                if delay > 95: self.log.debug('询价延迟过高!  %f ms' % delay)
                return
        if Deficit_A > 0 and Deficit_A < 0.01:  # symbol A  1买 2卖  卖出主币 需要主币数量足够，买入主币需要计价货币足够，对于symbol_A主币是2，计价币是1
            size = min(cur_size_11/A_bestask_1, cur_size_22, A_bestask_size_1, A_bestbid_size_2) * self.ratio
            amt_1 = float(self.exchange_1.amount_to_precision(symbol_A,size))
            amt_2 = float(self.exchange_2.amount_to_precision(symbol_A,size))
            price_1 = float(self.exchange_1.price_to_precision(symbol_A,A_bestask_1))
            price_2 = float(self.exchange_2.price_to_precision(symbol_A,A_bestbid_2))
            win = size * Deficit_A
            if size> min_amt_A1 and size > min_amt_A2 and amt_1 >0 and amt_2 >0 and price_1>0 and price_2>0 and win > 0 and delay <= 95:
                t = []
                order_result = []
                t.append(MyThread(self.CreatOrder, args=(symbol_A,1,'limit','buy' ,size,A_bestask_1,)))
                t.append(MyThread(self.CreatOrder, args=(symbol_A,2,'limit','sell',size,A_bestbid_2,)))
                begin = time.time()
                for i in t:
                    i.setDaemon(True)
                    i.start()
                for i in t:
                    i.join()
                    order_result.append(i.get_result())
                end = time.time()
                delay_ = float((end - begin) // 0.001)
                self.log.debug("symbol_A发现逆循环信号！")
                self.log.debug("预估交易数量: %f  %f" % (size, size))
                self.log.debug("预估交易价格: %f  %f" % (A_bestask_1, A_bestbid_2))
                self.log.debug('buy cost : %f  sell cost : %f  win : %f' % (size*A_bestask_1,size*A_bestbid_2,win))
                self.log.debug("价差比率:%f" % (Deficit_A))
                self.log.debug('询价延迟: %f ms' % delay )
                self.log.debug('下单延迟: %f ms' % delay_)
                self.log.debug('下单参数：')
                self.log.debug('A: %f %f %f %f' % (size, A_bestask_1, amt_1, price_1))
                self.log.debug('B: %f %f %f %f' % (size, A_bestbid_2, amt_2, price_2))
                self.log.debug('下单结果：')
                for i in order_result:
                    if 'id' not in i:
                        # self.log.debug('下单出错!')
                        # self.open_fail += 1
                        signal = False
                    else:
                        self.log.debug(i)
                self.CheckOpenBilateral(symbol_A,min_amt_A1,min_amt_A2)
                if signal:
                    self.open_num += 1
                self.log.debug('套利前币量之总和： %f %f %f' % (cur_size_11 + cur_size_21, cur_size_12 + cur_size_22, cur_size_13 + cur_size_23))
                total = (cur_size_11 + cur_size_21) + (cur_size_12 + cur_size_22) * (
                        0.5 * A_bestbid_1 + 0.5 * A_bestask_1) + (cur_size_13 + cur_size_23) * (
                                0.5 * C_bestask_1 + 0.5 * C_bestbid_1)
                self.log.debug('币量相当于%f个%s' % (total, X))
                cur_size_11, cur_size_12, cur_size_13, cur_size_21, cur_size_22, cur_size_23 = self.GetBalance(X, Y, Z)
                self.log.debug('套利后币量之总和： %f %f %f' % (cur_size_11 + cur_size_21, cur_size_12 + cur_size_22, cur_size_13 + cur_size_23))
                total_ = (cur_size_11 + cur_size_21) + (cur_size_12 + cur_size_22) * (
                        0.5 * A_bestbid_1 + 0.5 * A_bestask_1) + (cur_size_13 + cur_size_23) * (
                                0.5 * C_bestask_1 + 0.5 * C_bestbid_1)
                self.log.debug('币量相当于%f个%s' % (total_, X))
                self.win[X] += total_ - total
                return
            else:
                self.log.debug('symbol_A有逆循环信号，但不符合条件!')
                # self.log.debug('余钱：%f 余币：%f 买一量：%f 卖一量：%f' % (cur_size_11/A_bestask_1, cur_size_22, A_bestask_size_1, A_bestbid_size_2))
                hand = [cur_size_11/A_bestask_1, cur_size_22, A_bestask_size_1, A_bestbid_size_2]
                n = hand.index(min(hand))
                if n == 0:
                    self.log.info('提示：交易所%s缺少%s' % (self.exchange_name_1, X))
                    self.signal_num += 1
                elif n == 1:
                    self.log.info('提示：交易所%s缺少%s' % (self.exchange_name_2, Y))
                    self.signal_num += 1
                else:
                    self.log.debug('盘口深度不够')
                self.log.debug('size: %f %f'%(size,size))
                self.log.debug('min_amt: %f %f'%(min_amt_A1,min_amt_A2))
                self.log.debug('amt: %f %f price: %f %f'%(amt_1,amt_2,price_1,price_2))
                if win <= 0: self.log.debug('预估盈利太低')
                if delay > 95: self.log.debug('询价延迟过高!  %f ms' % delay)
                return
        if Surplus_B > 0 and Surplus_B < 0.01: # symbol B  1卖 2买   卖出主币 需要主币数量足够，买入主币需要计价货币足够，对于symbol_B主币是2，计价币是3
            size = min(cur_size_12, cur_size_23/B_bestask_2, B_bestbid_size_1, B_bestask_size_2) * self.ratio
            amt_1 = float(self.exchange_1.amount_to_precision(symbol_B,size))
            amt_2 = float(self.exchange_2.amount_to_precision(symbol_B,size))
            price_1 = float(self.exchange_1.price_to_precision(symbol_B, B_bestbid_1))
            price_2 = float(self.exchange_2.price_to_precision(symbol_B, B_bestask_2))
            win = size * Surplus_B
            if size > min_amt_B1 and size > min_amt_B2 and amt_1>0 and amt_2>0 and price_1>0 and price_2>0 and win > 0 and delay <= 95:
                t = []
                order_result = []
                t.append(MyThread(self.CreatOrder, args=(symbol_B,1,'limit','sell',size,B_bestbid_1,)))
                t.append(MyThread(self.CreatOrder, args=(symbol_B,2,'limit','buy' ,size,B_bestask_2,)))
                begin = time.time()
                for i in t:
                    i.setDaemon(True)
                    i.start()
                for i in t:
                    i.join()
                    order_result.append(i.get_result())
                end = time.time()
                delay_ = float((end - begin) // 0.001)
                self.log.debug("symbol_B发现正循环信号！")
                self.log.debug("预估交易数量: %f  %f" % (size,size))
                self.log.debug("预估交易价格: %f  %f" % (B_bestbid_1,B_bestask_2))
                self.log.debug('sell cost : %f  buy cost : %f  win : %f' %(size*B_bestbid_1,size*B_bestask_2,win))
                self.log.debug("价差比率:%f" % (Surplus_B))
                self.log.debug('询价延迟: %f ms' % delay )
                self.log.debug('下单延迟: %f ms' % delay_)
                self.log.debug('下单参数：')
                self.log.debug('A: %f %f %f %f' % (size, B_bestbid_1, amt_1, price_1))
                self.log.debug('B: %f %f %f %f' % (size, B_bestask_2, amt_2, price_2))
                self.log.debug('下单结果：')
                for i in order_result:
                    if 'id' not in i:
                        # self.log.debug('下单出错!')
                        # self.open_fail += 1
                        signal = False
                    else:
                        self.log.debug(i)
                self.CheckOpenBilateral(symbol_B,min_amt_B1,min_amt_B2)
                if signal:
                    self.open_num += 1
                self.log.debug('套利前币量之总和： %f %f %f' % (cur_size_11 + cur_size_21, cur_size_12 + cur_size_22, cur_size_13 + cur_size_23))
                total = (cur_size_11 + cur_size_21) + (cur_size_12 + cur_size_22) * (
                        0.5 * A_bestbid_1 + 0.5 * A_bestask_1) + (cur_size_13 + cur_size_23) * (
                                0.5 * C_bestask_1 + 0.5 * C_bestbid_1)
                self.log.debug('币量相当于%f个%s' % (total, X))
                cur_size_11, cur_size_12, cur_size_13, cur_size_21, cur_size_22, cur_size_23 = self.GetBalance(X, Y, Z)
                self.log.debug('套利后币量之总和： %f %f %f' % (cur_size_11 + cur_size_21, cur_size_12 + cur_size_22, cur_size_13 + cur_size_23))
                total_ = (cur_size_11 + cur_size_21) + (cur_size_12 + cur_size_22) * (
                        0.5 * A_bestbid_1 + 0.5 * A_bestask_1) + (cur_size_13 + cur_size_23) * (
                                0.5 * C_bestask_1 + 0.5 * C_bestbid_1)
                self.log.debug('币量相当于%f个%s' % (total_, X))
                self.win[X] += total_ - total
                return
            else:
                self.log.debug('symbol_B有正循环信号，但不符合条件！')
                # self.log.debug('余币：%f 余钱：%f 卖一量：%f 买一量：%f'%(cur_size_12, cur_size_23/B_bestask_2, B_bestbid_size_1, B_bestask_size_2))
                hand = [cur_size_12, cur_size_23/B_bestask_2, B_bestbid_size_1, B_bestask_size_2]
                n = hand.index(min(hand))
                if n == 0:
                    self.log.info('提示：交易所%s缺少%s' % (self.exchange_name_1, Y))
                    self.signal_num += 1
                elif n == 1:
                    self.log.info('提示：交易所%s缺少%s' % (self.exchange_name_2, Z))
                    self.signal_num += 1
                else:
                    self.log.debug('盘口深度不够')
                self.log.debug('size: %f %f' % (size, size))
                self.log.debug('min_amt: %f %f' % (min_amt_B1, min_amt_B2))
                self.log.debug('amt: %f %f price: %f %f' % (amt_1, amt_2, price_1, price_2))
                if win <= 0: self.log.debug('预估盈利太低')
                if delay > 95: self.log.debug('询价延迟过高!  %f ms' % delay)
                return
        if Deficit_B > 0 and Deficit_B < 0.01:  #symbol B 1买 2卖   卖出主币 需要主币数量足够，买入主币需要计价货币足够，对于symbol_B主币是2，计价币是3
            size = min(cur_size_13/B_bestask_1, cur_size_22, B_bestask_size_1, B_bestbid_size_2) * self.ratio
            amt_1 = float(self.exchange_1.amount_to_precision(symbol_B,size))
            amt_2 = float(self.exchange_2.amount_to_precision(symbol_B,size))
            price_1 = float(self.exchange_1.price_to_precision(symbol_B,B_bestask_1))
            price_2 = float(self.exchange_2.price_to_precision(symbol_B,B_bestbid_2))
            win = size * Deficit_B
            if size> min_amt_B1 and size > min_amt_B2 and amt_1 >0 and amt_2 >0 and price_1>0 and price_2>0 and win > 0 and delay <= 95:
                t = []
                order_result = []
                t.append(MyThread(self.CreatOrder, args=(symbol_B,1,'limit','buy' ,size,B_bestask_1,)))
                t.append(MyThread(self.CreatOrder, args=(symbol_B,2,'limit','sell',size,B_bestbid_2,)))
                begin = time.time()
                for i in t:
                    i.setDaemon(True)
                    i.start()
                for i in t:
                    i.join()
                    order_result.append(i.get_result())
                end = time.time()
                delay_ = float((end - begin) // 0.001)
                self.log.debug("symbol_B发现逆循环信号！")
                self.log.debug("预估交易数量: %f  %f" % (size, size))
                self.log.debug("预估交易价格: %f  %f" % (B_bestask_1, B_bestbid_2))
                self.log.debug('buy cost : %f  sell cost : %f  win : %f' % (size*B_bestask_1,size*B_bestbid_2,win))
                self.log.debug("价差比率:%f" % (Deficit_B))
                self.log.debug('询价延迟: %f ms' % delay )
                self.log.debug('下单延迟: %f ms' % delay_)
                self.log.debug('下单参数：')
                self.log.debug('A: %f %f %f %f' % (size, B_bestask_1, amt_1, price_1))
                self.log.debug('B: %f %f %f %f' % (size, B_bestbid_2, amt_2, price_2))
                self.log.debug('下单结果：')
                for i in order_result:
                    if 'id' not in i:
                        # self.log.debug('下单出错!')
                        # self.open_fail += 1
                        signal = False
                    else:
                        self.log.debug(i)
                self.CheckOpenBilateral(symbol_B,min_amt_B1,min_amt_B2)
                if signal:
                    self.open_num += 1
                self.log.debug('套利前币量之总和： %f %f %f' % (cur_size_11 + cur_size_21, cur_size_12 + cur_size_22, cur_size_13 + cur_size_23))
                total = (cur_size_11 + cur_size_21) + (cur_size_12 + cur_size_22) * (
                        0.5 * A_bestbid_1 + 0.5 * A_bestask_1) + (cur_size_13 + cur_size_23) * (
                                0.5 * C_bestask_1 + 0.5 * C_bestbid_1)
                self.log.debug('币量相当于%f个%s' % (total, X))
                cur_size_11, cur_size_12, cur_size_13, cur_size_21, cur_size_22, cur_size_23 = self.GetBalance(X, Y, Z)
                self.log.debug('套利后币量之总和： %f %f %f' % (cur_size_11 + cur_size_21, cur_size_12 + cur_size_22, cur_size_13 + cur_size_23))
                total_ = (cur_size_11 + cur_size_21) + (cur_size_12 + cur_size_22) * (
                        0.5 * A_bestbid_1 + 0.5 * A_bestask_1) + (cur_size_13 + cur_size_23) * (
                                0.5 * C_bestask_1 + 0.5 * C_bestbid_1)
                self.log.debug('币量相当于%f个%s' % (total_, X))
                self.win[X] += total_ - total
                return
            else:
                self.log.debug('symbol_B有逆循环信号，但不符合条件!')
                # self.log.debug('余钱：%f 余币：%f 买一量：%f 卖一量：%f' % (cur_size_13/B_bestask_1, cur_size_22, B_bestask_size_1, B_bestbid_size_2))
                hand = [cur_size_13/B_bestask_1, cur_size_22, B_bestask_size_1, B_bestbid_size_2]
                n = hand.index(min(hand))
                if n == 0:
                    self.log.info('提示：交易所%s缺少%s' % (self.exchange_name_1, Z))
                    self.signal_num += 1
                elif n == 1:
                    self.log.info('提示：交易所%s缺少%s' % (self.exchange_name_2, Y))
                    self.signal_num += 1
                else:
                    self.log.debug('盘口深度不够')
                self.log.debug('size: %f %f'%(size,size))
                self.log.debug('min_amt: %f %f'%(min_amt_B1,min_amt_B2))
                self.log.debug('amt: %f %f price: %f %f'%(amt_1,amt_2,price_1,price_2))
                if win <= 0: self.log.debug('预估盈利太低')
                if delay > 95: self.log.debug('询价延迟过高!  %f ms' % delay)
                return
        if Surplus_C > 0 and Surplus_C < 0.01: # symbol_C 1卖 2买  卖出主币 需要主币数量足够，买入主币需要计价货币足够，对于symbol_C主币是3，计价币是1
            size = min(cur_size_13, cur_size_21/C_bestask_2, C_bestbid_size_1, C_bestask_size_2) * self.ratio
            amt_1 = float(self.exchange_1.amount_to_precision(symbol_C,size))
            amt_2 = float(self.exchange_2.amount_to_precision(symbol_C,size))
            price_1 = float(self.exchange_1.price_to_precision(symbol_C, C_bestbid_1))
            price_2 = float(self.exchange_2.price_to_precision(symbol_C, C_bestask_2))
            win = size * Surplus_C
            if size > min_amt_C1 and size > min_amt_C2 and amt_1>0 and amt_2>0 and price_1>0 and price_2>0 and win > 0 and delay <= 95:
                t = []
                order_result = []
                t.append(MyThread(self.CreatOrder, args=(symbol_C,1,'limit','sell',size,C_bestbid_1,)))
                t.append(MyThread(self.CreatOrder, args=(symbol_C,2,'limit','buy' ,size,C_bestask_2,)))
                begin = time.time()
                for i in t:
                    i.setDaemon(True)
                    i.start()
                for i in t:
                    i.join()
                    order_result.append(i.get_result())
                end = time.time()
                delay_ = float((end - begin) // 0.001)
                self.log.debug("symbol_C发现正循环信号！")
                self.log.debug("预估交易数量: %f  %f" % (size,size))
                self.log.debug("预估交易价格: %f  %f" % (C_bestbid_1,C_bestask_2))
                self.log.debug('sell cost : %f  buy cost : %f  win : %f' %(size*C_bestbid_1,size*C_bestask_2,win))
                self.log.debug("价差比率:%f" % (Surplus_C))
                self.log.debug('询价延迟: %f ms' % delay )
                self.log.debug('下单延迟: %f ms' % delay_)
                self.log.debug('下单参数：')
                self.log.debug('A: %f %f %f %f' % (size, C_bestbid_1, amt_1, price_1))
                self.log.debug('B: %f %f %f %f' % (size, C_bestask_2, amt_2, price_2))
                self.log.debug('下单结果：')
                for i in order_result:
                    if 'id' not in i:
                        # self.log.debug('下单出错!')
                        # self.open_fail += 1
                        signal = False
                    else:
                        self.log.debug(i)
                self.CheckOpenBilateral(symbol_C,min_amt_C1,min_amt_C2)
                if signal:
                    self.open_num += 1
                self.log.debug('套利前币量之总和： %f %f %f' % (cur_size_11 + cur_size_21, cur_size_12 + cur_size_22, cur_size_13 + cur_size_23))
                total = (cur_size_11 + cur_size_21) + (cur_size_12 + cur_size_22) * (
                        0.5 * A_bestbid_1 + 0.5 * A_bestask_1) + (cur_size_13 + cur_size_23) * (
                                0.5 * C_bestask_1 + 0.5 * C_bestbid_1)
                self.log.debug('币量相当于%f个%s' % (total, X))
                cur_size_11, cur_size_12, cur_size_13, cur_size_21, cur_size_22, cur_size_23 = self.GetBalance(X, Y, Z)
                self.log.debug('套利后币量之总和： %f %f %f' % (cur_size_11 + cur_size_21, cur_size_12 + cur_size_22, cur_size_13 + cur_size_23))
                total_ = (cur_size_11 + cur_size_21) + (cur_size_12 + cur_size_22) * (
                        0.5 * A_bestbid_1 + 0.5 * A_bestask_1) + (cur_size_13 + cur_size_23) * (
                                0.5 * C_bestask_1 + 0.5 * C_bestbid_1)
                self.log.debug('币量相当于%f个%s' % (total_, X))
                self.win[X] += total_ - total
                return
            else:
                self.log.debug('symbol_C有正循环信号，但不符合条件！')
                # self.log.debug('余币：%f 余钱：%f 卖一量：%f 买一量：%f'%(cur_size_13, cur_size_21/C_bestask_2, C_bestbid_size_1, C_bestask_size_2))
                hand = [cur_size_13, cur_size_21/C_bestask_2, C_bestbid_size_1, C_bestask_size_2]
                n = hand.index(min(hand))
                if n == 0:
                    self.log.info('提示：交易所%s缺少%s' % (self.exchange_name_1, Z))
                    self.signal_num += 1
                elif n == 1:
                    self.log.info('提示：交易所%s缺少%s' % (self.exchange_name_2, X))
                    self.signal_num += 1
                else:
                    self.log.debug('盘口深度不够')
                self.log.debug('size: %f %f' % (size, size))
                self.log.debug('min_amt: %f %f' % (min_amt_C1, min_amt_C2))
                self.log.debug('amt: %f %f price: %f %f' % (amt_1, amt_2, price_1, price_2))
                if win <= 0: self.log.debug('预估盈利太低')
                if delay > 95: self.log.debug('询价延迟过高!  %f ms' % delay)
                return
        if Deficit_C > 0 and Deficit_C < 0.01:  # symbol_C   1买 2卖    卖出主币 需要主币数量足够，买入主币需要计价货币足够，对于symbol_C主币是3，计价币是1
            size = min(cur_size_11/C_bestask_1, cur_size_23, C_bestask_size_1, C_bestbid_size_2) * self.ratio
            amt_1 = float(self.exchange_1.amount_to_precision(symbol_C,size))
            amt_2 = float(self.exchange_2.amount_to_precision(symbol_C,size))
            price_1 = float(self.exchange_1.price_to_precision(symbol_C,C_bestask_1))
            price_2 = float(self.exchange_2.price_to_precision(symbol_C,C_bestbid_2))
            win = size * Deficit_C
            if size> min_amt_C1 and size > min_amt_C2 and amt_1 >0 and amt_2 >0 and price_1>0 and price_2>0 and win > 0 and delay <= 95:
                t = []
                order_result = []
                t.append(MyThread(self.CreatOrder, args=(symbol_C,1,'limit','buy' ,size,C_bestask_1,)))
                t.append(MyThread(self.CreatOrder, args=(symbol_C,2,'limit','sell',size,C_bestbid_2,)))
                begin = time.time()
                for i in t:
                    i.setDaemon(True)
                    i.start()
                for i in t:
                    i.join()
                    order_result.append(i.get_result())
                end = time.time()
                delay_ = float((end - begin) // 0.001)
                self.log.debug("symbol_C发现逆循环信号！")
                self.log.debug("预估交易数量: %f  %f" % (size, size))
                self.log.debug("预估交易价格: %f  %f" % (C_bestask_1, C_bestbid_2))
                self.log.debug('buy cost : %f  sell cost : %f  win : %f' % (size*C_bestask_1,size*C_bestbid_2,win))
                self.log.debug("价差比率:%f" % (Deficit_C))
                self.log.debug('询价延迟: %f ms' % delay )
                self.log.debug('下单延迟: %f ms' % delay_)
                self.log.debug('下单参数：')
                self.log.debug('A: %f %f %f %f' % (size, C_bestask_1, amt_1, price_1))
                self.log.debug('B: %f %f %f %f' % (size, C_bestbid_2, amt_2, price_2))
                self.log.debug('下单结果：')
                for i in order_result:
                    if 'id' not in i:
                        # self.log.debug('下单出错!')
                        # self.open_fail += 1
                        signal = False
                    else:
                        self.log.debug(i)
                self.CheckOpenBilateral(symbol_C,min_amt_C1,min_amt_C2)
                if signal:
                    self.open_num += 1
                self.log.debug('套利前币量之总和： %f %f %f' % (cur_size_11 + cur_size_21, cur_size_12 + cur_size_22, cur_size_13 + cur_size_23))
                total = (cur_size_11 + cur_size_21) + (cur_size_12 + cur_size_22) * (
                        0.5 * A_bestbid_1 + 0.5 * A_bestask_1) + (cur_size_13 + cur_size_23) * (
                                0.5 * C_bestask_1 + 0.5 * C_bestbid_1)
                self.log.debug('币量相当于%f个%s' % (total, X))
                cur_size_11, cur_size_12, cur_size_13, cur_size_21, cur_size_22, cur_size_23 = self.GetBalance(X, Y, Z)
                self.log.debug('套利后币量之总和： %f %f %f' % (cur_size_11 + cur_size_21, cur_size_12 + cur_size_22, cur_size_13 + cur_size_23))
                total_ = (cur_size_11 + cur_size_21) + (cur_size_12 + cur_size_22) * (
                        0.5 * A_bestbid_1 + 0.5 * A_bestask_1) + (cur_size_13 + cur_size_23) * (
                                0.5 * C_bestask_1 + 0.5 * C_bestbid_1)
                self.log.debug('币量相当于%f个%s' % (total_, X))
                self.win[X] += total_ - total
                return
            else:
                self.log.debug('symbol_C有逆循环信号，但不符合条件!')
                # self.log.debug('余钱：%f 余币：%f 买一量：%f 卖一量：%f' % (cur_size_11/C_bestask_1, cur_size_23, C_bestask_size_1, C_bestbid_size_2))
                hand = [cur_size_11/C_bestask_1, cur_size_23, C_bestask_size_1, C_bestbid_size_2]
                n = hand.index(min(hand))
                if n == 0:
                    self.log.info('提示：交易所%s缺少%s' % (self.exchange_name_1, X))
                    self.signal_num += 1
                elif n == 1:
                    self.log.info('提示：交易所%s缺少%s' % (self.exchange_name_2, Z))
                    self.signal_num += 1
                else:
                    self.log.debug('盘口深度不够')
                self.log.debug('size: %f %f'%(size,size))
                self.log.debug('min_amt: %f %f'%(min_amt_C1,min_amt_C2))
                self.log.debug('amt: %f %f price: %f %f'%(amt_1,amt_2,price_1,price_2))
                if win <= 0: self.log.debug('预估盈利太低')
                if delay > 95: self.log.debug('询价延迟过高!  %f ms' % delay)
                return
        # self.log.debug('询价延迟: %f ms' % delay)
        return
        # self.CheckBalance()

    def HandleTick(self):
        # 打印基础信息
        self.log.info('--------------------')
        self.log.info('累计信号次数：%d' % self.signal_num)
        self.log.info('累计开仓次数：%d' % self.open_num)
        self.log.info('下单出错次数：%d' % self.open_fail)
        self.log.info('累计补单次数：%d' % self.maker_fail)
        self.log.info('累计出错次数：%d' % self.error_num)
        self.log.info('当前盈利约为: %f CNY' %(self.win['USDT']*6.9+self.win['BTC']*80000))
        self.log.info('====================')
        box = self.box
        # 对指定的币对进行检测套利机会 如果有机会就执行开仓  coin表示不同的中间币 计价币分别是usdt  btc  eth
        for coin in box[0]:
            self.CheckTraingle("USDT", coin, "BTC")
        for coin in box[1]:
            self.CheckTraingle("USDT", coin, "ETH")
        for coin in box[2]:
            self.CheckTraingle("BTC", coin, "ETH")
        # 采用多线程轮询无法发现交易机会，原因是线程过多导致卡顿，若开启此功能，需要服务器配置较高
        # 由于python GIT锁 多线程跑checktraingle这个函数性能很低 能用但是不够好
        # 更好的办法是用ws获取行情信息，存入内存数据库，然后在内存数据库中去搜索套利机会
        # t1 = []
        # t2 = []
        # t3 = []
        # result = []
        # box = self.box
        # for i in box[0]:
        #     t1.append(MyThread(self.CheckTraingle, args=("USDT", i, "BTC",)))
        # for i in box[1]:
        #     t2.append(MyThread(self.CheckTraingle, args=("USDT", i, "ETH",)))
        # for i in box[2]:
        #     t3.append(MyThread(self.CheckTraingle, args=("BTC", i, "ETH",)))
        # for t in [t1,t2,t3]:
        #     for i in t:
        #         i.setDaemon(True)
        #         i.start()
        #     for i in t:
        #         i.join()
        #         result.append(i.get_result())

    def run(self):
        # 初始化日志记录 self.log.info .error .warning ()
        self.InitLog()
        while True:
            try:
                self.ChooseExchange()  #实例化交易所
                self.GetTotalBalance() #获取账户信息
                self.markets_1 = self.exchange_1.fetch_markets() #获取交易对信息
                self.markets_2 = self.exchange_2.fetch_markets() #获取交易对信息
                self.fee_1 = self.exchange_1.fees  #获取手续费
                self.fee_2 = self.exchange_2.fees  #获取手续费
                self.HandleTick()  #主函数
                self.num += 1
            except Exception:
                self.log.error("警告!!! 出现错误!", exc_info=True)
                self.error_num += 1
                time.sleep(10)

if __name__ == '__main__':
    # 支持交易所列表： okex huobi binance fcoin gateio bitmex ...... 具体见https://github.com/ccxt/ccxt/wiki/Manual
    # fcoin
    exchange_name_1 = 'fcoin'   #在这里填入第一个交易所的名称
    api_key_1 = ''    #填入交易所1的apikey
    seceret_key_1 = ''   #填入交易所1的seceretkey
    fee_ratio_1 = 1   # 填入你的手续费比率，如果没有点卡就填1 ，如果有5折买的点卡，就填0.5，如果有3折买的点卡就填0.3
    passphrase_1 = ''   # password 大部分交易所不需要填这个，空着就行，okex必须填写
    # okex v3
    exchange_name_2 = 'okex3'
    api_key_2=''
    seceret_key_2=''
    fee_ratio_2 = 1
    passphrase_2 = ''
    # gateio
    exchange_name_3 = 'gateio'
    api_key_3=''
    seceret_key_3=''
    fee_ratio_3 = 1
    passphrase_3 = ''
    ###
    exchange_name = [exchange_name_1,exchange_name_2,exchange_name_3]
    api_key = [api_key_1,api_key_2,api_key_3]
    seceret_key = [seceret_key_1,seceret_key_2,seceret_key_3]
    passphrase = [passphrase_1,passphrase_2,passphrase_3]
    # 填写你要搬的币  1:usdt+btc+xxx  2:usdt+eth+xxx  3:btc+eth+xxx  计价币  usdx btc eth
    box1 = [['TRX','XLM','EOS','XRP','ETC','LTC'],['TRX','XLM','EOS','XRP','ETC','LTC'],['TRX','XLM','EOS','XRP','ETC','LTC']]  #举例：此处填写 fcoin okex 监控币对
    box2 = [['XLM','ETC','EOS'],['TRX','XLM','ETC','EOS'],['XLM','ETC','EOS']]   # fcoin gateio
    box3 = [['XLM','ETC','EOS'],['TRX','XLM','ETC','EOS'],['XLM','ETC','EOS']]   # okex gateio
    check_box = [box1,box2,box3]
    # 设置手续费比率 如果有点卡 则对手续费加上相应折扣
    fee_ratio_box = [fee_ratio_1,fee_ratio_2,fee_ratio_3]
    eat_ratio = 0.8   # 吃单比率，指吃掉多少深度，一般0.5~0.8，如果太高，可能会导致较多的滑点，如果太低，可能导致较低的开仓率
    ###  遍历顺序     1：交易所1+交易所2  2：交易所1+交易所3    3： 交易所2+交易所3
    bz = BanZhuanKing(exchange_name,api_key,seceret_key,passphrase,check_box,ratio=eat_ratio,fee_ratio_box=fee_ratio_box)  #实例化我们的策略
    bz.run()  #主线程开始运行策略