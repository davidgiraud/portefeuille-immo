import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import uuid

# Custom function for currency formatting
def format_currency(value: float) -> str:
    """Format a number as currency with thousand separators (e.g., 1234567 -> 1,234,567)."""
    return f"{int(value):,}".replace(",", " ")

# Constants
MAX_BUILDINGS = 20
DEFAULT_CAP_RATE = 5.0
DEFAULT_LTV = 60.0
DEFAULT_OCCUPANCY = 95.0
DEFAULT_INDEXATION = 2.0
DEFAULT_INTEREST_RATE = 3.0
DEFAULT_OPERATING_COSTS = 20.0

# Set page config
st.set_page_config(page_title="Portefeuille Immobilier", layout="wide")
st.title("Simulateur de Portefeuille Immobilier - Bureaux")

# Description
st.markdown("""
Modélisez un portefeuille d'immeubles de bureaux avec :
- Rendement locatif (cap rate)
- Financement bancaire (LTV, taux d'intérêt)
- Indexation des loyers
- Variation du taux d'occupation
- Budget travaux (impact sur coût total)
- Frais d'exploitation
- Valeur de revente
""")

# Initialize session state
if "building_data" not in st.session_state:
    st.session_state.building_data = []

# Function to calculate building metrics
@st.cache_data
def calculate_building_metrics(building: dict) -> dict:
    """Calculate financial metrics for a single building."""
    try:
        # Validate critical inputs
        if building["Cap Rate Achat"] <= 0 or building["Cap Rate Sortie"] <= 0:
            raise ValueError("Les taux de rendement doivent être supérieurs à 0.")
        if building["Loyer Annuel"] < 0 or building["Budget Travaux"] < 0:
            raise ValueError("Les montants monétaires ne peuvent pas être négatifs.")

        # Acquisition value including works budget
        valeur_acquisition = building["Loyer Annuel"] / (building["Cap Rate Achat"] / 100)
        total_investment = valeur_acquisition + building["Budget Travaux"]

        # Financing
        dette = total_investment * (building["LTV"] / 100)
        equity = total_investment - dette

        # Debt service (monthly payment using amortization formula)
        taux_interet_mensuel = building["Taux Intérêt"] / 100 / 12
        nb_mois = building["Durée Financement"] * 12
        if taux_interet_mensuel > 0:
            mensualite = (dette * taux_interet_mensuel) / (1 - (1 + taux_interet_mensuel) ** (-nb_mois))
        else:
            mensualite = dette / nb_mois  # No interest case
        cout_total_interet = mensualite * nb_mois - dette

        # Occupancy rate with logistic growth
        t = building["Durée Financement"]
        evol_occupation = building["Évol Occupation"] / 100
        occupancy_initial = building["Occupation Initiale"] / 100
        # Logistic growth: occupancy = initial / (1 + e^(-kt)), capped at 100%
        k = 0.1  # Growth rate constant
        taux_occupation_final = occupancy_initial / (1 + np.exp(-k * evol_occupation * t))
        taux_occupation_final = np.clip(taux_occupation_final * 100, 0, 100)

        # Final revenue with indexation and occupancy
        loyer_final = building["Loyer Annuel"] * ((1 + building["Indexation Loyers"] / 100) ** t)
        revenu_final = loyer_final * (taux_occupation_final / 100)

        # Operating costs
        frais_exploitation = revenu_final * (building["Frais Exploitation"] / 100)
        noi = revenu_final - frais_exploitation - (mensualite * 12)

        # Exit value
        valeur_sortie = revenu_final / (building["Cap Rate Sortie"] / 100)

        return {
            "Nom": building["Nom"],
            "Valeur Acquisition (€)": round(total_investment),
            "Dette Bancaire (€)": round(dette),
            "Equity (€)": round(equity),
            "Revenu Final Annuel (€)": round(revenu_final),
            "NOI Annuel (€)": round(noi),
            "Coût Total Intérêt (€)": round(cout_total_interet),
            "Valeur de Sortie (€)": round(valeur_sortie)
        }
    except Exception as e:
        st.error(f"Erreur pour {building['Nom']}: {str(e)}")
        return None

# Function to generate visualizations
@st.cache_data
def generate_visualizations(df: pd.DataFrame, num_buildings: int) -> tuple:
    """Generate bar plots for exit value and equity/debt."""
    # Exit value plot
    fig1, ax1 = plt.subplots(figsize=(max(10, num_buildings * 2), 6))
    sns.barplot(x="Nom", y="Valeur de Sortie (€)", data=df, ax=ax1, palette="Blues_d")
    ax1.set_title("Valeur de sortie par immeuble")
    ax1.set_ylabel("Valeur (€)")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()

    # Equity vs Debt stacked bar plot
    fig2, ax2 = plt.subplots(figsize=(max(10, num_buildings * 2), 6))
    df.plot(kind="bar", x="Nom", y=["Equity (€)", "Dette Bancaire (€)"], stacked=True, ax=ax2, color=["#1f77b4", "#ff7f0e"])
    ax2.set_title("Equity et Dette par immeuble")
    ax2.set_ylabel("Montant (€)")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()

    return fig1, fig2

# Sidebar form for inputs
st.sidebar.header("Configurer les immeubles")
with st.sidebar.form("building_form"):
    num_buildings = st.number_input(
        "Nombre d'immeubles",
        min_value=1,
        max_value=MAX_BUILDINGS,
        value=1,
        step=1,
        help="Nombre total d'immeubles à modéliser (max 20)."
    )

    building_data = []
    for i in range(num_buildings):
        st.subheader(f"Immeuble {i+1}")
        st.markdown("**Nom** : Nom ou identifiant de l'immeuble.")
        name = st.text_input(f"Nom immeuble {i+1}", value=f"Immeuble {i+1}", key=f"name_{i}")
        st.markdown("**Loyer brut annuel** : Revenu locatif annuel brut en €.")
        loyer_annuel = st.number_input(
            f"Loyer brut annuel (€) {i+1}",
            min_value=0,
            value=100000,
            step=1000,
            key=f"loyer_{i}"
        )
        st.markdown("**Taux de rendement initial** : Cap rate à l'achat (%).")
        cap_rate_achat = st.number_input(
            f"Taux rendement initial (%) {i+1}",
            min_value=0.1,
            max_value=20.0,
            value=DEFAULT_CAP_RATE,
            step=0.1,
            key=f"cap_achat_{i}"
        )
        st.markdown("**LTV** : Loan-to-Value, pourcentage financé par la banque (%).")
        ltv = st.number_input(
            f"LTV (%) {i+1}",
            min_value=0.0,
            max_value=100.0,
            value=DEFAULT_LTV,
            step=1.0,
            key=f"ltv_{i}"
        )
        st.markdown("**Taux d'intérêt** : Taux annuel du prêt bancaire (%).")
        taux_interet = st.number_input(
            f"Taux d'intérêt (%/an) {i+1}",
            min_value=0.0,
            max_value=15.0,
            value=DEFAULT_INTEREST_RATE,
            step=0.1,
            key=f"interet_{i}"
        )
        st.markdown("**Taux d'occupation initial** : Pourcentage de location initial (%).")
        taux_occupation_init = st.number_input(
            f"Taux d'occupation initial (%) {i+1}",
            min_value=0.0,
            max_value=100.0,
            value=DEFAULT_OCCUPANCY,
            step=1.0,
            key=f"occup_init_{i}"
        )
        st.markdown("**Évolution taux occupation** : Variation annuelle du taux d'occupation (%/an).")
        evol_occupation = st.number_input(
            f"Évolution taux occupation (%/an) {i+1}",
            min_value=-10.0,
            max_value=10.0,
            value=0.0,
            step=0.1,
            key=f"evol_occup_{i}"
        )
        st.markdown("**Indexation loyers** : Augmentation annuelle des loyers (%/an).")
        indexation_loyers = st.number_input(
            f"Indexation loyers (%/an) {i+1}",
            min_value=0.0,
            max_value=10.0,
            value=DEFAULT_INDEXATION,
            step=0.1,
            key=f"indexation_{i}"
        )
        st.markdown("**Budget travaux** : Montant des travaux ou rénovations (€).")
        budget_travaux = st.number_input(
            f"Budget travaux (€) {i+1}",
            min_value=0,
            value=50000,
            step=1000,
            key=f"travaux_{i}"
        )
        st.markdown("**Frais exploitation** : Frais d'exploitation annuels (% du loyer).")
        frais_exploitation = st.number_input(
            f"Frais exploitation (% loyer) {i+1}",
            min_value=0.0,
            max_value=100.0,
            value=DEFAULT_OPERATING_COSTS,
            step=1.0,
            key=f"frais_expl_{i}"
        )
        st.markdown("**Durée financement** : Durée du prêt bancaire (années).")
        duree_financement = st.number_input(
            f"Durée financement (années) {i+1}",
            min_value=1,
            max_value=30,
            value=7,
            step=1,
            key=f"duree_{i}"
        )
        st.markdown("**Taux rendement sortie** : Cap rate à la revente (%).")
        cap_rate_sortie = st.number_input(
            f"Taux rendement sortie (%) {i+1}",
            min_value=0.1,
            max_value=20.0,
            value=6.0,
            step=0.1,
            key=f"cap_sortie_{i}"
        )

        building_data.append({
            "Nom": name,
            "Loyer Annuel": loyer_annuel,
            "Cap Rate Achat": cap_rate_achat,
            "LTV": ltv,
            "Taux Intérêt": taux_interet,
            "Occupation Initiale": taux_occupation_init,
            "Évol Occupation": evol_occupation,
            "Indexation Loyers": indexation_loyers,
            "Budget Travaux": budget_travaux,
            "Frais Exploitation": frais_exploitation,
            "Durée Financement": duree_financement,
            "Cap Rate Sortie": cap_rate_sortie
        })

    submitted = st.form_submit_button("Lancer la simulation")

# Simulation
if submitted and num_buildings > 0:
    st.session_state.building_data = building_data
    results = []
    total_equity, total_dette, total_valeur_sortie, total_noi = 0, 0, 0, 0

    for b in st.session_state.building_data:
        result = calculate_building_metrics(b)
        if result:
            results.append(result)
            total_equity += result["Equity (€)"]
            total_dette += result["Dette Bancaire (€)"]
            total_valeur_sortie += result["Valeur de Sortie (€)"]
            total_noi += result["NOI Annuel (€)"]

    if results:
        df = pd.DataFrame(results)

        # Display results
        st.subheader("Résultats par immeuble")
        st.dataframe(df, use_container_width=True)

        # Portfolio summary
        st.subheader("Résultats globaux du portefeuille")
        st.write(f"**Total Equity investie :** {format_currency(total_equity)} €")
        st.write(f"**Total Dette bancaire :** {format_currency(total_dette)} €")
        st.write(f"**NOI Annuel total :** {format_currency(total_noi)} €")
        st.write(f"**Valeur finale projetée :** {format_currency(total_valeur_sortie)} €")

        # Visualizations
        fig1, fig2 = generate_visualizations(df, num_buildings)
        st.pyplot(fig1)
        st.pyplot(fig2)

        # Export results
        csv = df.to_csv(index=False)
        st.download_button(
            label="Télécharger les résultats",
            data=csv,
            file_name="resultats_portefeuille.csv",
            mime="text/csv"
        )
    else:
        st.error("Aucun résultat valide. Vérifiez les données saisies.")
else:
    if num_buildings == 0:
        st.warning("Veuillez ajouter au moins un immeuble.")