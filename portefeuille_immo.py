
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

st.set_page_config(page_title="Portefeuille Immobilier", layout="wide")
st.title("Simulateur de Portefeuille Immobilier - Bureaux")

st.markdown("""
Modélisez plusieurs immeubles :
- Rendement locatif (cap rate)
- Financement bancaire (LTV)
- Indexation des loyers
- Variation du taux d'occupation
- Budget travaux
- Valeur de revente
""")

# Formulaire multi-immeubles
st.sidebar.header("Ajouter des immeubles")
building_data = []

num_buildings = st.sidebar.number_input("Nombre d'immeubles", min_value=1, max_value=20, value=1, step=1)

for i in range(num_buildings):
    st.sidebar.subheader(f"Immeuble {i+1}")
    name = st.sidebar.text_input(f"Nom immeuble {i+1}", value=f"Immeuble {i+1}")
    loyer_annuel = st.sidebar.number_input(f"Loyer brut annuel (€) {i+1}", min_value=0, value=100000, step=1000)
    cap_rate_achat = st.sidebar.number_input(f"Taux rendement initial (%) {i+1}", min_value=1.0, max_value=20.0, value=5.0, step=0.1)
    ltv = st.sidebar.number_input(f"LTV (%) {i+1}", min_value=0.0, max_value=100.0, value=60.0, step=1.0)
    taux_occupation_init = st.sidebar.number_input(f"Taux d'occupation initial (%) {i+1}", min_value=0.0, max_value=100.0, value=95.0, step=1.0)
    evol_occupation = st.sidebar.number_input(f"Évolution taux occupation (%/an) {i+1}", min_value=-10.0, max_value=10.0, value=0.0, step=0.1)
    indexation_loyers = st.sidebar.number_input(f"Indexation loyers (%/an) {i+1}", min_value=0.0, max_value=10.0, value=2.0, step=0.1)
    budget_travaux = st.sidebar.number_input(f"Budget travaux (€) {i+1}", min_value=0, value=50000, step=1000)
    duree_financement = st.sidebar.number_input(f"Durée financement (années) {i+1}", min_value=1, max_value=30, value=7, step=1)
    cap_rate_sortie = st.sidebar.number_input(f"Taux rendement sortie (%) {i+1}", min_value=1.0, max_value=20.0, value=6.0, step=0.1)

    building_data.append({
        "Nom": name,
        "Loyer Annuel": loyer_annuel,
        "Cap Rate Achat": cap_rate_achat,
        "LTV": ltv,
        "Occupation Initiale": taux_occupation_init,
        "Évol Occupation": evol_occupation,
        "Indexation Loyers": indexation_loyers,
        "Budget Travaux": budget_travaux,
        "Durée Financement": duree_financement,
        "Cap Rate Sortie": cap_rate_sortie
    })

# Simulation
if st.button("Lancer la simulation"):
    results = []
    total_equity, total_dette, total_valeur_sortie = 0, 0, 0

    for b in building_data:
        valeur_acquisition = b["Loyer Annuel"] / (b["Cap Rate Achat"] / 100)
        dette = valeur_acquisition * (b["LTV"] / 100)
        equity = valeur_acquisition - dette
        total_equity += equity
        total_dette += dette

        taux_occupation_final = b["Occupation Initiale"] + b["Évol Occupation"] * b["Durée Financement"]
        taux_occupation_final = np.clip(taux_occupation_final, 0, 100)

        loyer_final = b["Loyer Annuel"] * ((1 + b["Indexation Loyers"] / 100) ** b["Durée Financement"])
        revenu_final = loyer_final * (taux_occupation_final / 100)

        valeur_sortie = revenu_final / (b["Cap Rate Sortie"] / 100)
        total_valeur_sortie += valeur_sortie

        results.append({
            "Nom": b["Nom"],
            "Valeur Acquisition (€)": round(valeur_acquisition),
            "Dette Bancaire (€)": round(dette),
            "Equity (€)": round(equity),
            "Revenu Final Annuel (€)": round(revenu_final),
            "Valeur de Sortie (€)": round(valeur_sortie)
        })

    df = pd.DataFrame(results)
    st.subheader("Résultats par immeuble")
    st.dataframe(df)

    st.subheader("Résultats globaux du portefeuille")
    st.write(f"**Total Equity investie :** {round(total_equity):,} €")
    st.write(f"**Total Dette bancaire :** {round(total_dette):,} €")
    st.write(f"**Valeur finale projetée :** {round(total_valeur_sortie):,} €")

    fig, ax = plt.subplots(figsize=(10,6))
    sns.barplot(x="Nom", y="Valeur de Sortie (€)", data=df, ax=ax)
    ax.set_title("Valeur de sortie par immeuble")
    ax.set_ylabel("Valeur (€)")
    plt.xticks(rotation=45)
    st.pyplot(fig)
