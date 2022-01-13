import pandas as pd
import sqlite3
import socket
import dash
from dash import dcc
from dash import html
import plotly.express as px
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc

# for correct scaling in mobile devices
app = dash.Dash(meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1, shrink-to-fit=no"}])

# inital load of whiskies for dropdown
dbconn = sqlite3.connect('ws.db')
prices = pd.read_sql_query('SELECT DISTINCT Name AS WhiskyName FROM Whisky',dbconn)
dbconn.close()

# prepare the dropdown for selecting a whisky
optiondropdown = []
for w in prices.WhiskyName.unique():
    optiondropdown.append({'label':w,'value':w})

# layout
app.layout = html.Div([
    dbc.Row([
        dbc.Col([
            dcc.Graph(id='pricechart')
        ])  
    ]),
    dbc.Row([
        dbc.Col(
            dcc.Dropdown(
                id='whisky-dropdown',
                options=optiondropdown,
                value=prices.WhiskyName.unique()[0]
            )
        ),
        html.A('Go to data management',href="http://192.168.2.150:5005/",target='_blank')
    ])
])

# callback for dropdown
# As output (receiver) the figure is chosen. It receives the updated figure from the function
# below as soon as it is triggered by the input.
@app.callback(
    Output('pricechart', 'figure'),
    Input('whisky-dropdown', 'value')
)
def update_output(value):
    # create database connection, fetch all data for the selection, update the figure and close the connection
    dbcon = sqlite3.connect('ws.db')
    # Select whisky data based on selected name
    selected = pd.read_sql_query('SELECT A.Date,A.Price,B.Name AS WhiskyName,C.Name as ShopName FROM Prices AS A JOIN Whisky AS B ON A.WhiskyID = B.ID JOIN Shop AS C ON A.ShopID = C.ID WHERE WhiskyName = "'+str(value)+'";',dbcon)
    # create a figure from this data and return it
    fig = px.line(selected, x="Date", y="Price", color="ShopName", hover_name="ShopName")
    fig.update_layout(transition_duration=500)
    dbcon.close()
    return fig

# start application
if __name__ == '__main__':
    app.title = "Whisky Analytics"
    # my host is called 'raspberrypi'. according to your settings you must put here a different name
    # or leave it and only use one of the app.run_server commands
    if(socket.gethostname() == 'raspberrypi'):
        app.run_server(host='192.168.2.150',port=5010)
    else:
        app.run_server(debug=True)
