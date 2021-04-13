import config
import whois
import pandas as pd

from flask import Flask, render_template, request
from gensim.models import Word2Vec
app = Flask(__name__)

# Initial das Modell laden. Passiert, während der Server gestartet wird. 
# Vor dem ersten Start muss das ZIP Archiv entpackt werden. 
model = Word2Vec.load('model/web_wrt.model')

# Die Route zur Startseite
@app.route('/')
def start():
    # Es soll das Template mit den Eingabefeldern gerendert werden
    return render_template('start.html')

# Die Route zu den Vorschlägen
@app.route('/suggestion', methods=['POST'])
def suggestion():
    # Zunächst werden die Parameter aus dem Formular abgerufen
    topicWord = request.form.get('topicWord')
    requiredlWord = request.form.get('requiredlWord')

    # Hier werden nun Wörter aus dem Word2Vec Modell bestimmt, die einen ähnlichen
    # Kontext wie das eingegebene Thema besitzen. Ist das Wort selber nicht im Modell vorhanden,
    # wird auf eine Fehlerseite umgeleitet.
    try:
        results = model.wv.most_similar("".join(topicWord.lower().split()))
    except KeyError as k:
        return render_template('error.html')

    # Es entsteht dabei eine Liste von Tupeln, in denen das erste Element das 
    # gefundene Wort und das zweite Element die 'Ähnlichkeit' ist. Diese Ähnlichkeit
    # drückt sich in der geringsten Cosinus Distanz zwischen den Wörtern aus, 
    # die sich aus den Vektoren ergibt.
    suggested_words = [x[0] for x in results]

    domains = []
    # Als nächstes werden Domainvorschläge erstellt.
    for word in suggested_words:
        domains.append("www."+str(word)+"-"+str(requiredlWord.lower())+".de")
        domains.append("www."+str(requiredlWord.lower())+"-"+str(word)+".de")

        domains.append("www."+str(word)+"-"+str(requiredlWord.lower())+".com")
        domains.append("www."+str(requiredlWord.lower())+"-"+str(word)+".com")

    # Hier wird der Verfügbarkeitsstatus aller Domains überprüft. Besitzen Sie
    # keinen mit WHOIS auffindbaren Eintrag, sind sie frei.
    status_list = []
    for dom in domains:
        # Im Falle einer freien Domain wird ein PywhoisError ausgelöst.
        try:
            domain = whois.whois(dom)
            status_list.append('<span style = "color : red">Vergeben</span>')
        except whois.parser.PywhoisError as pe:
            status_list.append('<span style = "color : green">Frei</span>')

    # Aus den Domains und ihrem jeweiligen Status wird ein Pandas Dataframe erzeugt.
    result_table = pd.DataFrame()
    result_table['Domain'] = domains
    result_table['Status'] = status_list

    # Dieser Dataframe wird in eine HTML Tabelle übersetzt. Die id wird benötigt,
    # da auf der Zielseite JQuery Datatables verwendet werden.
    return render_template( \
        'suggestion.html', \
        result_table = result_table.to_html( 
            escape = False, \
            table_id = 'result_table', \
            index = False
        )
    )

# Der Server wird beim Ausführen des Skripts gestartet. 
# Es ist nur eine Basiskonfiguration vorhanden. Flask ist ein 
# Dev-Server. Für den Produktiveinsatz sollte z.B. Werkzeug verwendet werden.
if __name__ == '__main__':
    # Laden der Adresse und des Ports aus der Konfiguration
    app.run(host = config.IP, port = config.PORT)