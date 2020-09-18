import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
from database2 import sqlAddRow, sqlSelectRows, sqlUpdateRows, sqlDelRow, sqlSumRows
import time




scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name('C:/inetpub/vhosts/default/htdocs/api/App_Data/Enumis sheets project-7568c914a4bc.json', scope)
gc = gspread.authorize(credentials)
wks = gc.open('Coinstand Trade Report').sheet1
wsDays = gc.open('Coinstand Trade Report').get_worksheet(1)

columnOrder = ["StartDate", "Volume", "Trades", "AverageMargin", "EstimatedProfit", "dtVolume", "dtTrades", "dtAverageMargin", "dtEstimatedProfit",
                 "totalVolume", "totalTrades", "totalEstimatedProfit", "7DAverage", "30DAverage", "WeekdayNum", "WeeklyTotal", "WeekStarting", "4WAverage", "Month"]



# work out daily vols
def main():
    # find last row to find last updated date
    lastRow = wsDays.row_count
    row = lastRow + 1
    lastDate = wsDays.acell('A' + str(lastRow)).value
    if lastDate:
        if lastDate[:3] == '202':
            lastDate = datetime.datetime.strptime(lastDate, "%Y-%m-%d")
        else:
            lastDate = datetime.datetime.strptime(lastDate, "%d/%m/%Y")

        # if >= 1 day since last update 
        if lastDate.date() < datetime.datetime.now().date() - datetime.timedelta(days=1):

            # find days between and add new rows 
            startDate = lastDate + datetime.timedelta(days=1)
            daysBetween = (datetime.datetime.now() - startDate).days
            wsDays.add_rows(daysBetween)

            # add new rows 
            for i in range(daysBetween):

                # create the sql queries for getting the correct trades for each day 
                date = startDate + datetime.timedelta(days=i)
                lbcQuery = "transaction_released_at != 'None' AND transaction_released_at LIKE '%" + str(date.date()) + "%'"
                dtQuery = "Date != 'None' AND Date LIKE '%" + str(date.date()) + "%'"
                stats = calculateStats(lbcQuery, dtQuery, date.date(), row)

                # add day stats to database
                lstCells = wsDays.range('A' + str(row) + ':S' + str(row))
                if len(lstCells) == len(columnOrder):
                    for i in range(len(lstCells)):
                        lstCells[i].value = stats[columnOrder[i]]
                    wsDays.update_cells(lstCells,  value_input_option='USER_ENTERED')

                # move the list of cells to change down a row
                row += 1

                time.sleep(1)


def transactionStats2():
    trades = sqlSelectRows("tblClosedTrades", "transaction_released_at != 'None'")
    print len(trades)
    dic = {}
    dic['oneTrade'] = {'count':0, 'above10000':0, 'below10000':0}
    dic['multTrades'] = {'count':0, 'above10000':0, 'below10000':0}
    
    for trade in trades:
        totalTrades = len(sqlSelectRows("tblClosedTrades", "customer_is = '" + trade['customer_is'] + "' AND transaction_released_at != 'None'"))
        if totalTrades == 1:
            dic['oneTrade']['count'] += 1
            if trade['fiat_amount'] >= 10000:
                dic['oneTrade']['above10000'] += 1
            else:
                dic['oneTrade']['below10000'] += 1
        elif totalTrades > 1:
            pass
            # dic['multTrades']['count'] += 1
            # if trade['fiat_amount'] >= 10000:
            #     dic['multTrades']['above10000'] += 1
            # else:
            #     dic['multTrades']['below10000'] += 1

    print dic['oneTrade']

# def transactionStats3():
#     print len(sqlSelectRows("tblClosedTrades", "transaction_released_at != 'None' AND fiat_amount >= 15000"))
#     print len(sqlSelectRows("tblClosedTrades", "transaction_released_at != 'None' AND fiat_amount < 15000"))
#     print len(sqlSelectRows("tblClosedTrades", "transaction_released_at != 'None'"))
#     print len(sqlSelectRows("DirectTrades", "AmountGBP >= 15000"))
#     print len(sqlSelectRows("DirectTrades", "AmountGBP < 15000"))

def transactionStats():
    trades = sqlSelectRows("tblClosedTrades", "transaction_released_at != 'None'")
    print len(trades)
    dic = {}
    dic['oneTrade'] = {'count':0, 'above10000':0, 'below10000':0}
    dic['multTrades'] = {'count':0, 'above10000':0, 'below10000':0}
    
    for trade in trades:
        totalTrades = len(sqlSelectRows("tblClosedTrades", "customer_is = '" + trade['customer_is'] + "' AND transaction_released_at != 'None'"))
        if totalTrades == 1:
            dic['oneTrade']['count'] += 1
            if trade['fiat_amount'] >= 10000:
                dic['oneTrade']['above10000'] += 1
            else:
                dic['oneTrade']['below10000'] += 1
        elif totalTrades > 1:
            pass
            # dic['multTrades']['count'] += 1
            # if trade['fiat_amount'] >= 10000:
            #     dic['multTrades']['above10000'] += 1
            # else:
            #     dic['multTrades']['below10000'] += 1








# add all the values for each row of db
def calculateStats(lbcQuery, dtQuery, startDate, row):
    emptyDict = {}
    emptyDict['StartDate'] = str(startDate)

    # lbc trade stats
    trades = sqlSelectRows("tblClosedTrades", lbcQuery)
    emptyDict['Volume'] = sqlSumRows("tblClosedTrades", "fiat_amount", lbcQuery)
    if emptyDict['Volume'][0]:
        emptyDict['Volume'] = emptyDict['Volume'][0]
        emptyDict['AverageMargin'] = aveMargin(trades, lbcQuery, "tblClosedTrades") 
    else:
        emptyDict['Volume'] = 0
        emptyDict['AverageMargin'] = 0
    emptyDict['EstimatedProfit'] = emptyDict['Volume'] * emptyDict['AverageMargin']
    emptyDict['Trades'] = len(trades)

    # now for direct trades
    trades = sqlSelectRows("DirectTrades", dtQuery)
    emptyDict['dtVolume'] = sqlSumRows("DirectTrades", "AmountGBP", dtQuery)
    if emptyDict['dtVolume'][0]:
        emptyDict['dtVolume'] = emptyDict['dtVolume'][0]
        emptyDict['dtAverageMargin'] = aveMargin(trades, dtQuery, "DirectTrades")
    else:
        emptyDict['dtVolume'] = 0
        emptyDict['dtAverageMargin'] = 0

    emptyDict['dtTrades'] = len(trades)
    emptyDict['dtEstimatedProfit'] = emptyDict['dtVolume'] * emptyDict['dtAverageMargin']

    # add in spreadsheet formulas for totals
    emptyDict['totalVolume'] = '=sum(B' + str(row) + ', F' + str(row) + ')'
    emptyDict['totalTrades'] = '=sum(C' + str(row) + ', G' + str(row) + ')'
    emptyDict['totalEstimatedProfit'] = '=sum(E' + str(row) + ', I' + str(row) + ')'
    emptyDict['7DAverage'] = '=sum(J' + str(row-6) + ':J' + str(row) + ')/7'
    emptyDict["30DAverage"] = '=sum(J' + str(row-29) + ':J' + str(row) + ')/30'
    emptyDict["WeekdayNum"] = '=weekday(A' + str(row) +', 2)'
    emptyDict["WeeklyTotal"] = '=if(O' + str(row) + '=7, sum(J' + str(row-6) + ':J' + str(row) + '), "")'
    emptyDict["WeekStarting"] = '=if(O' + str(row) + '=7, A' + str(row-6) + ', "")'
    emptyDict["4WAverage"] = '=if(O' + str(row) + '=7, sum(P' + str(row-21) + ':P' + str(row) + ')/4, "")'
    emptyDict["Month"] = '=if(A' + str(row) + ' - (DAY(A' + str(row) + ')-1) = A' + str(row) + ', A' + str(row) + ', "")'
    return emptyDict
    


# work out average margin, weighted by fiat amount 
def aveMargin(lstTrades, sqlQuery, type):
    if type == "tblClosedTrades":
        for trade in lstTrades:
            if trade['marginAbove'] == 0:
                # find btc prices
                query = "created_at LIKE '%" + str(trade['transaction_released_at'].split(' ')[0]) + "%' AND created_at > '" + str(trade['transaction_released_at']) + "'"
                btc_prices = sqlSelectRows("tblBtcPrice", query)
                if len(btc_prices) == 0:
                    # no btc price data available
                    margin = "None"
                else:
                    # find closest btc price snapshot from database (and add 0.1%), then work out margin of trade
                    btc_price = btc_prices[0]['gbp_price'] * 1.001
                    margin = float(trade['fiat_per_btc']) / float(btc_price)
                # update trade in db with margin above btc price
                sqlUpdateRows("tblClosedTrades", "transaction_id = " + str(trade['transaction_id']), {'marginAbove':margin})

        # find fiat_amount weighted margin above btc price, to find average above for all trades in list
        sumMarginAbove = 0
        lstTrades = sqlSelectRows("tblClosedTrades", sqlQuery)
        for trade in lstTrades:
            if trade['marginAbove'] != 0 and trade['marginAbove'] != 'None':
                sumMarginAbove += float(trade['fiat_amount']) * float(trade['marginAbove'])
        sumFiatAmount = sqlSumRows("tblClosedTrades", "fiat_amount", sqlQuery + " AND marginAbove != 0 AND marginAbove != 'None'")
        

    elif type == "DirectTrades":
        for trade in lstTrades:
            if trade['marginAbove'] == 0:
                # find btc prices
                query = "created_at LIKE '%" + str(trade['Date'].split(' ')[0]) + "%' AND created_at < '" + str(trade['AddedAt']) + "'"
                btc_prices = sqlSelectRows("tblBtcPrice", query)
                if len(btc_prices) == 0:
                    # no btc price data available
                    margin = "None"
                else:

                    # find closest btc price snapshot from database (and add 0.3%), then work out margin of trade
                    btc_price = btc_prices[-1]['gbp_price'] * 1.003
                    margin = float(trade['PriceBTC']) / float(btc_price)
                sqlUpdateRows("DirectTrades", "TXID = '" + str(trade['TXID'] + "'"), {'marginAbove':margin})

        # find fiat_amount weighted margin above btc price, to find average above for all trades in list
        sumMarginAbove = 0
        lstTrades = sqlSelectRows("DirectTrades", sqlQuery)
        for trade in lstTrades:
            if trade['marginAbove'] != 0 and trade['marginAbove'] != 'None':
                sumMarginAbove += float(trade['AmountGBP']) * float(trade['marginAbove'])
        sumFiatAmount = sqlSumRows("DirectTrades", "AmountGBP", sqlQuery + " AND marginAbove != 0 AND marginAbove != 'None'")

    if not sumFiatAmount[0] or sumMarginAbove == 0:
        aveMargin = 0
    else:
        if type == 'tblClosedTrades':
            aveMargin = sumMarginAbove / sumFiatAmount[0]
            aveMargin = aveMargin * 0.99 - 1
        elif type == "DirectTrades":
            aveMargin = sumMarginAbove / sumFiatAmount[0]
            aveMargin = aveMargin - 1
    return aveMargin

def findAveRev():
    users = sqlSelectRows("tblClosedTrades", "transaction_released_at != 'None'", "DISTINCT customer_is")
    for user in users:
        firstTrade = sqlSelectRows("tblClosedTrades", "customer_is = '" + user['id'] + "' AND transaction_released_at != 'None'")[0]
        totalTrades = sqlSumRows("tblClosedTrades", "fiat_amount", "customer_is = '" + user['id'] + "' AND transaction_released_at != 'None'")
        totalRev = totalTrades[0] / firstTrade['fiat_amount']
        sqlUpdateRows("tblLBCCustomers", "username = '" + user['id'] + "'", {'totalRev':totalRev})

def totalRev():
    num = 0
    den = 0
    users = sqlSelectRows("tblLBCCustomers", "")
    for user in users:
        trades = sqlSelectRows("tblClosedTrades", "customer_is = '" + user['username'] + "' AND transaction_released_at != 'None'")
        if len(trades) > 0:
            num += user['totalRev'] * trades[0]['fiat_amount']
            den += trades[0]['fiat_amount']
    print num / den





if __name__ == '__main__':
    #totalRev()
    main()
