# MockExchange
Current state of QFin mock exchange

All relevant info should be in playing.py and your_algo.py
Probably many bugs so lmk if any issues. 

Its pretty much all the regular libraries atm + rich for some pretty console printing

The market maker acts as per linear market impact; it just maintains a constant width about a price which is just a function of its net position. View its code to be more illuminated -> especially if you want to see an incredibly dumb implementation with a maximum amount of cancelling



