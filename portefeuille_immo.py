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


# ---- Fonctions pour l'analyse de sensibilité (TRI / IRR) ----

def calculate_irr(cash_flows, max_iter=1000, tol=1e-8):
    """
    Calcule le TRI (Taux de Rendement Interne) par la méthode de Newton-Raphson.

    Le TRI est le taux annuel qui rend la VAN (Valeur Actuelle Nette) égale à zéro.
    En pratique : c'est le rendement annualisé de votre mise de fonds.

    cash_flows[0] doit être négatif (= mise de fonds initiale).
    Retourne le TRI en décimal (ex: 0.12 = 12 %), ou NaN si pas de solution trouvée.
    """
    rate = 0.10  # point de départ : on suppose 10% de rendement
    for _ in range(max_iter):
        # VAN au taux courant
        npv = sum(cf / (1 + rate) ** t for t, cf in enumerate(cash_flows))
        # Dérivée de la VAN par rapport au taux (nécessaire pour Newton-Raphson)
        dnpv = sum(-t * cf / (1 + rate) ** (t + 1) for t, cf in enumerate(cash_flows))
        if abs(dnpv) < 1e-12:
            break
        new_rate = rate - npv / dnpv
        if abs(new_rate - rate) < tol:
            return new_rate
        rate = new_rate
    return float("nan")  # pas de solution convergente


def build_cash_flows(building, cap_rate_sortie_pct, occupation_finale_pct):
    """
    Construit les flux de trésorerie annuels en fonds propres pour un immeuble.

    Retourne une liste [CF_an0, CF_an1, ..., CF_anT] où :
    - CF_an0 est négatif (mise de fonds initiale)
    - CF_anT inclut le produit de cession de l'immeuble

    Les paramètres cap_rate_sortie_pct et occupation_finale_pct permettent
    de faire des simulations "et si..." sans modifier les données de base.
    """
    loyer = building["Loyer Annuel"]
    cap_rate_achat = building["Cap Rate Achat"] / 100
    ltv = building["LTV"] / 100
    taux_interet = building["Taux Intérêt"] / 100
    indexation = building["Indexation Loyers"] / 100
    frais_expl_pct = building["Frais Exploitation"] / 100
    travaux = building["Budget Travaux"]
    duree = building["Durée Financement"]
    cap_rate_sortie = cap_rate_sortie_pct / 100
    occupation = occupation_finale_pct / 100

    # Valeur d'acquisition et structure de financement
    valeur_acquisition = loyer / cap_rate_achat
    total_investissement = valeur_acquisition + travaux
    dette = total_investissement * ltv
    equity = total_investissement - dette  # apport en fonds propres (an 0)

    # Mensualité constante — amortissement français (même formule que le reste de l'app)
    r_m = taux_interet / 12  # taux mensuel
    n = duree * 12           # nombre de mensualités
    if r_m > 0:
        mensualite = (dette * r_m) / (1 - (1 + r_m) ** (-n))
    else:
        mensualite = dette / n
    service_annuel = mensualite * 12

    # Construction des flux année par année
    cash_flows = [-equity]  # an 0 : sortie de fonds propres (valeur négative)
    for y in range(1, duree + 1):
        # Le loyer croît chaque année avec l'indexation, modulé par le taux d'occupation
        revenue_y = loyer * ((1 + indexation) ** y) * occupation
        frais_y = revenue_y * frais_expl_pct
        cf_y = revenue_y - frais_y - service_annuel  # flux opérationnel annuel
        if y == duree:
            # Dernière année : on ajoute le produit de cession
            # (la dette est entièrement remboursée sur la durée, donc reste = 0 €)
            revenu_final = loyer * ((1 + indexation) ** duree) * occupation
            valeur_sortie = revenu_final / cap_rate_sortie
            cf_y += valeur_sortie  # tout le produit revient aux fonds propres
        cash_flows.append(cf_y)

    return cash_flows


def compute_sensitivity_grid(building, cap_rates, occupations):
    """
    Calcule le TRI (%) pour chaque combinaison de cap rate de sortie et taux d'occupation.

    Retourne un tableau 2D numpy :
    - lignes  = taux d'occupation (du plus bas au plus haut)
    - colonnes = cap rate de sortie (du plus bas au plus haut)
    """
    grid = np.zeros((len(occupations), len(cap_rates)))
    for i, occ in enumerate(occupations):
        for j, cr in enumerate(cap_rates):
            cfs = build_cash_flows(building, cr, occ)
            irr = calculate_irr(cfs)
            # Stocker en %, arrondi à 1 décimale
            grid[i, j] = round(irr * 100, 1) if not np.isnan(irr) else np.nan
    return grid


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

        # ---- Analyse de sensibilité — TRI (IRR) ----
        st.markdown("---")
        st.subheader("Analyse de sensibilité — TRI (IRR)")

        with st.expander("ℹ️ Qu'est-ce que le TRI (IRR) ?"):
            st.markdown("""
            Le **TRI (Taux de Rendement Interne)** — ou **IRR** en anglais (*Internal Rate of Return*) —
            est le taux de rendement annualisé de votre mise de fonds.

            **En pratique :**
            - C'est le taux qui rend votre investissement "neutre" : les gains futurs,
              ramenés à aujourd'hui, compensent exactement votre mise initiale.
            - Si le TRI > coût d'emprunt → l'opération crée de la valeur.
            - Si le TRI < coût d'emprunt → l'effet de levier joue contre vous.

            **Standard européen (INREV / ILPA) :**
            Le TRI et le multiple MOIC sont les deux métriques de référence pour
            les fonds immobiliers en Europe — privilégiez-les face au simple rendement annuel.

            **Comment lire la heatmap :**
            - Chaque case montre le TRI (%) pour une combinaison hypothétique de
              *cap rate de sortie* et *taux d'occupation final*.
            - Cases **vertes** = meilleure rentabilité, cases **rouges** = moins bonne.
            - Utile pour évaluer votre marge de sécurité : même si l'occupation baisse
              ou si le marché se détend (cap rate plus élevé), le projet reste-t-il viable ?
            """)

        # Sélecteur d'immeuble (utile si plusieurs immeubles dans le portefeuille)
        building_names = [b["Nom"] for b in st.session_state.building_data]
        selected_name = st.selectbox(
            "Immeuble à analyser",
            building_names,
            key="sensitivity_building",
            help="Choisissez l'immeuble pour lequel afficher la heatmap de sensibilité."
        )
        selected_building = next(
            b for b in st.session_state.building_data if b["Nom"] == selected_name
        )

        # Plages de variation pour les deux axes de la heatmap
        cap_rates_range = np.arange(4.0, 9.5, 0.5)   # cap rate sortie : de 4 % à 9 %
        occupations_range = np.arange(70, 105, 5)     # taux d'occupation : de 70 % à 100 %

        # Calcul de la grille TRI
        grid = compute_sensitivity_grid(selected_building, cap_rates_range, occupations_range)

        # Tracé de la heatmap
        fig_sens, ax_sens = plt.subplots(figsize=(12, 6))
        sns.heatmap(
            grid,
            annot=True,         # afficher la valeur dans chaque case
            fmt=".1f",          # 1 décimale
            cmap="RdYlGn",      # rouge (mauvais) → jaune → vert (bon)
            ax=ax_sens,
            xticklabels=[f"{cr:.1f}%" for cr in cap_rates_range],
            yticklabels=[f"{occ:.0f}%" for occ in occupations_range],
            cbar_kws={"label": "TRI (%)"},
            linewidths=0.5,
            linecolor="lightgrey",
        )
        ax_sens.set_title(
            f"TRI (%) — Cap Rate de Sortie × Taux d'Occupation Final\n{selected_name}",
            fontsize=13,
            pad=12,
        )
        ax_sens.set_xlabel("Cap Rate de Sortie (%)")
        ax_sens.set_ylabel("Taux d'Occupation Final (%)")
        plt.tight_layout()
        st.pyplot(fig_sens)
        plt.close(fig_sens)  # libérer la mémoire après affichage

        st.caption(
            "⚠️ *Estimation — la valeur d'actif est calculée par capitalisation du revenu "
            "(cap rate), ce qui est une approximation simplifiée d'une valorisation "
            "indépendante formelle au sens de l'AIFMD.*"
        )

    else:
        st.error("Aucun résultat valide. Vérifiez les données saisies.")
else:
    if num_buildings == 0:
        st.warning("Veuillez ajouter au moins un immeuble.")