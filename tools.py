# -*- coding: utf-8 -*-
"""
Some tools useful in conjunction with the API, for example a Trade object.
"""
import csv
import json
import shutil
from collections import OrderedDict
from datetime import datetime, date, timezone
from decimal import Decimal

try:
    # noinspection PyUnresolvedReferences
    from pygments import highlight, lexers, formatters
    pygments_available = True
except ImportError:
    pygments_available = False


def prettify(data, use_colors=pygments_available, indent=4, newlines=True):
    """
    Prints a dict as prettily formatted json (with indents).
    Uses colors if available.
    @param data: Data to print as json.
    @type data: dict|list
    @param use_colors: If true, use colors. Default is True if pygments is installed.
    @type use_colors: bool
    @param indent: Number of spaces to indent.
    @type indent: int
    @param newlines: Use newlines if True.
    @type newlines: bool
    @return: formatted output
    @rtype: str
    """
    json_str = json.dumps(data, indent=indent)
    if not newlines:
        json_str = json_str.replace('\n', '')
    if use_colors and pygments_available:
        # noinspection PyUnresolvedReferences
        json_str = highlight(json_str.encode('utf8'),
                             lexers.JsonLexer(), formatters.TerminalFormatter())
    return json_str


def read_trades_from_file(filename):
    """
    Reads trades from a json or csv file.
    :param filename: Filename
    :type filename: str
    :return: trades
    :rtype: list
    """
    if filename.endswith(".csv"):
        return read_trades_from_csv_file(filename)
    else:
        return read_trades_from_json_file(filename)


def read_trades_from_json_file(filename):
    """
    Reads trades from a json file.
    :param filename: Filename
    :type filename: str
    :return: trades
    :rtype: list
    """
    return json.load(open(filename), object_pairs_hook=OrderedDict)
    # Strip API returns fields that are not trades (grrrr)
    # for key in ["success", "method"]: del result[key]
    # return result.values()


def read_trades_from_csv_file(filename):
    """
    Reads trades from a csv file.
    :param filename: Filename
    :type filename: str
    :return: trades
    :rtype: list
    """
    # "Type","Buy","Cur.","Buy value in USD","Sell","Cur.","Sell value in USD","Fee","Cur.","Exchange","Trade Date"
    # "type","buy_amount","buy_currency","buy_value_usd","sell_amount","sell_currency","sell_value_usd","fee_amount","fee_currency","exchange","time"
    # "Type","Buy","Cur.","Buy value in USD","Sell","Cur.","Sell value in USD","Fee","Cur.","Exchange","Imported From","Trade Group","Comment","Trade ID","Add Date","Trade Date"
    # "type","buy_amount","buy_currency","buy_value_usd","sell_amount","sell_currency","sell_value_usd","fee_amount","fee_currency","exchange","imported_from","group","comment","trade_id","imported_time","time"
    return csv.DictReader(open(filename, newline=''))


class Trade(object):
    """
    A trade object represents a single trade entry in cointracking's API.
    The object allows for hashing, sorting, comparing and the like.
    """

    # noinspection PyShadowingBuiltins
    def __init__(self, type, time, buy_currency, sell_currency, fee_currency,
                 buy_amount, sell_amount, fee_amount, exchange, trade_id, group, comment, imported_from, imported_time, buy_value_usd="", sell_value_usd=""):
        self.type = type.strip()
        if self.type == "Gift(Out)": self.type = "Gift"
        try:
            self.time = datetime.utcfromtimestamp(int(time.strip()))
        except:
            try:
                self.time = datetime.strptime(time, "%d.%m.%Y %H:%M")
            except:
                self.time = datetime.strptime(time, "%Y-%m-%dT%H:%M:%S")
        self.trade_id = trade_id.strip()
        # self.buy_amount = Decimal((buy_amount != "-" and buy_amount != "0.00000000" and buy_amount.strip()) or 0)
        # self.sell_amount = Decimal((sell_amount != "-" and sell_amount != "0.00000000" and sell_amount.strip()) or 0)
        # self.fee_amount = Decimal((fee_amount != "-" and fee_amount != "0.00000000" and fee_amount.strip()) or 0)
        # # self.buy_currency = (self.buy_amount != Decimal(0) and buy_currency.strip()) or ""
        # # self.sell_currency = (self.sell_amount != Decimal(0) and sell_currency.strip()) or ""
        # # self.fee_currency = (self.fee_amount != Decimal(0) and fee_currency.strip()) or ""
        # self.buy_currency = buy_currency.strip() or ""
        # self.sell_currency = sell_currency.strip() or ""
        # self.fee_currency = fee_currency.strip() or ""
        # self.buy_value_usd = Decimal((buy_value_usd != "0.00000000" and buy_value_usd.strip()) or 0)
        # self.sell_value_usd = Decimal((sell_value_usd != "0.00000000" and sell_value_usd.strip()) or 0)
        self.buy_amount = Decimal((buy_amount != "-" and buy_amount.strip()) or 0)
        self.sell_amount = Decimal((sell_amount != "-" and sell_amount.strip()) or 0)
        self.fee_amount = Decimal((fee_amount != "-" and fee_amount != "0.00000000" and fee_amount.strip()) or 0)
        # self.buy_currency = (self.buy_amount != Decimal(0) and buy_currency.strip()) or ""
        # self.sell_currency = (self.sell_amount != Decimal(0) and sell_currency.strip()) or ""
        # self.fee_currency = (self.fee_amount != Decimal(0) and fee_currency.strip()) or ""
        self.buy_currency = buy_currency.strip() or ""
        self.sell_currency = sell_currency.strip() or ""
        self.fee_currency = (self.fee_amount != Decimal(0) and fee_currency.strip()) or ""
        self.buy_value_usd = Decimal(buy_value_usd.strip() or 0)
        self.sell_value_usd = Decimal(sell_value_usd.strip() or 0)
        self.exchange = exchange.strip()
        self.group = group.strip()
        self.comment = comment.strip()
        self.imported_from = imported_from.strip()
        try:
            self.imported_time = datetime.utcfromtimestamp(int(imported_time.strip()))
        except:
            try:
                self.imported_time = datetime.strptime(imported_time, "%d.%m.%Y %H:%M")
            except:
                self.imported_time = datetime.strptime(imported_time, "%Y-%m-%dT%H:%M:%S")

    def __key(self):
        """
        We key data only by the relevant fields. Trade entries might be same but differ in non-relevant fields
        such as comment.
        :return: key
        """
        return (
            self.trade_id, self.type, self.time,
            self.buy_currency, self.sell_currency, self.fee_currency,
            self.buy_amount, self.sell_amount, self.fee_amount
        )

    def __eq__(self, other):
        if not isinstance(other, Trade):
            return NotImplemented
        return self.__key() == other.__key()

    def __hash__(self):
        return hash(self.__key())

    def __repr__(self):
        return str(self.__key())

    def __str__(self):
        return json.dumps(self.to_odict())

    def __lt__(self, other):
        return self.time < other.time

    def __gt__(self, other):
        return self.time > other.time

    def to_odict(self):
        """
        Returns trade data as an ordered dict. Used for dumping object attrs to string in order.
        :return:
        :rtype:
        """
        return OrderedDict([
            ('type', self.type),
            ('time', self.time.isoformat()),
            ('trade_id', self.trade_id),
            ('buy_currency', self.buy_currency),
            ('sell_currency', self.sell_currency),
            ('fee_currency', self.fee_currency),
            ('buy_amount', '{0:f}'.format(self.buy_amount)),
            ('sell_amount', '{0:f}'.format(self.sell_amount)),
            ('fee_amount', '{0:f}'.format(self.fee_amount)),
            ('buy_value_usd', '{0:f}'.format(self.buy_value_usd)),
            ('sell_value_usd', '{0:f}'.format(self.sell_value_usd)),
            ('exchange', self.exchange),
            ('group', self.group),
            ('comment', self.comment),
            ('imported_from', self.imported_from),
            ('imported_time', self.imported_time.isoformat()),
        ])


def convert_trade_objs(trades):
    """
    Converts trade dicts to Trade objects.
    :param trades: Trades as exported by cointracking.
    :type trades: list
    :return: Ordered list of objects.
    :rtype: list<Trade>
    """
    trade_objs = []
    for trade in trades:
        # Create trade object. Handle exceptions which mean that we hit an unexpected record.
        # try:
        trade_objs.append(Trade(**trade))
        # except Exception as e:
        #     print("Exception: {} for trade {}".format(str(e), str(trade)))
        #     print("Unexpected data? Skipping record.")

    return trade_objs