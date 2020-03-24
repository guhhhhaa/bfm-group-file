import pandas as pd
import asyncio
import websockets
import json
import nest_asyncio
import time
import verifyOptionTicker
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
nest_asyncio.apply()






async def call_api(msg):
   async with websockets.connect('wss://www.deribit.com/ws/api/v2') as websocket:
       #print(websocket)
       #<websockets.client.WebSocketClientProtocol object at 0x11ddeb2e8>
       await websocket.send(msg)
       while websocket.open:
           response = await websocket.recv()
           # do something with the response...
           #print(type(response))
           #print(response)
           return(response)
           
           
           

def getOptionInstrumentList():
    msg = \
    {
     "jsonrpc" : "2.0",
     "id" : 7627,
     "method" : "public/get_instruments",
     "params" : {
             "currency" : "BTC",
             "kind" : "option",
             "expired" : False
        }
    }
     
    loop=asyncio.get_event_loop()
    li_str=loop.run_until_complete(call_api(json.dumps(msg)))
    #loop.close()
    
    li_dict=json.loads(li_str)
    li_result=li_dict['result']
    sample_ticker=li_result[0]
    print('sample ticker:',(sample_ticker))
    #print(li_result[0].keys())
    ins_name=sample_ticker['instrument_name']
    names=ins_name.split('-')
    print('split sameple\'s name:',names)
    
    
    li_ins_names=[]
    for ticker in li_result:
        li_ins_names.append(ticker['instrument_name'])
    '''group_by_date={}
    for ticker in li_result:
        ins_name=ticker['instrument_name']
        names=ins_name.split('-')            
        if names[1] in group_by_date.keys():
            group_by_date[names[1]].append(ins_name)
        else:
            group_by_date.update({names[1]:[ins_name]})'''
    #for keys in group_by_date.keys():
    #    print(group_by_date[keys])
    #    break
    
    
    return li_ins_names
    




def getDeribitOptionTickers(num_per_loop=15,###整个来异步似乎有问题，分成部分
                           b_save_ticks=True,
                           b_verify=False#再次验证ticker完整性
                           ):
    li_ins_names=getOptionInstrumentList()
    #print(len(li_ins_names))
    tasks=[]
    for name in li_ins_names:
        tasks.append(call_api(json.dumps({"jsonrpc" : "2.0",
                                "id" : 8106,
                                "method" : "public/ticker",
                                "params" : {"instrument_name" : name}
                                })))
    #print(tasks)
    tickers_whole=[]
    
    
    for i in range(len(tasks)//num_per_loop+1):
        loop=asyncio.get_event_loop()
        sub_tasks=tasks[i*num_per_loop:(i+1)*num_per_loop]
        tickers= loop.run_until_complete(asyncio.gather(*sub_tasks))
        #loop.close()
        #print(type(tickers))###list
        if len(tickers)==num_per_loop:
            tickers_whole+=tickers
            print('成 功 获 取 %d tickers, iter #%d'%(len(tickers),i+1))
        elif i==len(tasks)//num_per_loop and len(tickers)==(len(tasks)%num_per_loop):#最后一个loop
            tickers_whole+=tickers
            print('成 功 获 取 %d tickers, iter #%d'%(len(tickers),i+1))
        else:
            print('#########    ticker有缺失或者谬误！1    ########')
            return False
        
    if len(tickers_whole)!=len(tasks):
        print('#########    ticker有缺失或者谬误！2    ########')
        return False
    else:
        print('所有option ticker都已经获得了')
    tickerd=dataframize([json.loads(tickers_whole[i])['result'] for i in range(len(tickers_whole))])
    tickerd['std_date']=pd.to_datetime(tickerd['exp_date'])
    tickerd=tickerd.sort_values(by=['std_date','strike','callput'])
    if b_save_ticks:
        now=time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))
        tickerd.to_csv('/Users/dansihong/spyder/Project_Option_volmap/csvs/'+'deribitOptionTicker_'+now+'.csv',index=False)
    if b_verify:
        verifyOptionTicker.sortAndShow(tickerd)
    return tickerd
def dataframize(li):
    #print(len(li))
    ins_name=li[0]['instrument_name'].split('-')
    df=pd.DataFrame({'instrument_name':li[0]['instrument_name'],'ask_iv':li[0]['ask_iv'],'bid_iv':li[0]['bid_iv'],'exp_date':ins_name[1],'strike':ins_name[2],'callput':ins_name[3]},index=[0])
    for i in range(1,len(li)):
        ins_name=li[i]['instrument_name'].split('-')
        df=df.append(pd.DataFrame({'instrument_name':li[i]['instrument_name'],'ask_iv':li[i]['ask_iv'],'bid_iv':li[i]['bid_iv'],'exp_date':ins_name[1],'strike':ins_name[2],'callput':ins_name[3]},index=[0]),ignore_index=True)
    #print(df)
    return df

def drawVolmap(b_uptodate=False,b_CP_ask=True,b_CP_bidask=True):
    if b_uptodate:
        df=getDeribitOptionTickers()
    else:
        df=pd.read_csv('//Users/dansihong/spyder/Project_Option_volmap/csvs/deribitOptionTicker_2019-11-10 23:08:22.csv')
    #print(type(df))
    
    #仅仅ask iv
    if b_CP_ask:
        target = pd.pivot_table(data = df ,
                            values = ['ask_iv'],
                            index = ['strike','callput'], 
                            columns = 'std_date')
        #print(target)
        #df1 = pd.DataFrame(data=[target.index,target])
        #print(type(df1))###dataframe
        #df1.to_csv('/Users/dansihong/spyder/Project_Option_volmap/csvs/pivot'+time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())))
        
        li=list(df.ask_iv.values)
        while 0 in li:
            li.remove(0)
        while np.nan in li:
            li.remove(np.nan)
        vmin=min(li)
        print('vmin other than 0 and nan:',vmin)
        
        plt.figure(figsize=(15,60), dpi= 70)
        ax = sns.heatmap(target, # 指定绘图数据
                 cmap='rainbow', # 指定填充色
                 linewidths=.1, # 设置每个单元方块的间隔
                 annot=True,
                 #robust=True,
                 vmax=200,
                 vmin=vmin# 显示数值
                )
    #ask+bid
    if b_CP_bidask:
        df1=df.copy()
        df1['bidask']=['bid' for i in range(len(df))]
        df1['iv']=df1['bid_iv']
        df2=df.copy()
        df2['bidask']=['ask' for i in range(len(df))]
        df2['iv']=df2['ask_iv']
        #print(df1)
        #print(df2)
        df1=df1.append(df2,ignore_index=True)
        d=df1
        #print(d)
        d=d.sort_values(by=['std_date','strike','callput','bidask'])
        d.reset_index(inplace=True,drop=True)
        target = pd.pivot_table(data = d ,
                            values = ['iv'],
                            index = ['strike','callput','bidask'], 
                            columns = 'std_date')
        #print(target)
        plt.figure(figsize=(15,60), dpi= 70)
        ax = sns.heatmap(target, # 指定绘图数据
                 cmap='rainbow', # 指定填充色
                 linewidths=.1, # 设置每个单元方块的间隔
                 annot=True # 显示数值
                )
if __name__=='__main__':
    #getDeribitOptionTickers()
    drawVolmap()
