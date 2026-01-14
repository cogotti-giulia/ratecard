#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import csv
import sys
import optparse
import xlrd
import zipfile
import xml.dom.minidom
from time import strptime, strftime
from datetime import datetime
from decimal import Decimal
from math import ceil

DIRNAME = os.path.dirname(__file__)

sys.path.append(DIRNAME + '/../../')
sys.path.append(DIRNAME + '/../')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "swissvoiptel.settings")
import django
django.setup()

match = 0
missing = 0
old_total = 0
new_total = 0

from django.db import connections
connection = connections['ratecard']
#connection = connections['vtfe_new']
cursor = connection.cursor()


# Merge COLT and TWT pricelists
def merge_pricelists():
  sql = "SELECT * FROM colt"
  cursor.execute(sql)
  colt_src = cursor.fetchall()
  for row in colt_src:
    #Search for a perfect match on TWT
    sql = "SELECT * FROM twt WHERE dialprefix = %s"
    sql_values = [row[0],]
    cursor.execute(sql,sql_values)
    twt_match = cursor.fetchall()
    if len(twt_match) == 1:
      #Found a perfect match
      continue
    else:
      #Let's look for a more generic prefix on TWT
      sql = ("SELECT dialprefix, destination, buyrate, LENGTH(dialprefix) "
             "AS pos FROM twt WHERE %s LIKE CONCAT(dialprefix,'%%')  "
             "AND LENGTH(%s)>=LENGTH(dialprefix) ORDER by pos DESC, buyrate DESC")
      sql_values = [row[0], row[0]]
      cursor.execute(sql, sql_values)
      matches = cursor.fetchall()
      if len(matches) > 0:
        #print "- G - %s, %s - %s %s" % (row[0], row[1], matches[0][0], matches[0][1])
        #Found a more generic price
        sql = "INSERT INTO twt VALUES (%s,%s,%s)"
        sql_values =[row[0], row[1], matches[0][2]]
        cursor.execute(sql, sql_values)
      else:
        #No common destination found
        print "MISSING in TWT", row[1], row[0]

  del colt_src

  sql = "SELECT * FROM twt"
  cursor.execute(sql)
  twt_src = cursor.fetchall()
  for row in twt_src:
    sql = "SELECT * FROM colt WHERE dialprefix = %s"
    sql_values = [row[0],]
    cursor.execute(sql,sql_values)
    colt_match = cursor.fetchall()
    if len(colt_match) == 1:
      #Found a perfect match
      continue
    else:
      #Let's look for a more generic prefix on COLT
      sql = "SELECT dialprefix, destination, buyrate, LENGTH(dialprefix) AS pos FROM colt WHERE %s LIKE CONCAT(dialprefix,'%%') AND LENGTH(%s)>=LENGTH(dialprefix) ORDER by pos DESC, buyrate DESC"
      sql_values = [row[0], row[0]]
      cursor.execute(sql, sql_values)
      matches = cursor.fetchall()
      if len(matches) > 0:
        #print "- G - %s, %s - %s, %s" % (row[0], row[1], matches[0][0], matches[0][1])
        #Found a more generic price
        sql = "INSERT INTO colt VALUES (%s,%s,%s)"
        sql_values =[row[0], row[1], matches[0][2]]
        cursor.execute(sql, sql_values)
      else:
        #No common destination found
        print "MISSING in COLT", row[1], row[0]

  del twt_src

def print_colt():
  #Output updated COLT pricelist
  sql = "SELECT * FROM colt ORDER BY dialprefix, destination"
  cursor.execute(sql)
  colt_src = cursor.fetchall()
  for row in colt_src:
    sql = "SELECT buyrate FROM twt WHERE dialprefix = %s"
    sql_values = [row[0],]
    cursor.execute(sql, sql_values)
    twt_src = cursor.fetchall()
    if len(twt_src)==0 or row[2] <= twt_src[0][0]:
      print '%s,"%s",0.01,%s'%(row[0],row[1],row[2])
    else:
      print '%s,"%s",0.03,%s'%(row[0],row[1],row[2])
  del colt_src
  del twt_src

def print_twt():
  #Output updated TWT pricelist
  sql = "SELECT * FROM twt ORDER BY dialprefix, destination"
  cursor.execute(sql)
  twt_src = cursor.fetchall()
  for row in twt_src:
    sql = "SELECT buyrate FROM colt WHERE dialprefix = %s"
    sql_values = [row[0],]
    cursor.execute(sql, sql_values)
    colt_src = cursor.fetchall()
    if len(colt_src)==0 or row[2] < colt_src[0][0]:
      print '%s,"%s",0.01,%s'%(row[0],row[1],row[2])
    else:
      print '%s,"%s",0.03,%s'%(row[0],row[1],row[2])
  del colt_src
  del twt_src


def print_sell():
  print '"Prefix","Destination","Best Carrier","TWT Price","Colt Price","Profitability","Sell Price EUR","Sell Price CHF"'
  # Generating LCR and checking sell rates
  sql = "SELECT * FROM twt ORDER BY destination"
  cursor.execute(sql)
  twt_src = cursor.fetchall()
  for row in twt_src:
    sql = "SELECT * FROM colt WHERE dialprefix = %s"
    sql_values = [row[0],]
    cursor.execute(sql, sql_values)
    colt_match = cursor.fetchall()
    if len(colt_match) != 1:
      continue
    selected = "TWT"
    first = row[2]
    second = row[2]
    if row[2] > colt_match[0][2]:
      selected = "COLT"
      first = colt_match[0][2]
    else:
      second = colt_match[0][2]
    sql = "SELECT sellrate, LENGTH(dialprefix) AS pos FROM sell WHERE (%s LIKE CONCAT (dialprefix, '%%') AND LENGTH(%s)>=LENGTH(dialprefix)) OR (dialprefix LIKE CONCAT (%s, '%%') AND LENGTH(%s)<LENGTH(dialprefix)) ORDER by pos DESC, sellrate DESC"
    sql_values = [row[0], row[0], row[0], row[0]]
    status = "OK"
    cursor.execute(sql, sql_values)
    sell_match = cursor.fetchall()
    if len(sell_match) == 0:
      status = "MISSING"
      sell = ""
    else:
      sell = sell_match[0][0] * 1.5 / 1.1
      if sell < first:
        status = "ALWAYS LOSS"
      elif sell < second:
        status = "POSSIBLE LOSS"
      elif sell < first*1.5 or sell_match[0][0] < second*1.5:
        status = "WARNING"
      else: #if sell_match[0][0] >= first*1.5 and sell_match[0][0] >= second*1.5:
        status = "OK"
    try:
      print "%s,\"%s\",\"%s\",%s,%s,%s,%s,%s"%(row[0], row[1], selected, row[2], colt_match[0][2], status, round(sell,2), round(sell*1.1,2) if sell else sell)
    except Exception as e:
      print e, row[0], row[1], selected, row[2], colt_match[0][2], status, sell
      continue

"""
#Check Sell pricelist OLD

#sql = "SELECT * FROM sell WHERE destination like 'lithuania%' ORDER BY destination"
sql = "SELECT * FROM sell ORDER BY destination"
cursor.execute(sql)
sell_list = cursor.fetchall()
for row in sell_list:
  #print row
  #Look for perfect TWT match
  sql = "SELECT buyrate FROM twt WHERE dialprefix = %s"
  sql_values = [row[0],]
  cursor.execute(sql, sql_values)
  twt_match = cursor.fetchall()
  if len(twt_match) == 1:
    twt_price = twt_match[0][0]
    #print "FOUND PERFECT"
  elif len(twt_match) > 1:
    print "ERROR: multiple entries for %s in TWT"%row[0]
  else:
    #look for more generic match
    sql = "SELECT buyrate, LENGTH(dialprefix) AS pos FROM twt WHERE (%s LIKE CONCAT (dialprefix, '%%') AND LENGTH(%s)>=LENGTH(dialprefix)) ORDER by pos DESC, buyrate DESC"
    sql_values = [row[0], row[0], ]
    cursor.execute(sql, sql_values)
    twt_match = cursor.fetchall()
    if len(twt_match) > 0:
      twt_price = twt_match[0][0]
      #print "FOUND GENERIC: ", twt_match[0]
    else:
      # look for more specialized match
      sql = "SELECT buyrate, LENGTH(dialprefix) AS pos FROM twt WHERE dialprefix LIKE CONCAT (%s, '%%') AND LENGTH(%s)<=LENGTH(dialprefix) ORDER by pos DESC, buyrate DESC"
      sql_values = [row[0], row[0], ]
      cursor.execute(sql, sql_values)
      twt_match = cursor.fetchall()
      if len(twt_match) > 0:
        twt_price = twt_match[0][0]
        #print "FOUND SPECIALIZED"
      else:
        print "ERROR: %s not found in TWT" % row[0]

  # Look for perfect COLT match
  sql = "SELECT buyrate FROM colt WHERE dialprefix = %s"
  sql_values = [row[0],]
  cursor.execute(sql, sql_values)
  colt_match = cursor.fetchall()
  if len(colt_match) == 1:
    colt_price = colt_match[0][0]
    #print "FOUND PERFECT"
  elif len(colt_match) > 1:
    print "ERROR: multiple entries for %s in COLT"%row[0]
  else:
    # look for more generic match
    sql = "SELECT buyrate, LENGTH(dialprefix) AS pos FROM colt WHERE (%s LIKE CONCAT (dialprefix, '%%') AND LENGTH(%s)>=LENGTH(dialprefix)) ORDER by pos DESC, buyrate DESC"
    sql_values = [row[0], row[0], ]
    cursor.execute(sql, sql_values)
    colt_match = cursor.fetchall()
    if len(colt_match) > 0:
      colt_price = colt_match[0][0]
      #print "FOUND GENERIC: ", colt_match[0]
    else:
      # look for more specialized match
      sql = "SELECT buyrate, LENGTH(dialprefix) AS pos FROM colt WHERE dialprefix LIKE CONCAT (%s, '%%') AND LENGTH(%s)<=LENGTH(dialprefix) ORDER by pos DESC, buyrate DESC"
      sql_values = [row[0], row[0], ]
      cursor.execute(sql, sql_values)
      colt_match = cursor.fetchall()
      if len(colt_match) > 0:
        colt_price = colt_match[0][0]
        #print "FOUND SPECIALIZED"
      else:
        print "ERROR: %s not found in COLT" % row[0]

  #sql = "SELECT buyrate, LENGTH(dialprefix) AS pos FROM colt WHERE (%s LIKE CONCAT (dialprefix, '%%') AND LENGTH(%s)>=LENGTH(dialprefix)) OR (dialprefix LIKE CONCAT (%s, '%%') AND LENGTH(%s)<=LENGTH(dialprefix)) ORDER by pos DESC, buyrate DESC"
  #sql_values = [row[0], row[0], row[0], row[0]]
  #cursor.execute(sql, sql_values)
  #colt_match = cursor.fetchall()
  #if len(twt_match)>0:
  #  twt_price = twt_match[0][0]
  #else:
  #  print "ERROR: %s not found in TWT"%row[0]
  #  continue
  #if len(colt_match)>0:
  #  colt_price = colt_match[0][0]
  #else:
  #  print "ERROR: %s not found in COLT"%row[0]
  #  continue
  sql = "UPDATE sell SET buyrate1 = %s, buyrate2 = %s WHERE dialprefix = %s"
  sql_values = [twt_price, colt_price, row[0]]
  cursor.execute(sql, sql_values)
"""
"""
#Output sell pricelist analysis OLD
sql = "select destination, round(min(sellrate)*1.5,2), round(buyrate1*1.1,4), round(buyrate1*1.1*1.5,4), round(buyrate2*1.1,4), round(buyrate2*1.1*1.5,4), count(*), GROUP_CONCAT(dialprefix) from sell WHERE destination like 'lithuania%' group by destination, buyrate1  order by destination, buyrate1"
cursor.execute(sql)
sell_list = cursor.fetchall()
for row in sell_list:
  status = 'OK'
  if row[1] < min([row[2],row[4]]):
    status = 'ALWAYS LOSS'
  elif row[1] < max([row[2],row[4]]):
    status = 'POSSIBLE LOSS'
  elif row[1] < row[3] or row[1] < row[5]:
    status = 'WARNING'
  print '"%s";%s;%s;%s;%s;%s;%s;%s;%s'%(row[0],row[1],row[2],row[3],row[4],row[5],row[6],status,row[7])
"""
def check_new_sell():
  # New sell analysis
  sql = "DELETE FROM sellnew"
  cursor.execute(sql)
  sql = "SELECT dialprefix, buyrate, destination FROM twt order by destination"
  cursor.execute(sql)
  twt_list = cursor.fetchall()
  for twt_price in twt_list:
    #Get matching COLT row
    sql = "SELECT buyrate FROM colt WHERE dialprefix = %s"
    sql_values = [twt_price[0],]
    cursor.execute(sql, sql_values)
    colt_list = cursor.fetchall()
    if len(colt_list) != 1:
      print "COLT ERROR: %s"%twt_price[0], colt_list
      continue
    colt_price = colt_list[0]
    #Find matching Sell pricelist
    sql = "SELECT dialprefix, destination, sellrate, LENGTH(dialprefix) as pos FROM sell WHERE %s LIKE CONCAT (dialprefix, '%%') ORDER BY pos DESC"
    sql_values = [twt_price[0],]
    cursor.execute(sql,sql_values)
    sell_list = cursor.fetchall()
    if len(sell_list) == 0:
      print "ERROR: sell rate not found %s"%twt_price[0], twt_price[2]
      continue
    else:
      sell_rate = sell_list[0]
    #Check if rate has already been put on the output table
    sql = "SELECT COUNT(*) FROM sellnew WHERE dialprefix = %s AND sellrate = %s AND buyrate1 = %s and buyrate2 = %s"
    #sql_values = (sell_rate[0], sell_rate[2], twt_price[1], colt_price[0])
    sql_values = (twt_price[0], sell_rate[2], twt_price[1], colt_price[0])
    #print sql%sql_values
    cursor.execute(sql, sql_values)
    if cursor.fetchall()[0][0] == 0:
      sql = "INSERT INTO sellnew (dialprefix, destination, sellrate, buyprefix, buyrate1, buyrate2) VALUES (%s,%s,%s,%s,%s,%s)"
      #sql_values = [sell_rate[0], sell_rate[1], sell_rate[2], twt_price[0], twt_price[1], colt_price[0]]
      sql_values = [twt_price[0], sell_rate[1], sell_rate[2], twt_price[0], twt_price[1], colt_price[0]]
      try:
        cursor.execute(sql, sql_values)
      except Exception as e:
        print twt_price[0], sell_rate[1], sell_rate[2], twt_price[2], twt_price[1], colt_price[0]
        from pprint import pprint
        pprint(twt_price)
        raise e
    else:
      sql = "UPDATE sellnew SET buyprefix = CONCAT(buyprefix, ',', %s) WHERE dialprefix = %s AND sellrate = %s AND buyrate1 = %s and buyrate2 = %s"
      sql_values=[twt_price[0], sell_rate[0], sell_rate[2], twt_price[1], colt_price[0]]
      try:
        cursor.execute(sql, sql_values)
      except Exception as e:
        from pprint import pprint
        pprint(sql_values)
        raise e

def print_new_sell():
  #Output sell pricelist analysis
  print('"Destination";"Sell rate";"Buy 1";"Buy 2";"Buy 3";"Buy 4";"Destination count";"Profit";"Sell prefix list";"Buy prefix list"')
  sql = "SELECT destination, ROUND(sellrate*1.5,2), ROUND(buyrate1*1.1,4), ROUND(buyrate1*1.1*1.5,4), ROUND(buyrate2*1.1,4), ROUND(buyrate2*1.1*1.5,4), COUNT(*), GROUP_CONCAT(dialprefix), GROUP_CONCAT(DISTINCT(buyprefix)) from sellnew group by destination, sellrate, buyrate1, buyrate2  order by destination, sellrate, buyrate1, buyrate2"
  cursor.execute(sql)
  sell_list = cursor.fetchall()
  for row in sell_list:
    status = 'OK'
    if row[1] < min([row[2],row[4]]):
      status = 'ALWAYS LOSS'
    elif row[1] < max([row[2],row[4]]):
      status = 'POSSIBLE LOSS'
    elif row[1] < row[3] or row[1] < row[5]:
      status = 'WARNING'
    print '"%s";%s;%s;%s;%s;%s;%s;%s;%s;%s'%(row[0],row[1],row[2],row[3],row[4],row[5],row[6],status,row[7],row[8])


"""
#BOOOOOOh!!!!! non completato
filename ="VT-analisi_listino_vendita-3.csv"
csv = open(filename)
for row in csv.readlines()[1:]:
  data = row.split(';')
  sql = "UPDATE sellnew SET "
  sql_data = []
  if row[2] != "":
    sql += "newdestination = %s, "
    sql_data.append(row[2])
  if row[3] != "":
    sql += "newsellrate = %s, "
    sql_data.append(Decimal(row[3].replace(',','.')))
  sql += "verified = True WHERE dialprefix = %s"
  
  for prefix in row[10].split(','):
"""
merge_pricelists()
#print_colt()
#print_twt()
#print_sell()
#check_new_sell()
#print_new_sell()

