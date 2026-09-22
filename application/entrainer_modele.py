"""Entraine le modele final (RF + variables enrichies) et le sauvegarde pour l'application.
Usage : python application/entrainer_modele.py
Produit : application/modele_afeo.joblib
"""
import os, sys, joblib
import numpy as np, pandas as pd
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "src"))
from lire_binsa import lire_binsa, noms_uniques
from construction_dataset import construire_fold, folds_glissants, CAUSES_MATERIELLES
from sklearn.ensemble import RandomForestClassifier

DATA = os.path.join(BASE, "donnees")
T = pd.Timestamp
FEAT = ["age", "prix_maint", "nb_interv_total", "nb_depannages", "nb_maintenances",
        "nb_anomalies", "nb_defaillance_mat", "nb_en_defaut", "nb_vetuste", "charge", "niveaux"]

parc = lire_binsa(os.path.join(DATA, "Appareil-2026-07-16_0843.xls"))
hist = pd.concat([noms_uniques(lire_binsa(os.path.join(DATA, f)))
                  for f in ["Suivi_des_Rapports-2026-07-16_0932.xls", "Suivi_des_Rapports-2026-07-16_0855.xls"]],
                 ignore_index=True).drop_duplicates(subset=["Exercice", "Nº Rapport", "Référence", "Date"])
hist["Date_dt"] = pd.to_datetime(hist["Date"], errors="coerce"); hist["TypeRapport"] = hist["Type"]
asc_refs = set(parc[parc["Type"] == "Ascenseur"]["Référence"].dropna())
parc_asc = parc[parc["Type"] == "Ascenseur"][["Référence", "Prix Maint.", "Date de debut de contrat"]].drop_duplicates("Référence").set_index("Référence")
parc_asc["prix_maint"] = pd.to_numeric(parc_asc["Prix Maint."], errors="coerce")
ft = pd.read_excel(os.path.join(DATA, "Fiche_technique.xlsx"))
ft["Référence"] = ft["N° Référence"].astype(str).str.strip()
ft["charge"] = pd.to_numeric(ft["Charge"], errors="coerce")
niv = pd.to_numeric(ft["Nombre de niveaux"], errors="coerce"); ft["niveaux"] = np.where(niv > 0, niv, np.nan)
FT = ft.set_index("Référence")[["charge", "niveaux"]]

train = folds_glissants(hist, parc_asc, asc_refs, [T("2025-01-01"), T("2025-02-01"), T("2025-03-01")])
train = train.join(FT)
med = {"charge": train["charge"].median(), "niveaux": train["niveaux"].median()}
for c in ["charge", "niveaux"]:
    train[c] = train[c].fillna(med[c])

model = RandomForestClassifier(n_estimators=300, class_weight="balanced", random_state=42,
                                n_jobs=-1, oob_score=True)
model.fit(train[FEAT].fillna(0), train["target_mat"])

# Reference pour l'interpretation : position du score dans le parc.
# On utilise les predictions OOB (out-of-bag) et non predict_proba(train), qui serait en
# grande partie de la memorisation et gonflerait artificiellement la distribution.
scores_tries = sorted(model.oob_decision_function_[:, 1].tolist())

# Saisonnalite mensuelle des defaillances materielles sur tout l'historique (indice moyen = 1.0)
mat = hist[(hist["TypeRapport"] == "Intervention") & hist["Origine"].isin(CAUSES_MATERIELLES)]
mat = mat.dropna(subset=["Date_dt"])
mois_couverts = pd.period_range(hist["Date_dt"].min().to_period("M"), hist["Date_dt"].max().to_period("M"), freq="M")
occurrences = pd.Series([p.month for p in mois_couverts]).value_counts().reindex(range(1, 13), fill_value=0)
compte = mat["Date_dt"].dt.month.value_counts().reindex(range(1, 13), fill_value=0)
taux = compte / occurrences.replace(0, np.nan)
saisonnalite_mois = {int(m): float(v) for m, v in (taux / taux.mean()).fillna(1.0).items()}

joblib.dump({
    "model": model, "features": FEAT, "medianes": med,
    "ref": {
        "scores_tries": scores_tries,
        "saisonnalite_mois": saisonnalite_mois,
    },
}, os.path.join(BASE, "application", "modele_afeo.joblib"))
print("Modele sauvegarde. Variables:", FEAT)
print("Saisonnalite (indice/mois):", {k: round(v, 2) for k, v in saisonnalite_mois.items()})
