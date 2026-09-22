"""Application Flask — scoring du risque de panne d'un ascenseur.

Front (formulaire accessible) + back (modele supervise charge depuis modele_afeo.joblib).
Authentification de demonstration (back-office) : admin / afeo2026.

Lancer : python application/app.py  puis ouvrir http://127.0.0.1:5001
"""
import os
import sys
import joblib
import pandas as pd
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from interpretation import interpreter

BASE = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__)
app.secret_key = "afeo-demo-secret-key"  

# Identifiants de test 
ADMIN_USER = "admin"
ADMIN_PWD = "afeo2026"

_bundle = None
def get_model():
    global _bundle
    if _bundle is None:
        _bundle = joblib.load(os.path.join(BASE, "modele_afeo.joblib"))
    return _bundle


def login_requis(f):
    @wraps(f)
    def wrapper(*a, **k):
        if not session.get("connecte"):
            return redirect(url_for("login"))
        return f(*a, **k)
    return wrapper


@app.route("/login", methods=["GET", "POST"])
def login():
    erreur = None
    if request.method == "POST":
        if request.form.get("user") == ADMIN_USER and request.form.get("pwd") == ADMIN_PWD:
            session["connecte"] = True
            return redirect(url_for("index"))
        erreur = "Identifiants incorrects."
    return render_template("login.html", erreur=erreur)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/", methods=["GET", "POST"])
@login_requis
def index():
    resultat = None
    if request.method == "POST":
        b = get_model()
        vals = {}
        for f in b["features"]:
            raw = request.form.get(f, "").strip().replace(",", ".")
            if raw == "" and f in b["medianes"]:
                vals[f] = b["medianes"][f]
            else:
                try:
                    vals[f] = float(raw)
                except ValueError:
                    vals[f] = 0.0
        X = pd.DataFrame([[vals[f] for f in b["features"]]], columns=b["features"])
        proba = float(b["model"].predict_proba(X)[0, 1])
        resultat = interpreter(vals, proba, b)
    return render_template("index.html", resultat=resultat)


if __name__ == "__main__":
    app.run(debug=True, port=5001)
