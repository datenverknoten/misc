from flask import Flask,render_template, url_for, request
from sklearn.cluster import KMeans
import pickle
import json
import pandas as pd

# Dieses Serverskript ist Teil eines Artikels auf datenverknoten.de
# https://datenverknoten.de/?p=656

# Bei Serverstart wird das Modell und die Tabelle mit den Clustern + Brennereien geladen
with open("../kmeansmodel.pkl", "rb") as f:
    kmeansmodel = pickle.load(f)
destills = pd.read_csv('../extended_whisky_dataset.csv',index_col = 0)
app = Flask(__name__)

@app.route('/')
def index():
    """
    In dieser route wird der Besucher auf die Startseite umgeleitet.
    """
    return render_template('index.html')

@app.route('/doCluster', methods=['POST'])
def doCluster():
    """
    In dieser route werden die Daten vom AJAX request empfangen. Die Liste wird für die
    Cluster Vorhersage verwendet. Zurückgegeben wird eine Liste mit den passenden Brennereien aus 
    dem vorhergesagten Cluster. Die fett markierten sind die Ausreißer
    """
    data = json.loads(request.data)
    cluster = kmeansmodel.predict([data['values']])
    list_of_destils_str = "<p class = 'lead' style='text-align: center;'>Probieren Sie Whiskys von diesen Brennereien. Die fett markierten bieten ein ganz besonderes Geschmackserlebnis in dieser Gruppe</p>"
    list_of_destils_str += "<ul>"
    matching_distills = destills[destills['Clusters'] == cluster[0]].reset_index()
    for i in range(0,len(matching_distills)):
        if(matching_distills.at[i,'Outlier'] == 1):
            list_of_destils_str += '<li><b>'+str(matching_distills.at[i,'Distillery'])+'</b></li>'
        else:
            list_of_destils_str += '<li>'+str(matching_distills.at[i,'Distillery'])+'</li>'
    list_of_destils_str += "</ul>"
    return list_of_destils_str

if __name__ == '__main__':
    """
    Hier wird der Server gestartet
    """
    app.run(debug = True)