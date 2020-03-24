#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Oct 27 19:04:47 2019

@author: dansihong
"""

import json


class okex:
    ex = None
    quote_currency = 'USDT'
    init_money = 0
    all_tickers = []
    all_prices = {}
    all_prices_usdt = {}
    quote_currency_usdt_price = 1  # 基础货币对USDT价格
    is_hide_zero = 1  # 隐藏0余额
    min_display_money = 1  # 最小显示金额，单位（USDT）
    g_risk_margin_alarm_line = 130  # 杠杆风险率预警阈值%
    baocang_line = 10  # 期货爆仓价逼近10%报警
    risk_margin = []  # 杠杆风险率预警
    risk_cangwei = []
    risk_baocang = []

    def __init__(self, risk=130, baocang_line=10):
        self.g_risk_margin_alarm_line = float(risk)
        self.baocang_line = float(baocang_line)
        # 必须重置高级类变量！否则将延续之前的值！
        self.all_tickers = []
        self.all_prices = {}
        self.all_prices_usdt = {}
        self.risk_margin = []  # 杠杆风险率预警
        self.risk_cangwei = []
        self.risk_baocang = []

    # 读取报价
    def set_all_tickers(self, tickers):
        self.all_tickers = tickers
        return
    
    # v2 获取总权益
    def get_acc_total_value(self, ex):
        self.ex = ex
        self.quote_currency = 'USDT'
        self.init_money = 0
        self.init_prices()
        acc_coins = 'BTC,LTC,ETH,ETC,XRP,EOS,BCH,BSV,TRX';
        return [
            self.get_wallet_account()[5],
            self.get_spot_account()[5],
            self.get_margin_account()[5],
            self.get_future_account(acc_coins)[5],
            self.get_swap_account(acc_coins)[5]
        ]
    
    # v2 风险为0
    def lowerRiskToZero(self):
        # @see ext.RiskForceCover
        return True;
    
    # read account info
    def get_acc_info(self, ex, quote_currency, init_money, acc_coins):
        self.ex = ex
        self.quote_currency = quote_currency
        self.init_money = init_money
        self.init_prices()
        return [
            self.get_wallet_account(),
            self.get_spot_account(),
            self.get_margin_account(),
            self.get_future_account(acc_coins),
            self.get_swap_account(acc_coins)
        ]

    # init prices
    def init_prices(self):
        global _C
        if len(self.all_tickers) > 0:
            all_tickers = self.all_tickers
        else:
            # Log('init_prices')
            all_tickers = _C(self.ex.IO, 'api', 'GET', '/api/spot/v3/instruments/ticker')
        spot_quote = self.quote_currency
        all_prices = {}
        all_prices_usdt = {}
        quote_currency_usdt_price = 1  # 基础货币对USDT价格
        all_prices[spot_quote] = 1  # 基础货币
        for ticker in all_tickers:
            coin, quote = ticker.instrument_id.split('-')
            if coin == spot_quote and quote == 'USDT':  # 提取基础货币美元报价
                quote_currency_usdt_price = float(ticker.last)
            if quote == spot_quote:
                all_prices[coin] = float(ticker.last)  # 最新价
            if quote == 'USDT':
                all_prices_usdt[coin] = float(ticker.last)  # 最新价
        # 如果基础货币不是USDT，则要转化
        if spot_quote != 'USDT':
            self.min_display_money = 1 / quote_currency_usdt_price
        self.all_prices = all_prices  # assoc
        self.all_prices_usdt = all_prices_usdt  # assoc
        self.quote_currency_usdt_price = quote_currency_usdt_price  # float

    # 获取本位报价
    def get_coin_price(self, coin):
        if coin in self.all_prices:
            return float(self.all_prices[coin])
        elif coin in self.all_prices_usdt:
            return float(self.all_prices_usdt[coin]) * float(self.quote_currency_usdt_price)
        else:
            return 0.00

    # wallet account
    def get_wallet_account(self):
        # api
        # Log('get_wallet_account')
        wallet = _C(self.ex.IO, 'api', 'GET', '/api/account/v3/wallet')  # list
        Sleep(200)
        balances = []
        total_value = 0
        exlabel = ext.php.strval(self.ex.GetLabel())
        # construct
        for wlt in wallet:
            if float(wlt.balance) > 0:  # 过滤零余额
                coin_price = self.get_coin_price(wlt.currency)
                voa = float(coin_price) * float(wlt.balance)
                total_value += voa
                if voa > self.min_display_money:  # 隐藏小余额
                    balances.append([
                        exlabel + ' ' + wlt.currency,
                        wlt.balance,
                        wlt.available,
                        wlt.hold,
                        format(voa, '0.2f'),  # 市值
                    ])
        # 排序-倒序
        balances = sorted(balances, key=lambda x: float(x[4]), reverse=True)
        total_value_usdt = total_value * self.quote_currency_usdt_price
        # data
        return ["资金账户(余额>0)", '币种,余额,可用,冻结,市值', balances, 'wallet', total_value, total_value_usdt]

    # spot 币币账户
    def get_spot_account(self):
        # api
        # Log('get_spot_account')
        wallet = _C(self.ex.IO, 'api', 'GET', '/api/spot/v3/accounts')  # list
        Sleep(200)
        balances = []
        total_value = 0
        exlabel = ext.php.strval(self.ex.GetLabel())
        # construct
        for wlt in wallet:
            if float(wlt.balance) > 0:  # 过滤零余额
                coin_price = self.get_coin_price(wlt.currency)
                voa = coin_price * float(wlt.balance)
                total_value += voa
                if voa > self.min_display_money:  # 隐藏小余额
                    balances.append([
                        exlabel + ' ' + wlt.currency,
                        wlt.balance,
                        wlt.available,
                        wlt.hold,
                        format(voa, '0.2f'),  # 市值
                    ])
        # 排序-倒序
        balances = sorted(balances, key=lambda x: float(x[4]), reverse=True)
        # data
        total_value_usdt = total_value * self.quote_currency_usdt_price
        return ["币币账户(余额>0)", '币种,余额,可用,冻结,市值', balances, 'spot', total_value, total_value_usdt]

    # 币币杠杆账户
    def get_margin_account(self):
        # api
        # Log('get_margin_account')
        wallet = _C(self.ex.IO, 'api', 'GET', '/api/margin/v3/accounts')  # list
        Sleep(200)
        balances = []
        risk_margin_list = []
        total_value = 0
        exlabel = ext.php.strval(self.ex.GetLabel())
        # construct
        for wlt in wallet:
            coin, quote = wlt.instrument_id.split('-')
            coinkey = 'currency:' + coin
            quoteCoinKey = 'currency:' + quote
            if float(wlt[quoteCoinKey].balance) > 0 or float(wlt[coinkey].balance) > 0:
                coin_price = self.get_coin_price(coin)
                quote_price = self.get_coin_price(quote)
                wlt_value = (
                        (float(wlt[coinkey].balance) - float(wlt[coinkey].borrowed) - float(
                            wlt[coinkey].lending_fee)) * coin_price
                        + (float(wlt[quoteCoinKey].balance) - float(wlt[quoteCoinKey].borrowed) - float(
                    wlt[quoteCoinKey].lending_fee)) * quote_price
                )
                margin_ratio = float(wlt.margin_ratio) * 100 if wlt.margin_ratio else 0
                margin_row = [
                    exlabel + ' ' + wlt.instrument_id,
                    wlt_value,
                    wlt[quoteCoinKey].balance,
                    wlt[quoteCoinKey].borrowed,
                    wlt[quoteCoinKey].available,
                    wlt[coinkey].balance,
                    wlt[coinkey].borrowed,
                    wlt[coinkey].available,
                    margin_ratio,  # 低于130%报警，低于110%强平
                    wlt.liquidation_price,
                ]
                balances.append(margin_row)
                if margin_ratio > 0 and margin_ratio <= self.g_risk_margin_alarm_line:
                    risk_margin_list.append(margin_row)
                total_value += wlt_value
        # 排序-倒序
        balances = sorted(balances, key=lambda x: x[4], reverse=True)
        total_value_usdt = total_value * self.quote_currency_usdt_price
        # risk margin
        self.risk_margin = risk_margin_list
        # data
        cols_title = '币种,权益,钱余额,已借钱,可用钱,币余额,已借币,可用币,风险率,爆仓价'
        return ["币币杠杆账户", cols_title, balances, 'margin', total_value, total_value_usdt]

    # 交割合约账户
    def get_future_account(self, acc_coins):
        # api
        cols_title = "名称,账户权益,可用,仓位,均价,利润,多空,合约类型,预估爆仓价"
        # wallet = []
        # accounts = {}
        balances = []  # 含全仓模式、逐仓模式
        total_value = 0
        # saved_futures_accounts = {}  # 单个合约账户信息列表
        exlabel = ext.php.strval(self.ex.GetLabel())
        self.ex.SetContractType('quarter')  # 取消指定合约类型，这样就可以显示全部
        # wallet = _C(self.ex.IO, 'api', 'GET', '/api/futures/v3/position')['holding']  # {holding:list}
        if acc_coins == '' or not acc_coins:
            Log("交割合约未指定币种！#ff0000")
            return ["交割合约", cols_title, [], 'future', 0]
        for _coin in acc_coins.strip().split(','):
            # 标记价格：/api/futures/v3/instruments/BTC-USD-180309/mark_price
            '''{
    "mark_price":"3.591",
    "instrument_id":"EOS-USD-190628",
    "timestamp":"2019-03-22T06:28:53.208Z"
}'''

            coin = _coin.upper()
            # Log('get_future_account 1')
            futures_account = _C(self.ex.IO, 'api', 'GET', '/api/futures/v3/accounts/' + coin)  # 限速规则：20次/2s
            Sleep(600)
            coin_price = self.get_coin_price(coin)
            coin_value = float(futures_account.equity) * coin_price
            total_value += coin_value
            acc = [
                # "名称,账户权益,可用,仓位,均价,利润,多空,合约类型,预估爆仓价";
                exlabel + ' ' + coin,
                futures_account.equity,
                futures_account.total_avail_balance,
                0,
                0,
                0,
                '',
                '币种小计',
                0,
            ]
            balances.append(acc)
            # 逐个查询持仓
            _C(self.ex.IO, 'currency', coin)
            # Log('get_future_account 1.5')
            positions = _C(self.ex.GetPosition)
            # Log("positions %s" % coin, json.dumps(positions))
            Sleep(200)
            if len(positions) > 0:
                for pos in positions:
                    wlt = pos['Info']
                    long_short = 'long' if pos.Type == PD_LONG else 'short'
                    # if 'contracts' in futures_account and isinstance(futures_account['contracts'], list):
                    #     Log(futures_account)
                    # accounts[coin] = futures_account
                    # saved_futures_accounts[coin] = futures_account
                    # coin_price = self.get_coin_price(coin)
                    # total_value += (float(futures_account.equity) * coin_price)
                    # for ctt in futures_account['contracts']:
                    #     wlt = _C(self.ex.IO, 'api', 'GET', '/api/futures/v3/%s/position' % ctt.instrument_id)  # 限速规则：20次/2s
                    #     Log("%s %s wlt:" % (exlabel, coin), wlt)
                    #     Sleep(100)  # 调用接口后要适当延时
                    # Log('wlt %s' % coin, wlt)
                    mark_price = 0
                    # if int(wlt.long_qty) > 0 or int(wlt.short_qty) > 0:
                    if pos.Amount > 0:
                        # Log('get_future_account 2')
                        mpr = _C(self.ex.IO, 'api', 'GET',
                                 '/api/futures/v3/instruments/%s/mark_price' % wlt.instrument_id)
                        Sleep(100)
                        mark_price = float(mpr.mark_price)
                        if long_short == 'long':
                            baocang_price = wlt.liquidation_price if wlt.margin_mode == 'crossed' else wlt.long_liqui_price
                            acc_long = [
                                # "名称,账户权益,可用,仓位,均价,利润,多空,合约类型,预估爆仓价"
                                exlabel + ' ' + coin,
                                futures_account['equity'],
                                futures_account['total_avail_balance'],
                                wlt.long_qty,
                                wlt.long_avg_cost,
                                wlt.long_pnl,
                                'long',
                                wlt.instrument_id,
                                baocang_price,
                            ]
                            balances.append(acc_long)

                            # 爆仓预警
                            diff_rate = abs(float(mark_price) - float(baocang_price)) / float(mark_price) * 100
                            if float(baocang_price) > 0 and diff_rate < self.baocang_line:
                                self.risk_baocang.append(acc_long + [mark_price, diff_rate])  # 补充标记价格[9,10]
                        else:
                            baocang_price = wlt.liquidation_price if wlt.margin_mode == 'crossed' else wlt.short_liqui_price
                            acc_short = [
                                # "名称,账户权益,可用,仓位,均价,利润,多空,合约类型,预估爆仓价"
                                exlabel + ' ' + coin,
                                futures_account['equity'],
                                futures_account['total_avail_balance'],
                                wlt.short_qty,
                                wlt.short_avg_cost,
                                wlt.short_pnl,
                                'short',
                                wlt.instrument_id,
                                baocang_price,
                            ]
                            balances.append(acc_short)
                            # 爆仓预警
                            # Log('self.baocang_line', self.baocang_line)
                            diff_rate = abs(float(mark_price) - float(baocang_price)) / float(mark_price) * 100
                            if float(baocang_price) > 0 and diff_rate < self.baocang_line:  # 逼近爆仓价，考虑到全仓模式爆仓价可能是低于现价的
                                self.risk_baocang.append(acc_short + [mark_price, diff_rate])  # 补充标记价格[9,10]
        # Log(exlabel, balances)
        # construct
        # for wlt0 in wallet:
        #     for wlt in wlt0:  # 二维数组
        #         coin, quote, due_date = wlt.instrument_id.split('-')
        #         # merge with account info
        #
        #
        #         acc_long = [
        #             # "名称,账户权益,可用,仓位,均价,利润,多空,合约类型,预估爆仓价"
        #             exlabel + ' ' + coin,
        #             futures_account.equity,
        #             futures_account.total_avail_balance,
        #             wlt.long_qty,
        #             wlt.long_avg_cost,
        #             wlt.long_pnl,
        #             'long',
        #             wlt.instrument_id,
        #             wlt.liquidation_price if wlt.margin_mode == 'crossed' else wlt.long_liqui_price,
        #         ]
        #         acc_short = [
        #             # "名称,账户权益,可用,仓位,均价,利润,多空,合约类型,预估爆仓价"
        #             exlabel + ' ' + coin,
        #             futures_account.equity,
        #             futures_account.total_avail_balance,
        #             wlt.short_qty,
        #             wlt.short_avg_cost,
        #             wlt.short_pnl,
        #             'short',
        #             wlt.instrument_id,
        #             wlt.liquidation_price if wlt.margin_mode == 'crossed' else wlt.short_liqui_price,
        #         ]
        #         balances.append(acc_long)
        #         balances.append(acc_short)
        # data
        total_value_usdt = total_value * self.quote_currency_usdt_price
        return ["交割合约", cols_title, balances, 'future', total_value, total_value_usdt]

    # 永续合约账户
    def get_swap_account(self, acc_coins):
        global Log, Sleep
        # api
        cols_title = "名称,账户权益,可用,仓位,均价,利润,多空,合约类型,预估爆仓价"
        if acc_coins == '' or not acc_coins:
            Log("永续合约未指定币种！#ff0000")
            return ["永续合约", cols_title, [], 'swap', 0]

        # BEGIN
        balances = []  # 含全仓模式、逐仓模式
        total_value = 0
        exlabel = ext.php.strval(self.ex.GetLabel())
        for _coin in acc_coins.strip().split(','):
            coin = _coin.upper()
            # 获取账户
            # _C(self.ex.IO, 'currency', coin+'_USD')
            # _acc = _C(self.ex.GetAccount)
            # Log('get_swap_account 1')
            _acc = _C(self.ex.IO, 'api', 'GET', '/api/swap/v3/%s-USD-SWAP/accounts' % coin)
            # Log("_acc %s" % coin, json.dumps(_acc))
            Sleep(100)  # 调用接口后要适当延时
            coin_price = self.get_coin_price(coin)
            coin_value = float(_acc.info.equity) * coin_price
            total_value += coin_value
            acc = [
                # "名称,账户权益,可用,仓位,均价,利润,多空,合约类型,预估爆仓价";
                exlabel + ' ' + coin,
                _acc.info.equity,
                _acc.info.total_avail_balance,
                0,
                0,
                0,
                '',
                '币种小计',
                0,
            ]
            balances.append(acc)  # 币种小计
            mark_price = 0
            if float(_acc.info.equity) > 0:
                # {
                #     "instrument_id":"BTC-USD-SWAP",
                #     "mark_price":"3914.3",
                #     "timestamp":"2019-03-26T03:33:50.064Z"
                # }
                # 标记价格 /api/swap/v3/instruments/BTC-USD-SWAP/mark_price
                # # 爆仓价趋近标记价格10%报警
                # Log('get_swap_account 2')
                mpr = _C(self.ex.IO, 'api', 'GET', '/api/swap/v3/instruments/%s-USD-SWAP/mark_price' % coin)
                Sleep(100)
                mark_price = float(mpr.mark_price)
            # 获取持仓
            # positions = _C(self.ex.GetPosition)
            # wlt = _C(self.ex.IO, 'api', 'GET', '/api/swap/v3/%s-USD-SWAP/position' % coin)
            # Log('get_swap_account 3')
            ret = _C(self.ex.IO, 'api', 'GET', '/api/swap/v3/%s-USD-SWAP/position' % coin)
            positions = ret.holding
            Sleep(100)  # 调用接口后要适当延时
            for pos in positions:
                acc = [
                    # "名称,账户权益,可用,仓位,均价,利润,多空,合约类型,预估爆仓价";
                    exlabel + ' ' + coin + ' ' + ret.margin_mode,
                    _acc.info.equity,
                    _acc.info.total_avail_balance,
                    pos.position,
                    pos.avg_cost,
                    pos.realized_pnl,
                    pos.side,
                    pos.instrument_id,
                    pos.liquidation_price,
                ]
                balances.append(acc)
                # 爆仓预警
                if float(pos.liquidation_price) > 0 and float(mark_price) > 0 \
                        and abs(float(mark_price) - float(pos.liquidation_price)) < float(
                    mark_price) * self.baocang_line / 100:
                    diff_rate = abs(float(mark_price) - float(pos.liquidation_price)) / float(mark_price) * 100
                    self.risk_baocang.append(acc + [mark_price, diff_rate])  # 补充标记价格[9, 10]
        total_value_usdt = total_value * self.quote_currency_usdt_price
        return ["永续合约", cols_title, balances, 'swap', total_value, total_value_usdt]


global ext
ext.okex = okex

