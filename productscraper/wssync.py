import sqlite3
import pandas as pd
from bs4 import BeautifulSoup
import requests as req
import schedule
import time
from datetime import datetime


def insertPrice(wid,sid,price,conn):
    """
    This function inserts a whisky - shop - price combination into the database.

    Parameters:
    -----------
    wid : int
        the whisky id
    sid : int
        the shop id
    price : float
        the current price
    conn : sqlite3.connection
        connection to local sqlite3 database

    Returns:
    --------
    None

    """
    cursor = conn.cursor()
    stmt = "INSERT INTO Prices (WhiskyID,ShopID,Price) VALUES (?, ?, ?)"
    cursor.execute(stmt,(wid,sid,price))
    conn.commit()
    cursor.close()

def insertError(wid,sid,desc,conn):
    """
    This function inserts an error into the database that might occure during insertion or float converting.

    Parameters:
    -----------
    wid : int
        the whisky id
    sid : int
        the shop id
    desc : text
        a brief description of what went wrong
    conn : sqlite3.connection
        connection to local sqlite3 database

    Returns:
    --------
    None
    
    """
    cursor = conn.cursor()
    stmt = "INSERT INTO Errors (WhiskyID,ShopID,Description) VALUES (?, ?, ?)"
    cursor.execute(stmt,(wid,sid,desc))
    conn.commit()
    cursor.close()


def fetchPrice(address,field,fieldtype,container):
    """
    This function fetches the price from a website. It uses Beautiful Soup package to download the site
    and to find the element to look for, defined by the parameters.

    Parameters:
    -----------
    address : str 
        the address of the productsite in a webshop
    field : str
        a string containing the class(es) from the html tag to look for
    fieldtype : str
        the attribute of the html tag. could be class, id, ...
    container : str
        the html tag. could be a div, span, p, ...

    Returns:
    --------
    price : float
        the extracted price
    OR
    None if no price could be extracted
    """
    content = None
    # fetch the site
    resp = req.get(address)
    soup = BeautifulSoup(resp.text, 'lxml')
    content = soup.find(container, {fieldtype: field.split(",")})
    # extract the price. return none if not possible
    try:
        pricetext = content.text
        price = ''.join(i for i in pricetext if i.isdigit() or i == ',' or i == '.')
    except:
        return None
    return str(price).replace(',','.')

def startSync():
    """
    This function starts a new extraction round. It uses the SQL statement to fetch information
    about what sites to visit and what element to look for. It then inserts the price with 
    the whisky - shop combination into the database. The date is set in the database automatically.
    If extraction breaks, an error will be written to the database that can be shown in the GUI.

    Parameters:
    -----------
    None

    Returns:
    --------
    None
    
    """
    print("Start sync at: "+str(datetime.now()))
    dbconn = sqlite3.connect('ws.db')
    supply = pd.read_sql_query("SELECT A.WhiskyID,A.ShopID,A.Address,C.container,C.field,C.fieldtype FROM SupplySource AS A JOIN ShopSourceFields AS B ON A.ShopID = B.ShopID JOIN SupplySourceFields AS C ON B.SourceFieldsID = C.ID",dbconn)
    for i in range(0,len(supply)):
        wid = int(supply.at[i,'WhiskyID'])
        sid = int(supply.at[i,'ShopID'])
        address = supply.at[i,'Address']
        field = supply.at[i,'Field']
        fieldtype = supply.at[i,'Fieldtype']
        container = supply.at[i,'Container']
	    # only insert when conversion to float is possible
        doInsert = True
        price = fetchPrice(address,field,fieldtype,container)
        try:
            f = float(price)
        except:
            if(price == None):
                desc = "The price to insert was none"
            else:
                desc = "The price to insert was: "+str(price)
            insertError(wid,sid,desc,dbconn)
            doInsert = False
        if(doInsert):
            try:
                insertPrice(wid,sid,price,dbconn)
            except:
                desc = "Error during insert"
                insertError(wid,sid,desc,dbconn)
    dbconn.close()
    print("Finished sync at: "+str(datetime.now()))

# schedule the extraction on 10 am and 8 pm daily.
schedule.every().day.at("10:00").do(startSync)
schedule.every().day.at("20:00").do(startSync)

# do initial extraction when running the script
print("initial sync")
startSync()

# go into scheduling loop. wait 45 seconds to check if next extraction run should be started
print("going into loop")
while True:
    schedule.run_pending()
    time.sleep(45)
