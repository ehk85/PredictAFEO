# Journal de bord — parcours des données

> À conserver et à exploiter dans le mémoire : ce parcours illustre concrètement les
> difficultés d'accès et de qualité des données en PME, qui constituent l'angle original du sujet.
> Ce n'est pas une anecdote, c'est un résultat de l'étude de faisabilité.

## Chronologie

**Étape 1 — Premier export du parc : inexploitable.**
L'export initial du parc (`Appareil-2026-06-29`) ne contenait que **25 appareils**, alors que
l'historique référençait plus de 1 500 appareils distincts. Il s'agissait d'un échantillon filtré,
non représentatif. Seuls 12 de ces 25 appareils apparaissaient dans les interventions.

**Étape 2 — Premier export d'interventions : une seule période.**
L'export `Suivi_des_Rapports-2026-06-29` ne couvrait qu'**un seul mois** (juin 2026), et non les
18 mois attendus : le filtre de dates était resté sur sa valeur par défaut (mois en cours).
Avec un seul mois d'historique, aucune modélisation temporelle n'était possible.

**Étape 3 — Diagnostic et reformulation de la demande.**
Le problème n'était pas la disponibilité des données mais les **paramètres d'export**. Deux demandes
précises ont été formulées : ré-exporter le parc complet (toutes agences), et ré-exporter les
interventions avec un filtre de dates couvrant toute la période d'étude.

**Étape 4 — Exports corrects obtenus.**
- Parc (`Appareil-2026-07-16_0843`) : **3 744 appareils** (dont 1 855 ascenseurs).
- Interventions 2025 (`Suivi_des_Rapports-2026-07-16_0932`) : janvier → décembre 2025, 31 702 lignes.
- Interventions 2026 (`Suivi_des_Rapports-2026-07-16_0855`) : janvier → juillet 2026, 16 860 lignes.
- Historique fusionné et dédoublonné : **48 435 interventions sur 18 mois**.

## Enseignements pour le mémoire

1. **L'accès aux données est le premier facteur limitant en PME**, avant toute question d'algorithme.
2. **La qualité d'un export dépend de paramètres non triviaux** (filtres de dates, de périmètre) qu'il
   faut expliciter et vérifier.
3. **Vérifier systématiquement la volumétrie et la plage temporelle** d'un fichier avant de l'exploiter :
   un fichier « présent » n'est pas un fichier « complet ».

## Limites de qualité résiduelles (à assumer)

- Pas de **marque / modèle constructeur** dans l'export du parc.
- L'« âge » disponible est une **ancienneté de contrat**, pas l'âge réel de l'ascenseur.
- Le parc n'inclut que les appareils **encore sous contrat** (pas de résiliés).
