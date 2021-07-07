from flask import Flask,request
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.model_selection import cross_val_score
from sklearn.model_selection import train_test_split
from sklearn import svm

# Normalverteilung der Größe mit Mittelwert 179,9 cm und Standardabweichung von 10 (cm)
training_data_height = np.random.normal(loc=179.9,size=250,scale=10)
# Normalverteilung des Brustumfangs mit Mittelwert 106 cm und Standardabweichung von 5 (cm)
training_data_chest = np.random.normal(loc=106,size=250,scale=5)

# Beide Normalverteilungen in einen Pandas Dataframe speichern
modeldata = pd.DataFrame({'Height':training_data_height,'ChestCircumference':training_data_chest})

def prepareData(data):
    # Daten filtern, die größer oder kleiner als die zweifache Standardabweichung pro Feature sind
    print("Starting with: "+str(len(data)))
    data = (
        data[
            # Filterung auf ungewöhnliche Werte
            (data['Height'] <= 250) &\
            (data['Height'] >= 130) &\
            (data['ChestCircumference'] >= 70) &\
            (data['ChestCircumference'] <= 160)
        ]
    )

    data = (
        data[
            # Filterung auf statistisch ungewöhnliche Werte
            (data['Height'] <= data['Height'].mean() + data['Height'].std() * 3) &\
            (data['Height'] >= data['Height'].mean() - data['Height'].std() * 3) &\
            (data['ChestCircumference'] <= data['ChestCircumference'].mean() + data['ChestCircumference'].std() * 3) &\
            (data['ChestCircumference'] >= data['ChestCircumference'].mean() - data['ChestCircumference'].std() * 3)
        ]
    )
    print("After filter: "+str(len(data)))
    
    # KMeans Modell fitten
    kmeanscluster = KMeans(n_clusters=3, random_state=0).fit(\
                     [[x] for x in data['ChestCircumference']*data['Height']]
                    )

    # Cluster bestimmen
    data['Cluster'] = kmeanscluster.predict(\
                     [[x] for x in data['ChestCircumference']*data['Height']]
                    )

    # Die Reihenfolge der Clusternummerierung bestimmen. Das kleinste
    # Zentrum steht an nullter Stelle. (Muss gemacht werden, da die
    # Reihenfolge der Cluster umgedreht sein kann und das Mapping
    # von Größe auf Clusternummer ebenfalls umgedreht wird).
    # Die Ausgabe von cluster_centers_ ist geordnet (0,1,2,3...)

    l1 = [x[0] for x in kmeanscluster.cluster_centers_]
    center_indices = ([l1.index(x) for x in sorted(l1)])
    mapping = {center_indices[0]:'L', center_indices[1]:'XL', center_indices[2]:'XXL'}
    # Mapping der Größer auf die Clusternummer
    data['Size'] = data['Cluster'].map(mapping)
    return data

def createModel(data):
    # Daten vorbereiten. Es sei angenommen, das Modell verwendet immer nur die 2500 neusten Daten für die Klassifikation.
    data = prepareData(data.tail(10000).reset_index(drop=True))
    # Train-test split erstellen
    X_train, X_test, y_train, y_test = train_test_split(\
        data.drop(columns=['Cluster','Size']),\
        data['Size'],\
        test_size=0.33,\
        random_state=21
    )
    
    # Decision Tree Klassifikator initialisieren
    clf = svm.SVC(kernel='linear')
    
    # Klassifikator fitten
    clf.fit(X_train,y_train)
    
    acc = clf.score(X_test,y_test)
    print("Accuracy: "+str(acc))
    if(acc > 0.95):
        print("Returning new model")
        return clf
    
    # Das Modell hat eine niedrigere Genauigkeit als 98%
    return None

def predict(instance,data):
    global model
    # Nur Vorhersagen treffen, wenn der Maximalwert in den Trainingsdaten nicht überschritten wird.
    if(
        (instance[0] <= data['Height'].max()) &\
        (instance[0] >= data['Height'].min()) &\
        (instance[1] <= data['ChestCircumference'].max()) &\
        (instance[1] >= data['ChestCircumference'].min())
    ):
        # Hier wird die Instanz zum Datensatz hinzugefügt
        data = data.append(pd.DataFrame.from_dict({'Height':[instance[0]],'ChestCircumference':[instance[1]]}),ignore_index=True)
        # Alle 500 Instanzen das Modell neu trainieren.
        if(len(data) % 500 == 0):
            # Modell neu trainieren
            print("Retraining model")
            new_model = createModel(data)
            if(new_model != None):
                print("Using new model")
                model = new_model
        # Vorhersage
        return model.predict([instance]),data
    else:
        return None, data

# das erste Modell erstellen
model = createModel(prepareData(modeldata))

###############################################
app = Flask(__name__)
app.debug = True

@app.route("/data_statistics")
def data_statistics():
    # Diese Route sendet Mittelwert und Standardabweichung des DataFrames zurück.
    global modeldata
    stats = [
        len(modeldata),\
        modeldata['Height'].mean(),\
        modeldata['Height'].std(),\
        modeldata['ChestCircumference'].mean(),\
        modeldata['ChestCircumference'].std()
    ]
    return "<p>"+str(stats)+"</p>"

@app.route("/predict")
def index():
    # An diese Route wird eine Instanz geschickt, für welche die Kleidergröße vorhergesagt wird.
    global modeldata
    # Request Daten holen
    height = float(request.args.get('height'))
    circ = float(request.args.get('circ'))
    instance=[height,circ]
    # Vorhersage erstellen
    prediction, modeldata = predict(instance,modeldata)

    if(prediction == None):
        return '{"Prediction":"Error"}'
    else:
        return '{"Prediction":"'+str(prediction[0])+'"}'

if __name__ == '__main__':
    app.run(port=5055)