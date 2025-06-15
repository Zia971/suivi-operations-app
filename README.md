# 📊 Application de Suivi des Opérations de Construction

Cette application Streamlit permet de suivre l'avancement d'un portefeuille d'opérations de construction (chantier, VEFA, AMO, etc.) de manière intuitive et professionnelle.

## 🚀 Fonctionnalités principales

- Création et gestion d'opérations
- Vue détaillée avec journal, pièces jointes et frise des phases
- Vue manager avec indicateurs globaux et filtres avancés
- Export PDF / Word
- Base de données SQLite intégrée
- Interface responsive et claire

## 📁 Structure des fichiers

- `app_final_fully_fixed.py` : Fichier principal Streamlit
- `requirements.txt` : Dépendances nécessaires
- `operations.db` : Base SQLite créée automatiquement

## ✅ Déploiement sur Streamlit Cloud

1. Créez un dépôt GitHub et uploadez :
   - `app_final_fully_fixed.py`
   - `requirements.txt`
   - (facultatif) `README.md`

2. Allez sur [Streamlit Cloud](https://streamlit.io/cloud) et connectez votre GitHub.

3. Sélectionnez ce dépôt pour créer une nouvelle application.

4. Lancez l'application. La base `operations.db` sera générée automatiquement.

## ⚠️ Conseils

- Si vous modifiez la base de données, vous pouvez réinitialiser les tables via l’application.
- Utilisez les boutons et filtres pour naviguer efficacement entre les vues.

---

© 2025 - Suivi des Opérations de Construction