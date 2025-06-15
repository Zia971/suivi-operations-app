import streamlit as st
import plotly.express as px
import pandas as pd
import json
from datetime import datetime
import os
import base64
from io import BytesIO

# Constantes requises pour l'application
TYPES_OPERATION = ["OPP", "VEFA", "AMO", "Mandat"]
PHASES = [
    "Phase de montage",
    "Programmation",
    "Foncier",
    "Études",
    "DCE",
    "Chantier",
    "Livraison",
    "Clôture"
]
STATUSES = {
    "à_vendre": "🟡 À vendre",
    "en_cours": "🟢 En cours",
    "bloque": "🔴 Bloqué",
    "cloture": "✅ Clôturé"
}

class OperationConstruction:
    def __init__(self):
        self.operations = {}
        self.fichier_donnees = "operations.json"
        self.charger_donnees()

    def charger_donnees(self):
        if os.path.exists(self.fichier_donnees):
            try:
                with open(self.fichier_donnees, 'r', encoding='utf-8') as f:
                    self.operations = json.load(f)
            except json.JSONDecodeError:
                self.operations = {}
        else:
            self.operations = {}

    def sauvegarder_donnees(self):
        with open(self.fichier_donnees, 'w', encoding='utf-8') as f:
            json.dump(self.operations, f, ensure_ascii=False, indent=2)

    def ajouter_operation(self, nom, type_op, charge, phases):
        id_op = len(self.operations) + 1
        self.operations[id_op] = {
            "nom": nom,
            "type": type_op,
            "charge": charge,
            "statut": "à_vendre",
            "phases": {phase: False for phase in PHASES},
            "dates": {phase: None for phase in PHASES},
            "journal": [],
            "avancement": 0,
            "pieces_jointes": []
        }
        self.sauvegarder_donnees()
        return id_op

    def ajouter_journal(self, id_op, entree):
        if id_op in self.operations:
            operation = self.operations[id_op]
            operation["journal"].append({
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "entree": entree
            })
            self.sauvegarder_donnees()

    def mettre_a_jour_phase(self, id_op, phase, terminee):
        if id_op in self.operations:
            operation = self.operations[id_op]
            operation["phases"][phase] = terminee
            operation["avancement"] = int(sum(operation["phases"].values()) / len(PHASES) * 100)
            self.sauvegarder_donnees()

def creer_gantt(id_op, operation):
    df = pd.DataFrame([
        dict(
            Task=phase,
            Start=operation["dates"][phase] or datetime.min,
            Finish=operation["dates"][phase] or datetime.max,
            Resource=operation["charge"]
        )
        for phase in PHASES
    ])

    fig = px.timeline(df, x_start="Start", x_end="Finish", y="Task", color="Resource")
    fig.update_layout(
        title=f"Gantt - {operation['nom']}",
        xaxis_title="Dates",
        yaxis_title="Phases"
    )
    return fig

def main():
    gestionnaire = OperationConstruction()

    st.set_page_config(
        page_title="Suivi Opérations Construction",
        page_icon="🏗️",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    with st.sidebar:
        st.header("Filtres")
        type_filtre = st.selectbox("Type d'opération", ["Tous"] + TYPES_OPERATION)
        statut_filtre = st.selectbox("Statut", ["Tous"] + list(STATUSES.values()))
        charge_filtre = st.selectbox("Chargé d'opération", ["Tous"])

    tab_accueil, tab_operations, tab_detail = st.tabs(["Accueil", "Opérations", "Détail"])

    with tab_accueil:
        st.header("Tableau de bord")

        col1, col2, col3 = st.columns(3)
        with col1:
            operations_totales = len(gestionnaire.operations)
            st.metric("Opérations totales", operations_totales)

        with col2:
            avancement_moyen = sum(op["avancement"] for op in gestionnaire.operations.values()) / operations_totales if operations_totales > 0 else 0
            st.metric("Avancement moyen", f"{avancement_moyen:.1f}%")

        with col3:
            operations_en_cours = sum(1 for op in gestionnaire.operations.values() if op["statut"] == "en_cours")
            st.metric("En cours", operations_en_cours)

        st.header("Vue d'ensemble des opérations")
        cols = st.columns([2, 2, 2, 2, 2, 2])
        for i, op in gestionnaire.operations.items():
            with cols[i % 6]:
                st.markdown(f"### {op['nom']}")
                st.write(f"• Type: {op['type']}  
• Statut: {STATUSES[op['statut']]}  
• Avancement: {op['avancement']}%")

    with tab_operations:
        st.header("Gestion des opérations")
        with st.form("ajout_operation"):
            st.header("Nouvelle opération")
            nom = st.text_input("Nom de l'opération")
            type_op = st.selectbox("Type", TYPES_OPERATION)
            charge = st.text_input("Chargé d'opération")

            if st.form_submit_button("Créer"):
                gestionnaire.ajouter_operation(nom, type_op, charge, PHASES)
                st.success("Opération créée avec succès !")

    with tab_detail:
        st.header("Détails de l'opération")
        id_op = st.number_input("ID de l'opération", min_value=1, value=1)

        if id_op in gestionnaire.operations:
            operation = gestionnaire.operations[id_op]
            st.header(operation["nom"])
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"Type: {operation['type']}")
                st.write(f"Chargé: {operation['charge']}")
            with col2:
                st.write(f"Statut: {STATUSES[operation['statut']]}")
                st.write(f"Avancement: {operation['avancement']}%")

            st.header("Planning")
            fig = creer_gantt(id_op, operation)
            st.plotly_chart(fig, use_container_width=True)

            st.header("Journal")
            for entree in reversed(operation["journal"][:10]):
                st.write(f"[{entree['date']}] {entree['entree']}")

            with st.form("nouveau_journal"):
                entree = st.text_area("Nouvelle entrée journal")
                if st.form_submit_button("Ajouter à la journal"):
                    gestionnaire.ajouter_journal(id_op, entree)
                    st.success("Entrée ajoutée au journal")

if __name__ == "__main__":
    main()
