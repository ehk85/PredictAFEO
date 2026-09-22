"""Analyse principale : construction du dataset (fenetres glissantes),
modelisation (3 modeles), validation temporelle, generation des figures et metriques.

Usage : python src/analyse_principale.py
Les figures sont ecrites dans resultats/figures/ et les metriques dans resultats/metriques.csv
"""
import os
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(__file__))
from lire_binsa import lire_binsa, noms_uniques
from construction_dataset import construire_fold, folds_glissants, CAUSES_MATERIELLES

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import (roc_auc_score, precision_score, recall_score,
                             f1_score, roc_curve, confusion_matrix)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "donnees")
FIG = os.path.join(BASE, "resultats", "figures")
os.makedirs(FIG, exist_ok=True)

FICHIER_PARC = os.path.join(DATA, "Appareil-2026-07-16_0843.xls")
FICHIERS_HIST = [os.path.join(DATA, "Suivi_des_Rapports-2026-07-16_0932.xls"),
                 os.path.join(DATA, "Suivi_des_Rapports-2026-07-16_0855.xls")]

FEATURES = ["age", "prix_maint", "nb_interv_total", "nb_depannages", "nb_maintenances",
            "nb_anomalies", "nb_defaillance_mat", "nb_en_defaut", "nb_vetuste"]


def charger():
    parc = lire_binsa(FICHIER_PARC)
    hist = pd.concat([noms_uniques(lire_binsa(f)) for f in FICHIERS_HIST], ignore_index=True)
    hist = hist.drop_duplicates(subset=["Exercice", "Nº Rapport", "Référence", "Date"])
    hist["Date_dt"] = pd.to_datetime(hist["Date"], errors="coerce")
    hist["TypeRapport"] = hist["Type"]
    asc_refs = set(parc[parc["Type"] == "Ascenseur"]["Référence"].dropna())
    parc_asc = (parc[parc["Type"] == "Ascenseur"]
                [["Référence", "Prix Maint.", "Type contrat", "Fréquence Maintenance",
                  "NomAgence", "Date de debut de contrat"]]
                .drop_duplicates("Référence").set_index("Référence"))
    parc_asc["prix_maint"] = pd.to_numeric(parc_asc["Prix Maint."], errors="coerce")
    return parc, hist, parc_asc, asc_refs


def modeles():
    return {
        "Régression logistique": make_pipeline(
            StandardScaler(), LogisticRegression(max_iter=1000, class_weight="balanced")),
        "Random Forest": RandomForestClassifier(
            n_estimators=300, class_weight="balanced", random_state=42, n_jobs=-1),
        "Gradient Boosting": HistGradientBoostingClassifier(
            max_iter=300, learning_rate=0.05, random_state=42),
    }


def fig_interventions_par_mois(hist):
    s = hist["Date_dt"].dt.to_period("M").value_counts().sort_index()
    s = s[(s.index >= pd.Period("2025-01")) & (s.index <= pd.Period("2026-07"))]
    fig, ax = plt.subplots(figsize=(11, 3.2))
    ax.bar([str(p) for p in s.index], s.values, color="#3b6ea5")
    ax.set_title("Interventions par mois (janvier 2025 – juillet 2026)")
    ax.tick_params(axis="x", rotation=90)
    plt.tight_layout(); plt.savefig(os.path.join(FIG, "interventions_par_mois.png"), dpi=130); plt.close()


def fig_equilibre(train, test):
    fig, ax = plt.subplots(figsize=(6, 3.4))
    x = np.arange(2); w = 0.35
    ax.bar(x - w/2, [train["target_all"].mean()*100, train["target_mat"].mean()*100], w, label="Train (T4-2025)", color="#3b6ea5")
    ax.bar(x + w/2, [test["target_all"].mean()*100, test["target_mat"].mean()*100], w, label="Test (T1-2026)", color="#c0504d")
    ax.set_xticks(x); ax.set_xticklabels(["Tout dépannage", "Défaillance mat."])
    ax.set_ylabel("% d'ascenseurs en panne"); ax.set_title("Équilibre des classes"); ax.legend()
    plt.tight_layout(); plt.savefig(os.path.join(FIG, "equilibre_classes.png"), dpi=130); plt.close()


def fig_roc(train, test, target, nom_fichier, titre):
    fig, ax = plt.subplots(figsize=(5.2, 5.2))
    for nom, m in modeles().items():
        m.fit(train[FEATURES].fillna(0), train[target])
        proba = m.predict_proba(test[FEATURES].fillna(0))[:, 1]
        fpr, tpr, _ = roc_curve(test[target], proba)
        auc = roc_auc_score(test[target], proba)
        ax.plot(fpr, tpr, label=f"{nom} (AUC={auc:.3f})")
    ax.plot([0, 1], [0, 1], "--", color="grey")
    ax.set_xlabel("Taux de faux positifs"); ax.set_ylabel("Taux de vrais positifs")
    ax.set_title(titre); ax.legend(loc="lower right")
    plt.tight_layout(); plt.savefig(os.path.join(FIG, nom_fichier), dpi=130); plt.close()


def fig_importance(train, target):
    rf = RandomForestClassifier(n_estimators=300, class_weight="balanced", random_state=42, n_jobs=-1)
    rf.fit(train[FEATURES].fillna(0), train[target])
    imp = pd.Series(rf.feature_importances_, index=FEATURES).sort_values()
    fig, ax = plt.subplots(figsize=(7.5, 4))
    ax.barh(imp.index, imp.values, color="#3b6ea5")
    ax.set_title("Importance des variables (défaillance matérielle)")
    plt.tight_layout(); plt.savefig(os.path.join(FIG, "importance_variables.png"), dpi=130); plt.close()
    return imp.sort_values(ascending=False)


def evaluer(train, test):
    lignes = []
    for target, libelle in [("target_all", "Tout dépannage"), ("target_mat", "Défaillance matérielle")]:
        Xtr, ytr = train[FEATURES].fillna(0), train[target]
        Xte, yte = test[FEATURES].fillna(0), test[target]
        for nom, m in modeles().items():
            m.fit(Xtr, ytr)
            p, proba = m.predict(Xte), m.predict_proba(Xte)[:, 1]
            lignes.append({
                "Cible": libelle, "Modèle": nom,
                "AUC": round(roc_auc_score(yte, proba), 3),
                "Précision": round(precision_score(yte, p, zero_division=0), 3),
                "Rappel": round(recall_score(yte, p, zero_division=0), 3),
                "F1": round(f1_score(yte, p, zero_division=0), 3),
            })
    return pd.DataFrame(lignes)


def main():
    T = pd.Timestamp
    parc, hist, parc_asc, asc_refs = charger()
    print("Historique:", len(hist), "|", hist["Date_dt"].min().date(), "->", hist["Date_dt"].max().date())

    # Entrainement : fenetres glissantes (3 origines) -> plus d'exemples
    origines = [T("2025-01-01"), T("2025-02-01"), T("2025-03-01")]
    train = folds_glissants(hist, parc_asc, asc_refs, origines, obs_mois=9, pred_mois=3)
    # Test : periode strictement future (observation avr-dec 2025 -> prediction T1-2026)
    test = construire_fold(hist, parc_asc, asc_refs,
                           T("2025-04-01"), T("2026-01-01"), T("2026-01-01"), T("2026-04-01"))
    print(f"Train (fenetres glissantes): {len(train)} lignes")
    print(f"Test  (T1-2026 futur)      : {len(test)} lignes")

    metriques = evaluer(train, test)
    metriques.to_csv(os.path.join(BASE, "resultats", "metriques.csv"), index=False)
    print("\n", metriques.to_string(index=False))

    fig_interventions_par_mois(hist)
    fig_equilibre(train, test)
    fig_roc(train, test, "target_all", "roc_tout_depannage.png", "ROC — tout dépannage (test T1-2026)")
    fig_roc(train, test, "target_mat", "roc_defaillance_mat.png", "ROC — défaillance matérielle (test T1-2026)")
    imp = fig_importance(train, "target_mat")
    imp.to_csv(os.path.join(BASE, "resultats", "importance_variables.csv"), header=["importance"])
    print("\nFigures et metriques ecrites dans resultats/")


if __name__ == "__main__":
    main()
