# Bibliothèques nécessaires au dashboard
import streamlit as st  # interface web interactive
import pandas as pd     # manipulation et analyse des données tabulaires
import numpy as np      # calculs numériques (ex: annualisation de la volatilité)
import matplotlib.pyplot as plt  # tracé des graphiques (barres, courbes)
import seaborn as sns   # heatmap pour la matrice de corrélation
# Partie 1: nettoyage 
# Configuration générale de la page Streamlit

st.set_page_config(#titrre pour la page
    page_title="Dashboard Boursier BVMT",
     page_icon="📈",
    layout="wide"
)
#Partie 1 : nettoyage 
# Chargement et nettoyage des données 
# @st.cache_data évite de recharger les fichiers à chaque interaction utilisateur
@st.cache_data
def load_data():
    def clean(df):
        # Supprimer les espaces superflus dans les noms de colonnes et la colonne VALEUR
        df.columns = df.columns.str.strip()
        df['VALEUR'] = df['VALEUR'].astype(str).str.strip()
        # Convertir la colonne date (format jour/mois/année)
        df['SEANCE'] = pd.to_datetime(df['SEANCE'], dayfirst=True)
        # Supprimer les doublons éventuels
        df = df.drop_duplicates()
        # Retirer les lignes avec des valeurs manquantes sur les colonnes de prix essentielles
        cols_vitales = ['OUVERTURE', 'CLOTURE', 'PLUS_BAS', 'PLUS_HAUT']
        df = df.dropna(subset=cols_vitales)
        # Exclure les clôtures nulles ou négatives (données aberrantes)
        df = df[df['CLOTURE'] > 0]
        # Filtrer uniquement les groupes sectoriels souhaités (11, 12, 51, 52)
        df = df[df['GROUPE'].isin([11, 12, 51, 52])]
        # Trier par date pour garantir l'ordre chronologique des calculs
        df = df.sort_values("SEANCE")
        # Calculer le rendement journalier en % : (clôture - ouverture) / ouverture * 100
        df['RENDEMENT_J'] = (
            (df['CLOTURE'] - df['OUVERTURE']) / df['OUVERTURE'] * 100#ajouter de nouvelle colonne
        )
        return df

    
    df23 = clean(pd.read_csv("2023.csv", sep=";"))
    df24 = clean(pd.read_csv("2024.csv", sep=";"))
    df25 = clean(pd.read_csv("2025.csv", sep=";"))
    return df23, df24, df25#nettoyer les doner et les recharger


df23, df24, df25 = load_data()

#Fonctions de calcul des KPI 
def performance(df):
    return (
        (df['CLOTURE'].iloc[-1] - df['OUVERTURE'].iloc[0])
        / df['OUVERTURE'].iloc[0] * 100
    )


def calc_kpi(df):
    kpi1 = df.groupby('VALEUR').apply(performance)
    kpi2 = df.groupby('VALEUR')['RENDEMENT_J'].std() * np.sqrt(252)
    kpi3 = (
        df.groupby('VALEUR')['RENDEMENT_J'].mean()
        / df.groupby('VALEUR')['RENDEMENT_J'].std()
    )
    return kpi1, kpi2, kpi3


# Pré-calcul des KPI et stockage par année pour un accès rapide via les filtres
kpi_map = {
    "2023": calc_kpi(df23),
    "2024": calc_kpi(df24),
    "2025": calc_kpi(df25)
}

# Dictionnaire pour accéder facilement au DataFrame brut selon l'année sélectionnée
df_map = {
    "2023": df23,
    "2024": df24,
    "2025": df25
}

# Barre latérale de navigation et filtres
st.sidebar.title("📊 Navigation")

# Sélection de la page à afficher
page = st.sidebar.radio(
    "Choisir une page",
    ["📈 Prix",
     "📊 Performance",
     "📉 Volatilité",
     "⚖️ Sharpe",
     "🏆 10 Top entreprises",
     "🌐 Corrélation",
     "📋 Données Filtrée"]
)

# Filtre par année : charge le bon DataFrame et les KPI associés
annee = st.sidebar.selectbox("Année", ["2023", "2024", "2025"])
df = df_map[annee]
kpi1, kpi2, kpi3 = kpi_map[annee]

# Filtre multi-sélection sur les entreprises disponibles (3 par défaut)
valeurs = st.sidebar.multiselect(
    "Actions",
    df['VALEUR'].unique(),
    default=df['VALEUR'].unique()[:3]
)

# Sous-ensemble du DataFrame limité aux entreprises sélectionnées
df_filtre = df[df['VALEUR'].isin(valeurs)]

# Titre affiché en haut de chaque page
st.title("📊 Dashboard Boursier")


#Fonction utilitaire : pie chart générique
def draw_pie(sizes, labels, colors, title, total):
    # Filtrer les tranches vides pour éviter les erreurs matplotlib
    filtered = [(l, s, c) for l, s, c in zip(labels, sizes, colors) if s > 0]
    if not filtered:
        return None
    labels_f, sizes_f, colors_f = zip(*filtered)

    explode_f = [0.04] * len(labels_f)

    fig, ax = plt.subplots(figsize=(5, 5))
    _, texts, autotexts = ax.pie(
        sizes_f,
        labels=labels_f,
        colors=colors_f,
        explode=explode_f,
        autopct=lambda p: f"{p:.1f}%\n({int(round(p * total / 100))} ent.)",
        startangle=140,
        pctdistance=0.72,
        textprops={"fontsize": 9}
    )

    for at in autotexts:
        at.set_fontsize(8)
        at.set_fontweight("bold")
        at.set_color("white")

    ax.set_title(
        f"{title}\n({total} entreprises)",
        fontsize=11, fontweight="bold"
    )

    return fig


#Page 1 : Prix de clôture
if page == "📈 Prix":
    st.header("Évolution des prix")

    fig, ax = plt.subplots(figsize=(10, 5))

    for v in valeurs:
        data = df_filtre[df_filtre['VALEUR'] == v]
        ax.plot(data['SEANCE'], data['CLOTURE'], label=v)

    ax.set_title("Prix de clôture")
    ax.legend()
    ax.grid(True)

    st.pyplot(fig)


#Page 2 :sur le KPI 1 on fait la performance
elif page == "📊 Performance":
    st.header("KPI 1 - Performance")

    perf_all = kpi1
    perf_moy = perf_all.mean()
    perf_med = perf_all.median()
    SEUIL_NUL = 5.0
    total = len(perf_all)

    nb_pos = (perf_all > SEUIL_NUL).sum()
    nb_quasi = ((perf_all >= 0) & (perf_all <= SEUIL_NUL)).sum()
    nb_neg = (perf_all < 0).sum()

    st.subheader("📌 Statistiques globales du marché")
    c1, c2 = st.columns(2)

    c1.metric("📈 Moyenne", f"{perf_moy:.2f} %")
    c2.metric("📊 Médiane", f"{perf_med:.2f} %")

    st.divider()

    col_bar, col_pie = st.columns([2, 1])

    with col_bar:
        st.subheader(f"Performance des entreprises sélectionnées ({annee})")

        if not valeurs:
            st.info("Sélectionnez au moins une entreprise dans la barre latérale.")
        else:
            perf_sel = kpi1[valeurs]

            colors = [
                "#2ecc71" if v > SEUIL_NUL else
                ("#f39c12" if v >= 0 else "#e74c3c")
                for v in perf_sel.values
            ]

            fig_bar, ax = plt.subplots(figsize=(10, 5))
            bars = ax.bar(perf_sel.index, perf_sel.values, color=colors)

            ax.axhline(perf_moy, linestyle="--")
            ax.axhline(perf_med, linestyle=":")

            st.pyplot(fig_bar)

    with col_pie:
        st.subheader(f"Répartition du marché ({annee})")

        fig_pie = draw_pie(
            [nb_pos, nb_quasi, nb_neg],
            ["Positives", "Quasi", "Négatives"],
            ["#2ecc71", "#f39c12", "#e74c3c"],
            "Répartition",
            total
        )

        if fig_pie:
            st.pyplot(fig_pie)
# Page 3 : Volatilité annualisée (KPI 2)
elif page == "📉 Volatilité":
    st.header("KPI 2 - Volatilité")
    vol_all = kpi2
    vol_moy = vol_all.mean()
    vol_med = vol_all.median()
    total   = len(vol_all)
    # Seuils de classification du risque : faible < 15 %, modérée 15–30 %, élevée > 30 %
    SEUIL_FAIBLE = 15.0
    SEUIL_ELEVE  = 30.0
   # Comptage des entreprises par niveau de risque
    nb_faible  = (vol_all < SEUIL_FAIBLE).sum()
    nb_moderee = ((vol_all >= SEUIL_FAIBLE) & (vol_all <= SEUIL_ELEVE)).sum()
    nb_elevee  = (vol_all > SEUIL_ELEVE).sum()
    # Indicateurs synthétiques du marché
    st.subheader("📌 Statistiques globales du marché")
    c1, c2 = st.columns(2)
    c1.metric("📉 Volatilité moyenne", f"{vol_moy:.2f} %",help="Moyenne des volatilités annualisées de toutes les entreprises")
    c2.metric("📊 Volatilité médiane", f"{vol_med:.2f} %", help="50 % des entreprises au-dessus, 50 % en-dessous de ce niveau de risque")
    st.divider()
    col_bar, col_pie = st.columns([2, 1])

    with col_bar:
        st.subheader(f"Volatilité des entreprises sélectionnées ({annee})")
        if not valeurs:
            st.info("Sélectionnez au moins une entreprise dans la barre latérale.")
        else:
            vol_sel = kpi2[valeurs]
            # Couleur selon le niveau de risque : vert = faible, orange = modéré, rouge = élevé
            colors = ["#2ecc71" if v < SEUIL_FAIBLE else ("#f39c12" if v <= SEUIL_ELEVE else "#e74c3c")for v in vol_sel.values]
            fig_bar, ax = plt.subplots(figsize=(10, 5))
            bars = ax.bar(vol_sel.index, vol_sel.values, color=colors,edgecolor="white", linewidth=0.8)
            ax.axhline(vol_moy, color="#3498db", linestyle="--", linewidth=1.8,label=f"Moyenne marché : {vol_moy:.2f} %")
            ax.axhline(vol_med, color="#9b59b6", linestyle=":", linewidth=1.8,label=f"Médiane marché : {vol_med:.2f} %")
            # Lignes horizontales matérialisant les seuils de risque
            ax.axhline(SEUIL_FAIBLE, color="#2ecc71", linestyle="-.", linewidth=1,alpha=0.6, label=f"Seuil faible : {SEUIL_FAIBLE} %")
            ax.axhline(SEUIL_ELEVE, color="#e74c3c", linestyle="-.", linewidth=1,alpha=0.6, label=f"Seuil élevé : {SEUIL_ELEVE} %")
            for bar, val in zip(bars, vol_sel.values):
                ax.text(bar.get_x() + bar.get_width() / 2,bar.get_height() + 0.3,f"{val:.1f}%", ha="center", va="bottom",fontsize=9, fontweight="bold")
            ax.set_title(f"Volatilité annualisée — {annee}", fontsize=13, fontweight="bold")
            ax.set_ylabel("Volatilité (%)")
            ax.legend(fontsize=8)
            ax.grid(axis="y", linestyle="--", alpha=0.4)
            plt.xticks(rotation=45, ha="right")
            st.pyplot(fig_bar)

    with col_pie:
        st.subheader(f"Répartition du marché ({annee})")
        fig_pie = draw_pie(
            sizes  = [nb_faible, nb_moderee, nb_elevee],
            labels = [f"Faible\n(< {SEUIL_FAIBLE}%)",f"Modérée\n({SEUIL_FAIBLE}–{SEUIL_ELEVE}%)",f"Élevée\n(> {SEUIL_ELEVE}%)"],
            colors = ["#2ecc71", "#f39c12", "#e74c3c"],
            title  = "Répartition par niveau de risque",
            total  = total)
        if fig_pie:
            st.pyplot(fig_pie)
    st.divider()

#Page 4 : Ratio de Sharpe (KPI 3)
elif page == "⚖️ Sharpe":
    st.header("KPI 3 - Sharpe Ratio")
    sharpe_all = kpi3
    sharpe_moy = sharpe_all.mean()
    sharpe_med = sharpe_all.median()
    total= len(sharpe_all)
    # Seuils : ratio < 0 = inefficient, 0–0.05 = acceptable, > 0.05 = bon rendement ajusté
    SEUIL_BON = 0.05
    nb_negatif= (sharpe_all < 0).sum()
    nb_acceptable = ((sharpe_all >= 0) & (sharpe_all <= SEUIL_BON)).sum()
    nb_bon= (sharpe_all > SEUIL_BON).sum()
    # Indicateurs synthétiques du marché
    st.subheader("📌 Statistiques globales du marché")
    c1, c2 = st.columns(2)
    c1.metric("⚖️ Sharpe moyen", f"{sharpe_moy:.4f}",help="Moyenne des ratios de Sharpe de toutes les entreprises")
    c2.metric("📊 Sharpe médian", f"{sharpe_med:.4f}",help="50 % des entreprises au-dessus, 50 % en-dessous de ce ratio")
    st.divider()
    col_bar, col_pie = st.columns([2, 1])
    with col_bar:
        st.subheader(f"Ratio de Sharpe des entreprises sélectionnées ({annee})")
        if not valeurs:
            st.info("Sélectionnez au moins une entreprise dans la barre latérale.")
        else:
            sharpe_sel = kpi3[valeurs]
            # Couleur selon l'efficience : vert = bon, orange = acceptable, rouge = négatif
            colors = ["#2ecc71" if v > SEUIL_BON else ("#f39c12" if v >= 0 else "#e74c3c") for v in sharpe_sel.values]
            fig_bar, ax = plt.subplots(figsize=(10, 5))
            bars = ax.bar(sharpe_sel.index, sharpe_sel.values, color=colors,edgecolor="white", linewidth=0.8)
            ax.axhline(sharpe_moy, color="#3498db", linestyle="--", linewidth=1.8,label=f"Moyenne marché : {sharpe_moy:.4f}")
            ax.axhline(sharpe_med, color="#9b59b6", linestyle=":", linewidth=1.8,label=f"Médiane marché : {sharpe_med:.4f}")
            ax.axhline(0, color="black", linewidth=0.8, alpha=0.5,label="Seuil zéro")
            ax.axhline(SEUIL_BON, color="#2ecc71", linestyle="-.", linewidth=1,alpha=0.6, label=f"Seuil bon rendement : {SEUIL_BON}")
            for bar, val in zip(bars, sharpe_sel.values):
                ax.text(bar.get_x() + bar.get_width() / 2,bar.get_height() + (0.001 if val >= 0 else -0.003),f"{val:.4f}", ha="center" , va="bottom"
                        if val >=0 else "top",fontsize=9, fontweight="bold")
            ax.set_title(f"Ratio de Sharpe — {annee}", fontsize=13, fontweight="bold")
            ax.set_ylabel("Ratio de Sharpe")
            ax.legend(fontsize=8)
            ax.grid(axis="y", linestyle="--", alpha=0.4)
            plt.xticks(rotation=45, ha="right")
            st.pyplot(fig_bar)

    with col_pie:
        st.subheader(f"Répartition du marché ({annee})")
        fig_pie = draw_pie(
            sizes  = [nb_bon, nb_acceptable, nb_negatif],
            labels = [f"Bon\n(> {SEUIL_BON})",f"Acceptable\n(0–{SEUIL_BON})","Inefficient\n(< 0)"],
            colors = ["#2ecc71", "#f39c12", "#e74c3c"],
            title  = "Répartition par efficience",
            total  = total )
        if fig_pie:
            st.pyplot(fig_pie)
    st.divider()
#Page 5 : Top 10 entreprises par ratio de Sharpe
elif page == "🏆 Top entreprises":
    st.header("Top entreprises")

    top = kpi3.sort_values(ascending=False).head(10)

    result = pd.DataFrame({
        "Entreprise": top.index,
        "Sharpe": top.values
    })

    st.dataframe(result)


#Page 6 : Matrice de corrélation des rendements
elif page == "🌐 Corrélation":
    st.header("Corrélation")

    pivot = df_filtre.pivot_table(
        index="SEANCE",
        columns="VALEUR",
        values="RENDEMENT_J"
    )

    corr = pivot.corr()

    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(corr, annot=True, cmap="coolwarm", ax=ax)

    st.pyplot(fig)


# Page 7 : Données brutes filtrées 
elif page == "📋 Données":
    st.header("Données filtrées")
    st.dataframe(df_filtre)