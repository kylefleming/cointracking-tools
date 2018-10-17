# -*- coding: utf-8 -*-
import csv
import json
import sys
from collections import OrderedDict
from dateutil.relativedelta import relativedelta
from tools import read_trades_from_file, convert_trade_objs


if len(sys.argv) != 3:
    print(f"Usage: {sys.argv[0]} <json_or_csv_file> <output_csv>")
    exit(1)

trade_objs = sorted(convert_trade_objs(read_trades_from_file(sys.argv[1])))

class Transaction(object):
    def __init__(self, amount, buy_basis, sell_basis, buy_trade, sell_trade, comment=""):
        self.amount = amount
        self.buy_basis = buy_basis
        self.sell_basis = sell_basis
        self.buy_trade = buy_trade
        self.sell_trade = sell_trade
        self.comment = comment

    def __str__(self):
        return str(self.to_odict())

    def __repr__(self):
        return json.dumps(self.to_odict())

    fieldnames = ['amount', 'currency', 'basis', 'proceeds', 'gain', 'buy_time', 'sell_time', 'tax_year', 'time_held', 'is_long', 'buy_exchange', 'sell_exchange', 'comment']

    def to_odict(self):
        """
        Returns trade data as an ordered dict. Used for dumping object attrs to string in order.
        :return:
        :rtype:
        """
        return OrderedDict([
            ('amount', '{0:f}'.format(self.amount)),
            ('currency', self.buy_trade.buy_currency),
            ('basis', '{0:f}'.format(self.buy_basis)),
            ('proceeds', '{0:f}'.format(self.sell_basis)),
            ('gain', '{0:f}'.format(self.sell_basis - self.buy_basis)),
            ('buy_time', self.buy_trade.time.isoformat()),
            ('sell_time', self.sell_trade.time.isoformat()),
            ('tax_year', self.sell_trade.time.year),
            ('time_held', str(self.sell_trade.time - self.buy_trade.time)),
            ('is_long', (self.sell_trade.time >= (self.buy_trade.time + relativedelta(days=365)))), # relativedelta(years=1)
            ('buy_exchange', self.buy_trade.exchange),
            ('sell_exchange', self.sell_trade.exchange),
            ('comment', self.comment),
        ])

transactions = []

class BalanceEntry(object):
    def __init__(self, buy_trade, basis, amount):
        self.buy_trade = buy_trade
        self.basis = basis
        self.amount_remaining = amount

    def sell(self, amount, basis, trade):
        basis_removed = self.remove_amount(amount)
        return Transaction(amount, basis_removed, basis, self.buy_trade, trade)

    def withdraw(self, amount):
        basis_removed = self.remove_amount(amount)
        return BalanceEntry(self.buy_trade, basis_removed, amount)

    def spend(self, amount, basis, trade, comment=""):
        basis_removed = self.remove_amount(amount)
        return Transaction(amount, basis_removed, basis, self.buy_trade, trade, comment)

    def validate(self):
        if self.amount_remaining < 0:
            print(f"BalanceEntry failed validation: {self}")
            exit(1)

    def is_depleted(self):
        return self.amount_remaining == 0

    def remove_amount(self, remove_amount):
        basis_removed = remove_amount * self.basis / self.amount_remaining
        self.amount_remaining = self.amount_remaining - remove_amount
        self.basis = self.basis - basis_removed
        self.validate()
        return basis_removed



class Balance(object):

    balances = {}
    @classmethod
    def get_balance(cls, exchange, currency):
        if not (exchange, currency) in cls.balances:
            cls.balances[(exchange, currency)] = Balance(exchange, currency)
        return cls.balances[(exchange, currency)]
        # if not currency in cls.balances:
        #     cls.balances[currency] = Balance(exchange, currency)
        # return cls.balances[currency]

    def __init__(self, exchange, currency):
        self.exchange = exchange
        self.currency = currency
        self.balance_entries = []
        self.transactions = []

    def add_buy_trade(self, trade, basis):
        self.balance_entries.append(BalanceEntry(trade, basis, trade.buy_amount))

    def add_sell_trade(self, trade, basis):
        trade_amount_remaining = trade.sell_amount
        trade_basis_remaining = basis
        while trade_amount_remaining > 0 and len(self.balance_entries) > 0:
            entry = self.balance_entries[0]
            transaction_sell_amount = min(trade_amount_remaining, entry.amount_remaining)
            transaction_sell_basis = transaction_sell_amount * trade_basis_remaining / trade_amount_remaining
            transaction = entry.sell(transaction_sell_amount, transaction_sell_basis, trade)
            transactions.append(transaction)
            self.transactions.append(transaction)
            trade_amount_remaining = trade_amount_remaining - transaction_sell_amount
            trade_basis_remaining = trade_basis_remaining - transaction_sell_basis
            if entry.is_depleted():
                self.balance_entries.pop(0)

        if trade_amount_remaining > 0:
            if trade_amount_remaining < 1E-5 or trade_basis_remaining < 1E-5:
                # print(f"Skipping negligible add_sell_trade: {trade}")
                pass
            else:
                print("add_sell_trade error:")
                print(f"Found no match for the following trade: {trade}")
                print(f"trade_amount_remaining: {trade_amount_remaining}")
                print(f"trade_basis_remaining: {trade_basis_remaining}")
                print(f"Balance transactions: {self.transactions}")
                print("--------------------------------")
                # exit(1)

    def add_deposit_entry(self, balance_entry):
        self.balance_entries.append(balance_entry)

    def add_withdrawal_trade(self, trade, deposit_balance):
        trade_amount_remaining = trade.sell_amount
        while trade_amount_remaining > 0 and len(self.balance_entries) > 0:
            entry = self.balance_entries[0]
            transaction_trade_amount_remaining = min(trade_amount_remaining, entry.amount_remaining)
            balance_entry = entry.withdraw(transaction_trade_amount_remaining)
            deposit_balance.add_deposit_entry(balance_entry)
            trade_amount_remaining = trade_amount_remaining - transaction_trade_amount_remaining
            if entry.is_depleted():
                self.balance_entries.pop(0)

        if trade_amount_remaining > 0:
            if trade_amount_remaining < 1E-5 or trade_basis_remaining < 1E-5:
                # print(f"Skipping negligible add_withdrawal_trade: {trade}")
                pass
            else:
                print("add_withdrawal_trade error:")
                print(f"Found no match for the following trade: {trade}")
                print(f"trade_amount_remaining: {trade_amount_remaining}")
                print(f"Balance transactions: {self.transactions}")
                print("--------------------------------")
                # exit(1)

    def add_spend_trade(self, trade, basis, comment=""):
        trade_amount_remaining = trade.sell_amount
        trade_basis_remaining = basis
        while trade_amount_remaining > 0 and len(self.balance_entries) > 0:
            entry = self.balance_entries[0]
            transaction_amount = min(trade_amount_remaining, entry.amount_remaining)
            transaction_basis = transaction_amount * trade_basis_remaining / trade_amount_remaining
            transaction = entry.spend(transaction_amount, transaction_basis, trade, comment)
            transactions.append(transaction)
            self.transactions.append(transaction)
            trade_amount_remaining = trade_amount_remaining - transaction_amount
            trade_basis_remaining = trade_basis_remaining - transaction_basis
            if entry.is_depleted():
                self.balance_entries.pop(0)

        if trade_amount_remaining > 0:
            if trade_amount_remaining < 1E-5 or trade_basis_remaining < 1E-5:
                # print(f"Skipping negligible add_spend_trade: {trade}")
                pass
            else:
                print("add_spend_trade error:")
                print(f"Found no match for the following trade: {trade}")
                print(f"trade_amount_remaining: {trade_amount_remaining}")
                print(f"Balance transactions: {self.transactions}")
                print("--------------------------------")
                # exit(1)

    def add_income_trade(self, trade, basis):
        self.balance_entries.append(BalanceEntry(trade, basis, trade.buy_amount))


def validate_transfer(withdrawal, deposit):
    if withdrawal.sell_currency != deposit.buy_currency:
        print("validate_transfer error:")
        print(withdrawal)
        print(deposit)
        print("--------------------------------")
        exit(1)

def perform_transfer(withdrawal, deposit):
    validate_transfer(withdrawal, deposit)

    currency = withdrawal.sell_currency
    if currency == "USD":
        return
    withdrawal_balance = Balance.get_balance(withdrawal.exchange, currency)
    deposit_balance = Balance.get_balance(deposit.exchange, currency)

    withdrawal_balance.add_withdrawal_trade(withdrawal, deposit_balance)


def validate_basis(trade):
    if trade.buy_currency == "USD":
        if trade.buy_amount == trade.buy_value_usd:
            return True
    elif trade.sell_currency == "USD":
        if trade.sell_amount == trade.sell_value_usd:
            return True
    else:
        return True
    print(f"validate_basis error: {trade}")
    print("--------------------------------")
    return False

def determine_basis(trade):
    # validate_basis(trade)
    if trade.buy_currency == "USD":
        return trade.buy_amount
    if trade.sell_currency == "USD":
        return trade.sell_amount

    if trade.buy_currency == "":
        if trade.sell_value_usd != 0:
            return trade.sell_value_usd
    if trade.sell_currency == "":
        if trade.buy_value_usd != 0:
            return trade.buy_value_usd

    # for currency in ("BTC", "ETH", "XMR"):
    #     if trade.buy_currency == currency:
    #         if trade.buy_value_usd == 0:
    #             print(f"determine_basis buy_value_usd warning: {trade}")
    #             print("--------------------------------")
    #         return trade.buy_value_usd
    #     elif trade.sell_currency == currency:
    #         if trade.sell_value_usd == 0:
    #             print(f"determine_basis sell_value_usd warning: {trade}")
    #             print("--------------------------------")
    #         return trade.sell_value_usd

    # if trade.sell_value_usd != 0 and trade.buy_value_usd != 0:
    #     return min(trade.sell_value_usd, trade.buy_value_usd)

    if trade.sell_value_usd != 0:
        return trade.sell_value_usd

    print(f"determine_basis error: {trade}")
    print("--------------------------------")

    # if trade.sell_value_usd != 0:
    #     return trade.sell_value_usd

    exit(1)

def perform_trade(trade):
    sell_balance = Balance.get_balance(trade.exchange, trade.sell_currency)
    buy_balance = Balance.get_balance(trade.exchange, trade.buy_currency)

    basis = determine_basis(trade)

    if sell_balance.currency != "USD":
        sell_balance.add_sell_trade(trade, basis)
    if buy_balance.currency != "USD":
        buy_balance.add_buy_trade(trade, basis)

def perform_spend(trade, comment=""):
    balance = Balance.get_balance(trade.exchange, trade.sell_currency)
    basis = determine_basis(trade)
    balance.add_spend_trade(trade, basis, comment)

def perform_income(trade):
    balance = Balance.get_balance(trade.exchange, trade.buy_currency)
    basis = determine_basis(trade)
    balance.add_income_trade(trade, basis)



withdrawal = None
deposit = None

for i in range(0, len(trade_objs)):
    trade = trade_objs[i]

    if "cancelled" in trade.comment.lower() or "failed" in trade.comment.lower() \
        or "cancelled" in trade.group.lower() or "failed" in trade.group.lower():
        continue

    if trade.type == 'Withdrawal' or trade.type == 'Deposit':
        if trade.type == 'Withdrawal':
            withdrawal = trade
        else:
            deposit = trade

        if withdrawal != None and deposit != None:
            perform_transfer(withdrawal, deposit)
            withdrawal = None
            deposit = None
    else:
        if withdrawal != None or deposit != None:
            print("mismatched withdrawal/deposit")
            print(f"withdrawal: {withdrawal}")
            print(f"desposit: {deposit}")
            print(f"next trade: {trade}")
            print("--------------------------------")

        if trade.type == "Trade":
            if trade.buy_amount != 0 and trade.sell_amount != 0 and (trade.buy_value_usd != 0 or trade.sell_value_usd != 0):
                perform_trade(trade)
            else:
                # print(f"skipping negligible  trade: {trade}")
                # print("--------------------------------")
                pass
        elif trade.type == "Spend":
            perform_spend(trade)
        elif trade.type == "Donation":
            perform_spend(trade, "Donation")
        elif trade.type == "Gift":
            perform_spend(trade, "Gift")
        elif trade.type == "Stolen":
            perform_spend(trade, "Stolen")
        elif trade.type == "Income":
            perform_income(trade)
        else:
            print(f"unaccounted for trade: {trade}")
            print("--------------------------------")

transactions = [x.to_odict() for x in transactions]

with open(sys.argv[2], 'w') as output_file:
    json.dump(transactions, output_file, indent=4)

with open(sys.argv[2], 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=Transaction.fieldnames)
    writer.writeheader()
    for transaction in transactions:
        writer.writerow(transaction)

print(f"Success. Exported {len(transactions)} items.")
