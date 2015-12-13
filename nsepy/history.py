# -*- coding: utf-8 -*-
"""
Created on Tue Nov 24 21:25:54 2015

@author: Swapnil Jariwala
"""

from nsepy.urls import *
import six
from nsepy.commons import *
from nsepy.constants import *
from datetime import date, timedelta
from bs4 import BeautifulSoup
import pandas as pd
import six
import inspect
dd_mmm_yyyy = StrDate.default_format(format="%d-%b-%Y")
dd_mm_yyyy = StrDate.default_format(format="%d-%m-%Y")
EQUITY_SCHEMA = [str, str,
          dd_mmm_yyyy,
          float, float, float, float,
          float, float, float, int, float,
          int, int, float]
EQUITY_HEADERS = ["Symbol", "Series", "Date", "Prev Close", 
          "Open", "High", "Low","Last", "Close", "VWAP",
          "Volume", "Turnover", "Trades", "Deliverable Volume",
          "%Deliverble"]
EQUITY_SCALING = {"Turnover": 100000,
                  "%Deliverble": 0.01}
                  
FUTURES_SCHEMA = [str, dd_mmm_yyyy, dd_mmm_yyyy,
                  float, float, float, float,
                  float, float, int, float,
                  int, int, float]

FUTURES_HEADERS = ['Symbol', 'Date', 'Expiry',
                   'Open', 'High', 'Low', 'Close',
                   'Last', 'Settle Price', 'Number of Contracts', 'Turnover',
                   'Open Interest', 'Change in OI', 'Underlying']
FUTURES_SCALING = {"Turnover": 100000}

OPTION_SCHEMA = [str, dd_mmm_yyyy, dd_mmm_yyyy, str, float,
                 float, float, float, float,
                 float, float, int, float,
                 float, int, int, float]
OPTION_HEADERS = ['Symbol', 'Date', 'Expiry', 'Option Type', 'Strike Price',
                  'Open', 'High', 'Low', 'Close',
                  'Last', 'Settle Price', 'Number of Contracts', 'Turnover',
                  'Premium Turnover', 'Open Interest', 'Change in OI', 'Underlying']
OPTION_SCALING = {"Turnover": 100000,
                   "Premium Turnover": 100000}
                   

INDEX_SCHEMA = [dd_mmm_yyyy,
                float, float, float, float,
                int, float]
INDEX_HEADERS = ['Date',
                 'Open', 'High', 'Low', 'Close',
                 'Volume', 'Turnover']
INDEX_SCALING = {'Turnover': 10000000}

VIX_INDEX_SCHEMA = [dd_mmm_yyyy,
                    float, float, float, float, 
                    float, float, float]
VIX_INDEX_HEADERS = ['Date',
                     'Open', 'High', 'Low', 'Close',
                     'Previous', 'Change', '%Change']
VIX_SCALING = {'%Change': 0.01}        

INDEX_PE_SCHEMA = [dd_mmm_yyyy,
                   float, float, float]
INDEX_PE_HEADERS = ['Date', 'P/E', 'P/B', 'Div Yield']

"""
    symbol = "SBIN" (stock name, index name and VIX)
    start = date(yyyy,mm,dd)
    end = date(yyyy,mm,dd)
    index = True, False (True even for VIX)
    ---------------
    futures = True, False
    option_type = "CE", "PE", "CA", "PA"
    strike_price = integer number
    expiry_date = date(yyyy,mm,dd)

"""
def get_history(symbol, start, end, index=False, futures=False, option_type="",
                    expiry_date = None, strike_price="", series='EQ'):
    """This is the function to get the historical prices of any security (index,
        stocks, derviatives, VIX) etc.
        
        Args:
            symbol (str): Symbol for stock, index or any security
            start (datetime.date): start date
            end (datetime.date): end date
            index (boolean): False by default, True if its a index
            futures (boolean): False by default, True for index and stock futures
            expiry_date (datetime.date): Expiry date for derivatives, Compulsory for futures and options
            option_type (str): It takes "CE", "PE", "CA", "PA" for European and American calls and puts
            strike_price (int): Strike price, Compulsory for options
            series (str): Defaults to "EQ", but can be "BE" etc (refer NSE website for details)
        
        Returns:
            pandas.DataFrame : A pandas dataframe object 
            
        Raises:
            ValueError: 
                        1. strike_price argument missing or not of type int when options_type is provided
                        2. If there's an Invalid value in option_type, valid values-'CE' or 'PE' or 'CA' or 'CE'
                        3. If both futures='True' and option_type='CE' or 'PE'
    """
    frame = inspect.currentframe()
    args, _, _, kwargs = inspect.getargvalues(frame)
    del(kwargs['frame'])
    start = kwargs['start']
    end = kwargs['end']
    if (end - start) > timedelta(130):
        kwargs1 = dict(kwargs)
        kwargs2 = dict(kwargs)
        kwargs1['end'] = start + timedelta(130)
        kwargs2['start'] = kwargs1['end'] + timedelta(1)
        t1 = ThreadReturns(target=get_history, kwargs=kwargs1)
        t2 = ThreadReturns(target=get_history, kwargs=kwargs2)
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        return pd.concat((t1.result, t2.result))
    else:
        return get_history_quanta(**kwargs) 
        
    
    
def get_history_quanta(**kwargs):
    url, params, schema, headers, scaling = validate_params(**kwargs)
    df = url_to_df(url=url,
                   params=params,
                   schema=schema,
                   headers=headers, scaling=scaling)
    return df


def url_to_df(url, params, schema, headers, scaling={}):
    resp = url(**params)
    bs = BeautifulSoup(resp.text)
    tp = ParseTables(soup=bs,
                     schema=schema,
                     headers=headers, index="Date")
    df = tp.get_df()
    for key, val in six.iteritems(scaling):
        df[key] = val * df[key]
    return df
                    
"""
    symbol = "SBIN" (stock name, index name and VIX)
    start = date(yyyy,mm,dd)
    end = date(yyyy,mm,dd)
    index = True, False (True even for VIX)
    ---------------
    futures = True, False
    option_type = "CE", "PE", "CA", "PA"
    strike_price = integer number
    expiry_date = date(yyyy,mm,dd)

    
"""
def validate_params(symbol, start, end, index=False, futures=False, option_type="",
                    expiry_date = None, strike_price="", series='EQ'):
    params = {}
    
    
    if (futures and not option_type) or (not futures and option_type): #EXOR
        params['symbol'] = symbol
        params['dateRange'] = ''
        params['optionType'] = 'select'
        params['strikePrice'] = ''
        params['fromDate'] = start.strftime('%d-%b-%Y')
        params['toDate'] = end.strftime('%d-%b-%Y')
        url = derivative_history_url

       
        params['expiryDate'] = expiry_date.strftime("%d-%m-%Y")
        option_type = option_type.upper()
        if option_type in ("CE", "PE", "CA", "PA"):
            if not isinstance(strike_price,int):
                raise ValueError("strike_price argument missing or not of type int")
            #option specific
            if index: params['instrumentType'] = 'OPTIDX'
            else: params['instrumentType'] = 'OPTSTK'
            params['strikePrice'] = strike_price
            params['optionType'] = option_type
            schema = OPTION_SCHEMA
            headers = OPTION_HEADERS
            scaling = OPTION_SCALING
        elif option_type: 
            #this means that there's an invalid value in option_type
            raise ValueError("Invalid value in option_type, valid values-'CE' or 'PE' or 'CA' or 'CE'")
        else:
            # its a futures request
            if index:
                if symbol=='INDIAVIX': params['instrumentType'] = 'FUTIVX'
                else: params['instrumentType'] = 'FUTIDX'
            else: params['instrumentType'] = 'FUTSTK'            
            schema = FUTURES_SCHEMA
            headers = FUTURES_HEADERS
            scaling = FUTURES_SCALING
    elif futures and option_type: 
        raise ValueError("select either futures='True' or option_type='CE' or 'PE' not both")
    else: # its a normal request
        
        if index:
            if symbol=='INDIAVIX':
                params['fromDate'] = start.strftime('%d-%b-%Y')
                params['toDate'] = end.strftime('%d-%b-%Y')
                url = index_vix_history_url
                schema = VIX_INDEX_SCHEMA
                headers = VIX_INDEX_HEADERS
                scaling = VIX_SCALING
            else:
                if symbol in DERIVATIVE_TO_INDEX:
                    params['indexType'] = DERIVATIVE_TO_INDEX[symbol]
                else:
                    params['indexType'] = symbol
                params['fromDate'] = start.strftime('%d-%m-%Y')
                params['toDate'] = end.strftime('%d-%m-%Y')
                url = index_history_url
                schema = INDEX_SCHEMA
                headers = INDEX_HEADERS
                scaling = INDEX_SCALING
        else:
            params['symbol'] = symbol
            params['series'] = series
            params['symbolCount'] = get_symbol_count(symbol)
            params['fromDate'] = start.strftime('%d-%m-%Y')
            params['toDate'] = end.strftime('%d-%m-%Y')
            url = equity_history_url
            schema = EQUITY_SCHEMA
            headers = EQUITY_HEADERS
            scaling = EQUITY_SCALING
    
    return url, params, schema, headers, scaling
    
def get_index_pe_history(symbol, start, end):
    frame = inspect.currentframe()
    args, _, _, kwargs = inspect.getargvalues(frame)
    del(kwargs['frame'])
    start = kwargs['start']
    end = kwargs['end']
    if (end - start) > timedelta(130):
        kwargs1 = dict(kwargs)
        kwargs2 = dict(kwargs)
        kwargs1['end'] = start + timedelta(130)
        kwargs2['start'] = kwargs1['end'] + timedelta(1)
        t1 = ThreadReturns(target=get_index_pe_history, kwargs=kwargs1)
        t2 = ThreadReturns(target=get_index_pe_history, kwargs=kwargs2)
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        return pd.concat((t1.result, t2.result))
    else:
        return get_index_pe_history_quanta(**kwargs)

def get_index_pe_history_quanta(symbol, start, end):
    """This function will fetch the P/E, P/B and dividend yield for a given index
        
        Args:
            symbol (str): Symbol for stock, index or any security
            start (datetime.date): start date
            end (datetime.date): end date
        
        Returns:
            pandas.DataFrame : A pandas dataframe object 
    """
    if symbol in DERIVATIVE_TO_INDEX:
        index_name = DERIVATIVE_TO_INDEX[symbol]
    else:
        index_name = symbol
    resp = index_pe_history_url(indexName=index_name, 
                                fromDate=start.strftime('%d-%m-%Y'),
                                toDate=end.strftime('%d-%m-%Y'))
    
    bs = BeautifulSoup(resp.text)
    tp = ParseTables(soup=bs,
                     schema=INDEX_PE_SCHEMA,
                     headers=INDEX_PE_HEADERS, index="Date")
    df = tp.get_df()
    return df