"""Enrichissement du modele par le NLP (commentaires d'anomalie) et par des variables
de recence/tendance (table des pannes repetitives).

Compare les performances de facon incrementale :
  base -> + fiche technique -> + NLP -> + recence.

Resultat : le NLP apporte un petit gain reel ; les variables de recence issues de la
table des pannes repetitives sont largement redondantes avec les comptages deja presents
et n'ameliorent pas la generalisation (finding de selection de variables).

Usage : python src/enrichissement_nlp_recence.py
Prerequis dans donnees/ : les 3 exports Binsa + Fiche_technique.xlsx + Pannes_repetitives.xlsx
"""
import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from lire_binsa import lire_binsa, noms_uniques
from construction_dataset import construire_fold
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE_DIR, "donnees")
T = pd.Timestamp

BASE = ["age", "prix_maint", "nb_interv_total", "nb_depannages", "nb_maintenances",
        "nb_anomalies", "nb_defaillance_mat", "nb_en_defaut", "nb_vetuste"]
FT_C = ["charge", "niveaux"]

LEXIQUE = {
    "nlp_remplace": ["remplace", "remplacer", "remplacement"],
    "nlp_devis":    ["devis"],
    "nlp_vetuste":  ["vétuste", "vetuste", "usure", "rénovation", "renovation", "modernisation"],
    "nlp_defaut":   ["défaut", "defaut", " hs", "hors service", "panne"],
    "nlp_surveil":  ["surveiller", "prévoir", "prevoir", "préconis", "preconis"],
    "nlp_porte":    ["porte", "serrure", "opérateur", "operateur", "fermator"],
    "nlp_traction": ["poulie", "traction", "moteur", "frein", "câble", "cable"],
}
NIV_REP = {"Isole (1)": 1, "Repetitif (2)": 2, "Eleve (3-4)": 3, "Critique (5+)": 4}


def charger():
    parc = lire_binsa(os.path.join(DATA, "Appareil-2026-07-16_0843.xls"))
    hist = pd.concat([noms_uniques(lire_binsa(os.path.join(DATA, f)))
                      for f in ["Suivi_des_Rapports-2026-07-16_0932.xls",
                                "Suivi_des_Rapports-2026-07-16_0855.xls"]], ignore_index=True)
    hist = hist.drop_duplicates(subset=["Exercice", "Nº Rapport", "Référence", "Date"])
    hist["Date_dt"] = pd.to_datetime(hist["Date"], errors="coerce")
    hist["TypeRapport"] = hist["Type"]
    hist["com"] = hist["Commentaire Anomalie"].fillna("").astype(str).str.lower()
    asc_refs = set(parc[parc["Type"] == "Ascenseur"]["Référence"].dropna())
    parc_asc = (parc[parc["Type"] == "Ascenseur"][["Référence", "Prix Maint.", "Date de debut de contrat"]]
                .drop_duplicates("Référence").set_index("Référence"))
    parc_asc["prix_maint"] = pd.to_numeric(parc_asc["Prix Maint."], errors="coerce")

    ft = pd.read_excel(os.path.join(DATA, "Fiche_technique.xlsx"))
    ft["Référence"] = ft["N° Référence"].astype(str).str.strip()
    ft["charge"] = pd.to_numeric(ft["Charge"], errors="coerce")
    niv = pd.to_numeric(ft["Nombre de niveaux"], errors="coerce")
    ft["niveaux"] = np.where(niv > 0, niv, np.nan)
    FT = ft.set_index("Référence")[["charge", "niveaux"]]

    pr = pd.read_excel(os.path.join(DATA, "Pannes_repetitives.xlsx"))
    pr["Date_Panne"] = pd.to_datetime(pr["Date_Panne"], errors="coerce")
    pr["ref"] = pr["Ref_Appli"].astype(str).str.strip()
    pr["niv_rep"] = pr["Niveau_Repetition"].map(NIV_REP).fillna(0)
    return hist, parc_asc, asc_refs, FT, pr


def feats_nlp(obs, asc_refs):
    g = obs.groupby("Référence")
    out = pd.DataFrame(index=list(asc_refs))
    txt = g["com"].apply(lambda s: " ".join(s))
    out["nlp_nb_com"] = g["com"].apply(lambda s: (s.str.strip() != "").sum()).reindex(out.index).fillna(0)
    for name, kws in LEXIQUE.items():
        out[name] = txt.apply(lambda t: sum(t.count(k) for k in kws)).reindex(out.index).fillna(0)
    return out


def feats_recence(pr, asc_refs, obs_start, obs_end):
    w = pr[(pr["Date_Panne"] >= obs_start) & (pr["Date_Panne"] < obs_end) & (pr["ref"].isin(asc_refs))]
    g = w.groupby("ref")
    out = pd.DataFrame(index=list(asc_refs))
    out["rec_nb_pannes"] = g.size().reindex(out.index).fillna(0)
    out["rec_max_mois"] = g["Nb_Pannes_Mois"].max().reindex(out.index).fillna(0)
    out["rec_niv_max"] = g["niv_rep"].max().reindex(out.index).fillna(0)
    out["rec_recence_j"] = ((obs_end - g["Date_Panne"].max()).dt.days).reindex(out.index).fillna(999)
    p90 = w[w["Date_Panne"] >= (obs_end - pd.Timedelta(days=90))].groupby("ref").size()
    out["rec_pannes_90j"] = p90.reindex(out.index).fillna(0)
    return out


def main():
    hist, parc_asc, asc_refs, FT, pr = charger()

    def enrich(df, o_start, o_end):
        df = df.join(FT)
        for c in FT_C:
            df[c] = df[c].fillna(df[c].median())
        obs = hist[(hist["Date_dt"] >= o_start) & (hist["Date_dt"] < o_end) & (hist["Référence"].isin(asc_refs))]
        df = df.join(feats_nlp(obs, asc_refs))
        df = df.join(feats_recence(pr, asc_refs, o_start, o_end))
        return df

    train_parts = []
    for o in [T("2025-01-01"), T("2025-02-01"), T("2025-03-01")]:
        oe = o + pd.DateOffset(months=9); pe = oe + pd.DateOffset(months=3)
        train_parts.append(enrich(construire_fold(hist, parc_asc, asc_refs, o, oe, oe, pe), o, oe))
    train = pd.concat(train_parts)
    test = enrich(construire_fold(hist, parc_asc, asc_refs, T("2025-04-01"), T("2026-01-01"),
                                  T("2026-01-01"), T("2026-04-01")), T("2025-04-01"), T("2026-01-01"))

    NLP = [c for c in train.columns if c.startswith("nlp_")]
    REC = [c for c in train.columns if c.startswith("rec_")]

    def auc(feats, tgt):
        m = RandomForestClassifier(n_estimators=300, class_weight="balanced", random_state=42, n_jobs=-1)
        m.fit(train[feats].fillna(0), train[tgt])
        return roc_auc_score(test[tgt], m.predict_proba(test[feats].fillna(0))[:, 1])

    for tgt, lib in [("target_all", "Tout depannage"), ("target_mat", "Defaillance mat.")]:
        b = auc(BASE, tgt); f = auc(BASE + FT_C, tgt)
        n = auc(BASE + FT_C + NLP, tgt); r = auc(BASE + FT_C + NLP + REC, tgt)
        print("=== %s ===" % lib)
        print("  base                       : %.3f" % b)
        print("  + fiche technique          : %.3f (%+.3f)" % (f, f - b))
        print("  + NLP (commentaires)       : %.3f (%+.3f)  <- meilleur" % (n, n - f))
        print("  + recence (table pannes)   : %.3f (%+.3f)  (redondant, non retenu)" % (r, r - n))
        print()


if __name__ == "__main__":
    main()
