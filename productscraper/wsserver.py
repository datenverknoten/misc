import dis
from flask import Flask, render_template, request, url_for,redirect
import sqlite3
import pandas as pd
import socket
from bs4 import BeautifulSoup
import requests as req

app = Flask(__name__)

def fetchPrice(address,field,fieldtype,container):
    """
    This function fetches the price from a website. It uses Beautiful Soup package to download the site
    and to find the element to look for, defined by the parameters. It is used the same way as in wssync.py

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
    return price

def databaseFetcher(query,params=[]):
    """
    This function fetches the result of a query. It creates and closes the database connection.

    Parameters:
    -----------
    query : str
        an sql query as a string
    parameters : list
        the query might contain parameters. to apply these to form a prepared statement they are handed
        in separately

    Returns:
    --------
    res : pd.DataFrame
        a pandas dataframe containing the result of the query
    """
    dbconn = sqlite3.connect('ws.db')
    res = pd.read_sql_query(query,dbconn,params=params)
    dbconn.close()
    return res

def databaseInserter(query,params):
    """
    This function inserts the given statement into the database. The parameters are sent
    separetely to form a prepared statement. A database connection is opend and closed.

    Parameters:
    -----------
    query : str
        the sql statement as string
    params : list
        the parameter list to be inserted in the statement

    Returns:
    --------
    None

    """
    dbconn = sqlite3.connect('ws.db') 
    cursor = dbconn.cursor()
    cursor.execute(query,params)
    dbconn.commit()
    cursor.close()
    dbconn.close()

### Following are the routes. Each route usually has some kind of action, a form for example, 
### that inserts or fetches something from the database. 

# Default route 
@app.route('/')
def showIndex():
    return showWhiskies()

# Route for showing the page with scrape checker
@app.route('/scrapecheck')
def showScrapeChecker():
    return render_template('scrapecheck.html')

# the action triggered by the form on scrapecheck.html
@app.route('/checkscrape', methods=['POST'])
def handle_data_scraper():
    # fetch form data
    address = request.form['address']
    field = request.form['fields']
    fieldtype = request.form['fieldtype']
    container = request.form['container']
    # call fetchPrice function
    try:
        price = fetchPrice(address,field,fieldtype,container)
    except:
        price = 'No pricetag found'
    if(price == None):
        price = 'No pricetag found'
    # display results of the price fetching on a new page
    return render_template('scraperesult.html', price = price, address = address, field = field, fieldtype = fieldtype, container = container)

# Route for showing the prices in the database
@app.route('/prices')
def showPrices():
    # fetch the prices
    pricetable = databaseFetcher('SELECT B.Name AS Whisky,C.Name AS Shop,A.Date,A.Price AS Price FROM Prices AS A JOIN Whisky AS B ON A.WhiskyID = B.ID JOIN Shop AS C ON A.ShopID = C.ID')
    return render_template('prices.html',dt = pricetable.to_html(table_id='dt',index=False,classes='stripe',border=0))

# Errors
@app.route('/errors')
def showErrors():
    errortable = databaseFetcher('SELECT B.Name AS Whisky,C.Name as Shop,A.Date from Errors AS A JOIN Whisky AS B ON A.WhiskyID=B.ID JOIN Shop AS C ON A.ShopID=C.ID;').sort_values(by='Date')
    return render_template('errors.html',dt = errortable.to_html(table_id='dt',index=False,classes='stripe',border=0))

# Distilleries
@app.route('/distilleries')
def showDistilleries():
    distilleriestable = databaseFetcher('SELECT Name FROM Distillery').sort_values(by='Name')
    return render_template('distilleries.html',dt = distilleriestable.to_html(table_id='dt',index=False,classes='stripe',border=0))

# The action for inserting a new distillery to the database
@app.route('/insertdistillery', methods=['POST'])
def handle_data_distillery():
    distname = request.form['distinput']
    databaseInserter("INSERT INTO Distillery (Name) Values (?)",[distname])
    return redirect(url_for('showDistilleries'))


# Whiskies
@app.route('/whiskies')
def showWhiskies():
    whiskiestable = databaseFetcher('SELECT A.Name As Whisky,A.Age AS Age, B.Name AS Distillery FROM Whisky AS A JOIN Distillery AS B ON A.DistilleryID = B.ID')
    distilleriestable = databaseFetcher('SELECT ID,Name FROM Distillery').sort_values(by='Name')
    return render_template('whiskies.html',wt = whiskiestable.to_html(table_id='wt',index=False,classes='stripe',border=0),dt = distilleriestable)

# Action for inserting a new whisky.
@app.route('/insertwhisky', methods=['POST'])
def handle_data_whisky():
    whisname = request.form['whisname']
    whisage = request.form['whisage']
    distillery = request.form.get('distselect')
    databaseInserter("INSERT INTO Whisky (Name,Age,DistilleryID) Values (?,?,?)",[whisname,whisage,distillery])
    return redirect(url_for('showWhiskies'))


# Shops
@app.route('/shops')
def showShops():
    shopstable = databaseFetcher('SELECT * FROM Shop').sort_values(by='Name')
    return render_template('shops.html',st = shopstable.to_html(table_id='st',index=False,classes='stripe',border=0))

# Action for inserting a new shop.
@app.route('/insertshop', methods=['POST'])
def handle_data_shop():
    shopname = request.form['shopname']
    baselink = request.form['baselink']
    databaseInserter("INSERT INTO Shop (Name,BaseLink) Values (?,?)",[shopname,baselink])
    return redirect(url_for('showShops'))


# Supply source fields route
@app.route('/supplysourcefields')
def showSupplySourceFields():
    ssftable = databaseFetcher('SELECT Container,Fieldtype,Field FROM SupplySourceFields')
    return render_template('supplysourcefields.html',st = ssftable.to_html(table_id='st',index=False,classes='stripe',border=0))

# Action for inserting new source fields
@app.route('/insertsupplysourcefields', methods=['POST'])
def handle_data_ssf():
    container = str(request.form['container']).lower()
    fieldtype = str(request.form['fieldtype']).lower()
    field = str(request.form['field']).lower()

    result = databaseFetcher('SELECT * FROM SupplySourceFields WHERE Container=? AND Fieldtype=? AND Field=?',[container,fieldtype,field])

    if(len(result) > 0):
        return render_template('combalreadyexists.html')
    else:
        databaseInserter("INSERT INTO SupplySourceFields (Container,Fieldtype,Field) Values (?,?,?)",[container,fieldtype,field])
        return redirect(url_for('showSupplySourceFields'))

# Shop source fields
@app.route('/shopsourcefields')
def showShopSourceFields():
    ssftable = databaseFetcher('SELECT A.Name,C.Container,C.Fieldtype,C.Field FROM Shop AS A LEFT JOIN ShopSourceFields AS B ON A.ID = B.ShopID LEFT JOIN SupplySourceFields AS C ON B.SourceFieldsID = C.ID')
    shopt =databaseFetcher('SELECT * FROM Shop').sort_values(by='Name')
    sst = databaseFetcher('SELECT ID,Container,Fieldtype,Field FROM SupplySourceFields')
    sst['Combination'] = sst['Container'] + " :: " + sst['Fieldtype'] + " :: " + sst['Field']
    sst = sst[['ID','Combination']]
    return render_template('shopsourcefields.html', \
        st = ssftable.to_html(table_id='st',index=False,classes='stripe',border=0), \
        shopt = shopt, \
        sst = sst \
        )

# Insert new shop source fields
@app.route('/insertshopsourcefields', methods=['POST'])
def handle_data_shopsf():
    shopid = request.form.get('shopselect')
    combid = request.form.get('combinationselect')
    databaseInserter("INSERT OR REPLACE INTO ShopSourceFields (ShopID,SourceFieldsID) Values (?,?)",[shopid,combid])
    return redirect(url_for('showShopSourceFields'))


# Supply source
@app.route('/supplysource')
def showSupplySource():
    ssftable = databaseFetcher("""
        SELECT C.Name AS Whiskyname,D.Name AS Distillery, B.Name AS ShopnameG,A.Address FROM SupplySource AS A
        LEFT JOIN Shop AS B on B.ID = A.ShopID
        LEFT JOIN Whisky AS C ON C.ID = A.WhiskyID
        LEFT JOIN Distillery AS D ON C.DistilleryID = D.ID
    """)
    whist = databaseFetcher('SELECT ID,Name FROM Whisky').sort_values(by='Name')
    shopt = databaseFetcher('SELECT ID,Name FROM Shop').sort_values(by='Name')

    return render_template('shopsource.html', \
        st = ssftable.to_html(table_id='st',index=False,classes='stripe',border=0), \
        whist = whist, \
        shopt = shopt \
        )

# Action to insert new supply source
@app.route('/insertsupplysource', methods=['POST'])
def handle_data_supplysource():
    shopid = request.form.get('shopselect')
    whisid = request.form.get('whisselect')
    whislink = request.form['whislink']
    print(shopid,whisid,whislink)
    databaseInserter("INSERT INTO SupplySource (ShopID,WhiskyID,Address) Values (?,?,?)",[shopid,whisid,whislink])
    return redirect(url_for('showSupplySource'))

# the same here as in wsanalytics.py. According to your hostname, you must adjust this section 
# or only use one of the app.run commands without the ifs.
if __name__ == '__main__':
    if(socket.gethostname() == 'raspberrypi'):
        app.run(host='192.168.2.150',port=5005)
    else:
        app.run(debug=True,port=5005)
