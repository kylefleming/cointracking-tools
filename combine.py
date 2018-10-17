# -*- coding: utf-8 -*-
import json
import sys
from tools import read_trades_from_file, convert_trade_objs


if len(sys.argv) != 4:
    print("Usage: {} <dst_json_or_csv_file> <json_or_csv_file_with_seconds> <output_json>".format(sys.argv[0]))
    exit(1)

trade_objs_1 = convert_trade_objs(read_trades_from_file(sys.argv[1]))
trade_objs_2 = convert_trade_objs(read_trades_from_file(sys.argv[2]))

for trade_with_seconds in trade_objs_2:
    time_with_seconds = trade_with_seconds.time
    trade_with_seconds.time = trade_with_seconds.time.replace(second=0)
    try:
        trade_without_seconds = trade_objs_1[trade_objs_1.index(trade_with_seconds)]
    except:
        print("failed:")
        print(trade_with_seconds)
        raise
    trade_without_seconds.time = time_with_seconds
    trade_without_seconds.imported_time = trade_with_seconds.imported_time

trades = [x.to_odict() for x in trade_objs_1]

with open(sys.argv[3], 'w') as output_file:
    json.dump(trades, output_file, indent=4)

print("Success. Exported {} items.".format(len(trades)))
