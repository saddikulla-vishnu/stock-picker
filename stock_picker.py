#!/usr/bin/env python3

import sys
import argparse
import os
import errno
import csv
from datetime import datetime
from collections import defaultdict
from difflib import get_close_matches
from functools import partial

if not sys.version_info >= (3, 4):
    sys.exit('Sorry, Python < 3.4 is not supported')
else:
    from pathlib import Path
    from itertools import accumulate
    from statistics import mean, stdev


class StockPicker:
    def __init__(self, *args, **kwargs):
        self._cache = {}
        self.stock_data = []
        self.stock_data_dict = {}

    def get_value_by_type(self, key, value):
        #  datetime_fmt = partial(datetime.strptime, value)
        trans_vals = {'StockName': str, 'StockDate': lambda x: datetime.strptime(x, '%d-%b-%Y'), 'StockPrice': float}
        _value = trans_vals.get(key, str)(value or self._cache.get(key, 0))
        if not value == '':  # Update the cache if the value is not empty
            self._cache.update({key: value})
        return _value

    def set_data_from_csv(self, csv_path):
        print('Reading Data from CSV...')
        stock_data = []
        with open(str(csv_path)) as f:
            try:
                stock_data = [{k: self.get_value_by_type(k, v) for k, v in row.items()} for row in csv.DictReader(
                    f, skipinitialspace=True)]
            except Exception as e:
                print('Unsupported filetype.')
                raise e
        print('Reading Data Done...')

        stock_data = sorted(stock_data, key=lambda x: x['StockDate'])

        stock_data_dict = defaultdict(list)
        for row in stock_data:  # Create a stock data dict grouped by stock_code for easy calculation
            stock_data_dict[row.get('StockName', '')].append(row)
        self.stock_data = stock_data
        self.stock_data_dict = stock_data_dict
        return stock_data, stock_data_dict

    def remaining_flow(self, stock_code):
        start_date = self.prompt_date(msg='"From which date you want to start. Eg: 20-Jan-2019":-\t')
        if not start_date:
            raise Exception('Too Many Wrong Attemts...')

        end_date = self.prompt_date(msg='"Till which date you want to analyze. Eg: 20-Jan-2019":-\t')
        if not end_date:
            raise Exception('Too Many Wrong Attemts...')

        stock_picker_stats = self.get_stats(stock_code, start_date, end_date)
        self.print_stats(stats_data=stock_picker_stats)
        return True

    def stock_picker_setup(self):
        stock_code = input('"Welcome Agent! Which stock you need to process?":-\t').upper()
        available_stock_codes = self.stock_data_dict.keys()

        if stock_code.upper() in available_stock_codes:
            success = self.remaining_flow(stock_code)
            return success
        else:
            close_matches = get_close_matches(stock_code, available_stock_codes, n=5, cutoff=0.5)
            if close_matches:
                for x in close_matches:
                    prompt = input('"Oops! Do you mean {}? [y] or n":-\t'.format(x)) or 'y'
                    if prompt == 'y':
                        stock_code = x
                        self.remaining_flow(stock_code)
                        break
            else:
                raise Exception('Stock Code is not even close. Please try again.')

    def prompt_date(self, msg=''):
        error_msg = ''
        for x in range(3):
            sdate = input(error_msg+msg) or None
            if sdate:
                try:
                    sdate = datetime.strptime(sdate, '%d-%b-%Y')
                    break
                except Exception as e:
                    error_msg = 'Something is Wrong. Please Enter the date again.\n'

        return sdate

    def get_highest_profits_data(self, stock_data=[]):
        print('Calculating Highest Profits....')
        stock_prices = [x['StockPrice'] for x in stock_data]
        _profit = _prev_profit = profit = mean_ = stdev_ = 0
        buy_date, sell_date = '', ''
        for idx, x in enumerate(stock_prices[:-1]):
            #  diff_prices = stock_prices[idx:idx+1]+[t-s for s, t in zip(stock_prices, stock_prices[idx+1:])]
            diff_prices = [x-stock_prices[idx] for x in stock_prices[idx+1:]]  # Price Growth list.
            cummulatives = list(accumulate(diff_prices[:]))  # Cummulative Sum of all profits.
            _profit = max(cummulatives)
            _sell_idx = idx + cummulatives.index(_profit) + 1
            if _profit > _prev_profit:
                buy_date = stock_data[idx]['StockDate']
                sell_date = stock_data[_sell_idx]['StockDate']
                profit = _profit
                _prev_profit = _profit

        try:
            mean_ = mean(stock_prices)
            stdev_ = stdev(stock_prices)
        except Exception as e:
            pass

        data = {
            'buy_date': buy_date, 'sell_date': sell_date, 'profit': profit, 'mean': mean_,
            'std': stdev_
        }
        print('Calculating Highest Done....')
        return data

    def get_stats(self, stock_code, start_date, end_date):
        #  stock_data, stock_data_dict, s
        stock_data = [row for row in self.stock_data_dict[stock_code]
                      if row['StockDate'] >= start_date and row['StockDate'] <= end_date]
        data = self.get_highest_profits_data(stock_data[:])
        _buy_date = data.get('buy_date')
        _buy_date = _buy_date.strftime('%d-%b-%Y') if _buy_date else "Don't buy"
        _sell_date = data.get('sell_date')
        _sell_date = _sell_date.strftime('%d-%b-%Y') if _sell_date else "Don't sell"
        stats = {
            'mean': data.get('mean') or 0, 'std': data.get('std') or 0, 'buy_date': _buy_date,
            'sell_date': _sell_date, 'profit': data.get('profit', 0)
        }
        return stats

    def print_stats(self, stats_data={}):
        #  print(
            #  '"Here is you result":-\tMean: {0[mean]}, Std: {0[std]},'
            #  ' Buy date: {0[buy_date]}, Sell date: {0[sell_date]}, Profit: Rs.{0[profit]}'.format(stats_data)
        #  )
        print(
            '"Here is you result":-\tMean: {mean:,.3f}, Std: {std:,.3f},'
            ' Buy date: {buy_date}, Sell date: {sell_date}, Profit: Rs. {profit:,.3f}'.format(**stats_data)
        )
        return True

    def get_csv_path(self):
        """
        Get the path of csv file
        """
        parser = argparse.ArgumentParser(description='Stock Picker')
        parser.add_argument('path', type=Path, help='Path to Stocks CSV')
        args = vars(parser.parse_args())
        csv_path = args.get('path')

        if not csv_path.exists():
            print('Not a Valid Path')
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), str(csv_path))
        elif not csv_path.is_file():
            print('Not a Valid File')
            raise IOError(errno.EIO, os.strerror(errno.EIO), str(csv_path))
        return csv_path


if __name__ == "__main__":
    try:
        stock_picker = StockPicker()
        csv_path = stock_picker.get_csv_path()
        stock_picker.set_data_from_csv(csv_path)
        while True:  # As long as there is no error, run stock picker program forever
            try:
                stock_picker.stock_picker_setup()
                prompt = input('Do you want to start over? ([y] or n):-\t') or 'y'
                if not prompt == 'y':
                    print('\nThank You for using Stock Picker...\n\n')
                    break
            except Exception as e:
                print(str(e))
                break
    except (FileNotFoundError, IOError) as e:  # As the program should not crash
        pass
    except Exception as e:  # As the program should not crash
        pass
