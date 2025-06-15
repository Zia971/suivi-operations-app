
import streamlit as st
import sqlite3
import json
import plotly.express as px
from datetime import datetime
import pandas as pd
from typing import List, Dict
import os
import base64
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

# Configuration initiale
st.set_page_config(page_title="Suivi Opérations Construction", layout="wide")

# Connexion à la base de données
@st.cache_data(ttl=600)
def get_connection():
    return sqlite3.connect('construction.db')

# Création des tables si elles n'existent pas
def init_database():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Table des opérations
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS operations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            type_operation TEXT NOT NULL,
            responsable TEXT NOT NULL,
            statut TEXT DEFAULT 'À l\'étude',
            date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            avancement REAL DEFAULT 0
        )
    ''')
    
    # Table des phases
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS phases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operation_id INTEGER,
            phase TEXT NOT NULL,
            date_debut DATE,
            date_fin DATE,
            terminee BOOLEAN DEFAULT 0,
            FOREIGN KEY (operation_id) REFERENCES operations(id)
        )
    ''')
    
    # Table du journal
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operation_id INTEGER,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            evenement TEXT NOT NULL,
            utilisateur TEXT NOT NULL,
            FOREIGN KEY (operation_id) REFERENCES operations(id)
        )
    ''')
    
    # Table des pièces jointes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pieces_jointes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operation_id INTEGER,
            nom TEXT NOT NULL,
            contenu BLOB NOT NULL,
            date_ajout TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (operation_id) REFERENCES operations(id)
        )
    ''')
    
    conn.commit()

# Liste des phases possibles
PHASES = [
    'Phase de montage',
    'Programmation',
    'Foncier',
    'Études',
    'DCE',
    'Attribution de marché',
    'Chantier',
    'Livraison',
    'Clôture technique',
    'Clôture financière'
]

# Liste des statuts possibles
STATUTS = [
    '🟡 À l\'étude',
    '🟢 En cours',
    '🔴 Bloqué',
    '✅ Clôturé'
]

def ajouter_operation():
    with st.form("nouvelle_operation"):
        st.header("Nouvelle Opération")
        nom = st.text_input("Nom de l'opération")
        type_op = st.selectbox("Type d'opération", ["OPP", "VEFA", "AMO", "Mandat"])
        responsable = st.text_input("Responsable")
        
        if st.form_submit_button("Enregistrer"):
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO operations (nom, type_operation, responsable)
                VALUES (?, ?, ?)
            """, (nom, type_op, responsable))
            
            operation_id = cursor.lastrowid
            
            for phase in PHASES:
                cursor.execute("""
                    INSERT INTO phases (operation_id, phase)
                    VALUES (?, ?)
                """, (operation_id, phase))
            
            cursor.execute("""
                INSERT INTO journal (operation_id, evenement, utilisateur)
                VALUES (?, ?, ?)
            """, (operation_id, f"Création de l'opération {nom}", st.session_state.utilisateur))
            
            conn.commit()
            st.success("Opération créée avec succès!")

def afficher_tableau_bord():
    col1, col2, col3 = st.columns(3)
    
    with col1:
        conn = get_connection()
        total_ops = pd.read_sql_query(
            "SELECT COUNT(*) FROM operations",
            conn
        ).iloc[0,0]
        st.metric("Total Opérations", total_ops)
    
    with col2:
        active_ops = pd.read_sql_query("""
            SELECT COUNT(*) FROM operations 
            WHERE statut != '✅ Clôturé'
        """, conn).iloc[0,0]
        st.metric("Opérations Actives", active_ops)
    
    with col3:
        avg_avancement = pd.read_sql_query("""
            SELECT AVG(avancement) * 100 FROM operations
        """, conn).iloc[0,0]
        st.metric("Avancement Moyen (%)", f"{avg_avancement:.1f}")
    
    # Graphique des statuts
    df_statuts = pd.read_sql_query("""
        SELECT statut, COUNT(*) as count 
        FROM operations 
        GROUP BY statut
    """, conn)
    
    fig = px.pie(df_statuts, values='count', names='statut')
    st.plotly_chart(fig, use_container_width=True)

def afficher_detail_operation(operation_id):
    conn = get_connection()
    cursor = conn.cursor()
    
    op_data = pd.read_sql_query("""
        SELECT * FROM operations WHERE id = ?
    """, conn, params=(operation_id,)).iloc[0]
    
    # Affichage des informations générales
    col1, col2 = st.columns([2, 1])
    with col1:
        st.title(op_data['nom'])
    with col2:
        st.write(f"Type: {op_data['type_operation']}")
        st.write(f"Responsable: {op_data['responsable']}")
        st.write(f"Statut: {op_data['statut']}")
        st.write(f"Avancement: {op_data['avancement']*100:.1f}%")
    
    # Journal des actions
    st.subheader("Journal des Actions")
    df_journal = pd.read_sql_query("""
        SELECT date, evenement, utilisateur 
        FROM journal 
        WHERE operation_id = ?
        ORDER BY date DESC
        LIMIT 10
    """, conn, params=(operation_id,))
    
    if not df_journal.empty:
        st.dataframe(df_journal)
    
    # Ajout d'une nouvelle entrée de journal
    with st.form("nouveau_journal"):
        evenement = st.text_area("Nouvelle entrée")
        if st.form_submit_button("Ajouter à l'historique"):
            cursor.execute("""
                INSERT INTO journal (operation_id, evenement, utilisateur)
                VALUES (?, ?, ?)
            """, (operation_id, evenement, st.session_state.utilisateur))
            conn.commit()
            st.success("Entrée ajoutée au journal")
    
    # Gantt des phases
    phases_df = pd.read_sql_query("""
        SELECT phase, date_debut, date_fin, terminee 
        FROM phases 
        WHERE operation_id = ?
        ORDER BY CASE phase
            WHEN 'Phase de montage' THEN 1
            WHEN 'Programmation' THEN 2
            WHEN 'Foncier' THEN 3
            WHEN 'Études' THEN 4
            WHEN 'DCE' THEN 5
            WHEN 'Attribution de marché' THEN 6
            WHEN 'Chantier' THEN 7
            WHEN 'Livraison' THEN 8
            WHEN 'Clôture technique' THEN 9
            WHEN 'Clôture financière' THEN 10
        END
    """, conn, params=(operation_id,))
    
    fig = px.timeline.Gantt(phases_df, x_start="date_debut", x_end="date_fin", 
                           y="phase", title="Planning des Phases")
    st.plotly_chart(fig, use_container_width=True)

def vue_manager():
    st.header("Vue Manager")
    
    # KPIs globaux
    col1, col2, col3 = st.columns(3)
    with col1:
        total_ops = pd.read_sql_query(
            "SELECT COUNT(*) FROM operations",
            get_connection()
        ).iloc[0,0]
        st.metric("Total Opérations", total_ops)
    
    with col2:
        active_ops = pd.read_sql_query("""
            SELECT COUNT(*) FROM operations 
            WHERE statut != '✅ Clôturé'
        """, get_connection()).iloc[0,0]
        st.metric("Opérations Actives", active_ops)
    
    with col3:
        avg_avancement = pd.read_sql_query("""
            SELECT AVG(avancement) * 100 FROM operations
        """, get_connection()).iloc[0,0]
        st.metric("Avancement Moyen (%)", f"{avg_avancement:.1f}")
    
    # Filtres
    col1, col2, col3 = st.columns(3)
    with col1:
        type_filter = st.selectbox("Type d'opération", ["Tous"] + ["OPP", "VEFA", "AMO", "Mandat"])
    with col2:
        statut_filter = st.selectbox("Statut", ["Tous"] + STATUTS)
    with col3:
        responsable_filter = st.text_input("Responsable")
    
    # Liste des opérations filtrées
    df = pd.read_sql_query("""
        SELECT * FROM operations 
        WHERE (? = 'Tous' OR type_operation = ?)
        AND (? = 'Tous' OR statut = ?)
        AND (? = '' OR responsable LIKE ?)
        ORDER BY date_creation DESC
    """, get_connection(), params=(
        type_filter, type_filter,
        statut_filter, statut_filter,
        f"%{responsable_filter}%"
    ))
    
    for _, row in df.iterrows():
        with st.expander(row['nom']):
            afficher_detail_operation(row['id'])

def main():
    init_database()
    
    # Initialisation de l'utilisateur
    if 'utilisateur' not in st.session_state:
        st.session_state.utilisateur = st.sidebar.text_input("Nom de l'utilisateur")
    
    # Barre de navigation
    tabs = st.tabs(["Tableau de Bord", "Gestion des Opérations", "Vue Manager"])
    
    with tabs[0]:
        afficher_tableau_bord()
        
    with tabs[1]:
        ajouter_operation()
        
    with tabs[2]:
        vue_manager()

if __name__ == "__main__":
    main()