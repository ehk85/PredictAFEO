"""Enrichissement du modele par la fiche technique des appareils.

Compare les performances AVANT / APRES ajout des variables techniques exploitables
(nombre de niveaux, charge) et evalue l'apport de l'age reel de mise en service
la ou il est connu.

Usage : python src/enrichissement_fiche_technique.py
Prerequis : les 3 exports Binsa + Fiche_technique.xlsx dans donnees/.
"""
import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from lire_binsa import lire_binsa, noms_uniques
from construction_dataset import construire_fold, folds_glissants
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "donnees")
T = pd.Timestamp

FEAT_BASE = ["age", "prix_maint", "nb_interv_total", "nb_depannages", "nb_maintenances",
             "nb_anomalies", "nb_defaillance_mat", "nb_en_defaut", "nb_vetuste"]
FEAT_ENR = FEAT_BASE + ["charge", "niveaux"]


def charger():
    parc = lire_binsa(os.path.join(DATA, "Appareil-2026-07-16_0843.xls"))
    hist = pd.concat([noms_uniques(lire_binsa(os.path.join(DATA, f)))
                      for f in ["Suivi_des_Rapports-2026-07-16_0932.xls",
                                "Suivi_des_Rapports-2026-07-16_0855.xls"]], ignore_index=True)
    hist = hist.drop_duplicates(subset=["Exercice", "Nº Rapport", "Référence", "Date"])
    hist["Date_dt"] = pd.to_datetime(hist["Date"], errors="coerce")
    hist["TypeRapport"] = hist["Type"]
    asc_refs = set(parc[parc["Type"] == "Ascenseur"]["Référence"].dropna())
    parc_asc = (parc[parc["Type"] == "Ascenseur"][["Référence", "Prix Maint.", "Date de debut de contrat"]]
                .drop_duplicates("Référence").set_index("Référence"))
    parc_asc["prix_maint"] = pd.to_numeric(parc_asc["Prix Maint."], errors="coerce")
    return hist, parc_asc, asc_refs


def fiche_technique():
    ft = pd.read_excel(os.path.join(DATA, "Fiche_technique.xlsx"))
    ft["Référence"] = ft["N° Référence"].astype(str).str.strip()
    ft["charge"] = pd.to_numeric(ft["Charge"], errors="coerce")
    niv = pd.to_numeric(ft["Nombre de niveaux"], errors="coerce")
    ft["niveaux"] = np.where(niv > 0, niv, np.nan)          # 0 = valeur manquante deguisee
    an = pd.to_numeric(ft["Mise en service Année"], errors="coerce")
    ft["age_reel"] = np.where(an > 1900, 2025 - an, np.nan)  # dispo pour ~15% du parc
    return ft.set_index("Référence")[["charge", "niveaux", "age_reel"]]


def rf_auc(train, test, feats, target):
    mdl = RandomForestClassifier(n_estimators=300, class_weight="balanced", random_state=42, n_jobs=-1)
    mdl.fit(train[feats].fillna(0), train[target])
    return roc_auc_score(test[target], mdl.predict_proba(test[feats].fillna(0))[:, 1])


def main():
    hist, parc_asc, asc_refs = charger()
    FT = fiche_technique()
    print("Couverture : niveaux %.0f%% | charge %.0f%% | age_reel %.0f%% (%d appareils)"
          % (100 * FT["niveaux"].notna().mean(), 100 * FT["charge"].notna().mean(),
             100 * FT["age_reel"].notna().mean(), FT["age_reel"].notna().sum()))

    def prep(df):
        df = df.join(FT[["charge", "niveaux"]])
        for c in ["charge", "niveaux"]:
            df[c] = df[c].fillna(df[c].median())
        return df

    train = prep(folds_glissants(hist, parc_asc, asc_refs,
                                 [T("2025-01-01"), T("2025-02-01"), T("2025-03-01")]))
    test = prep(construire_fold(hist, parc_asc, asc_refs,
                                T("2025-04-01"), T("2026-01-01"), T("2026-01-01"), T("2026-04-01")))

    print("\nAVANT / APRES enrichissement (Random Forest, validation temporelle) :")
    for target, lib in [("target_all", "Tout depannage"), ("target_mat", "Defaillance mat.")]:
        a = rf_auc(train, test, FEAT_BASE, target)
        b = rf_auc(train, test, FEAT_ENR, target)
        print("  %-18s AUC %.3f -> %.3f (delta %+.3f)" % (lib, a, b, b - a))

    sub = test.join(FT[["age_reel"]])
    sub = sub[sub["age_reel"].notna()]
    if len(sub) > 30:
        print("\nSur les %d ascenseurs a age reel connu, correlation avec la panne :" % len(sub))
        print("  age de contrat : %.3f" % sub["age"].corr(sub["target_mat"]))
        print("  age reel       : %.3f  (nettement plus predictif)" % sub["age_reel"].corr(sub["target_mat"]))


if __name__ == "__main__":
    main()
