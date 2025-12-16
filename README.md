# PDF to Calendar

[Version française](#version-française)

Automatically downloads referee game schedules from Gmail, parses them, and adds events to Apple Calendar.

## What It Does

1. Downloads the latest PDF from a specific Gmail sender
2. Extracts game information from the PDF tables
3. Groups games by location and date
4. Creates calendar events in Apple Calendar
5. Cleans up temporary files

## Requirements

- macOS (uses AppleScript for Calendar integration)
- Python 3.7+
- Gmail account with app password enabled

## Installation

1. Clone this repository

2. Install dependencies:
```bash
pip install python-dotenv imapclient pyzmail36 pdfplumber
```

3. Set up environment variables:
```bash
cp .env.example .env
```

4. Edit `.env` with your credentials:
```
EMAIL=your_email@gmail.com
APP_PASSWORD=your_gmail_app_password
SENDER=sender_email@example.com
```

### Getting a Gmail App Password

1. Go to Google Account settings
2. Security > 2-Step Verification (must be enabled)
3. App passwords > Generate new app password
4. Use this password in `.env` (not your regular Gmail password)

## Configuration

Edit `calendar_mapping` in `main.py` to map locations to calendar names:

```python
calendar_mapping = {"St-Aug": "Ref St-Aug", "Chauveau": "Ref Chauveau"}
```

The script extracts the location from parentheses in the surface field (e.g., "Surface 1 (St-Aug Int)") and uses the first word to determine which calendar to use.

## Usage

Run the script when you receive a new schedule email:

```bash
python main.py
```

The script will:
- Download PDFs from the latest email
- Parse all games
- Create events in the appropriate calendars
- Show a summary of what was processed
- Clean up downloaded files

## Output Example

```
Downloading PDFs from Gmail...
Downloaded PDF: downloads/Schedule.pdf
Downloaded 1 PDF(s).
Parsing PDF: downloads/Schedule.pdf
Found 25 games in the PDF
Parsed 25 games from PDFs.
Creating events in Apple Calendar...
Created 8 event(s) in calendar 'Ref St-Aug'
Created 3 event(s) in calendar 'Ref Chauveau'

Cleaning up temporary files...
Deleted downloads/Schedule.pdf

SUMMARY
Total games parsed: 25
Total events created: 11
Games skipped: 14

WARNING: 14 game(s) skipped due to unmapped locations:
  Locations: Other-Location
  Add these to calendar_mapping in main.py if needed.

Success! All events added to Apple Calendar.
```

## Event Format

Each event contains:
- **Title**: Number of games (e.g., "3 games")
- **Time**: From first game to last game + 50 minutes
- **Description**: Game count per surface (e.g., "Surface 1: 2 games, Surface 2: 1 game")

Events are grouped by day - one event per calendar per day containing all games for that day.

## Troubleshooting

**No PDFs downloaded**
- Check that `SENDER` email in `.env` is correct
- Verify the sender has sent emails with PDF attachments
- Check Gmail login credentials

**Games skipped**
- Add missing locations to `calendar_mapping` in `main.py`
- Check the summary output for unmapped location names

**Calendar not created**
- Ensure Apple Calendar app is installed
- Grant terminal/Python permission to control Calendar if prompted

**Datetime parsing errors**
- The PDF format may have changed
- Check that dates are in YYYY-MM-DD format and times are in HH:MM format

## File Structure

- `main.py` - Main script, orchestrates the workflow
- `download_pdf.py` - Downloads PDFs from Gmail via IMAP
- `parse_pdf.py` - Extracts game data from PDF tables
- `.env` - Environment variables (not committed to git)
- `.env.example` - Template for environment variables

---

# Version française

[English version](#pdf-to-calendar)

Télécharge automatiquement les horaires de parties d'arbitre depuis Gmail, les analyse et ajoute les événements au Calendrier Apple.

## Ce qu'il fait

1. Télécharge le dernier PDF d'un expéditeur Gmail spécifique
2. Extrait les informations des parties des tableaux PDF
3. Groupe les parties par emplacement et date
4. Crée des événements dans le Calendrier Apple
5. Nettoie les fichiers temporaires

## Prérequis

- macOS (utilise AppleScript pour l'intégration au Calendrier)
- Python 3.7+
- Compte Gmail avec mot de passe d'application activé

## Installation

1. Cloner ce dépôt

2. Installer les dépendances:
```bash
pip install python-dotenv imapclient pyzmail36 pdfplumber
```

3. Configurer les variables d'environnement:
```bash
cp .env.example .env
```

4. Modifier `.env` avec vos identifiants:
```
EMAIL=votre_email@gmail.com
APP_PASSWORD=votre_mot_de_passe_application_gmail
SENDER=email_expediteur@example.com
```

### Obtenir un mot de passe d'application Gmail

1. Aller dans les paramètres du compte Google
2. Sécurité > Validation en deux étapes (doit être activée)
3. Mots de passe des applications > Générer un nouveau mot de passe
4. Utiliser ce mot de passe dans `.env` (pas votre mot de passe Gmail régulier)

## Configuration

Modifier `calendar_mapping` dans `main.py` pour associer les emplacements aux noms de calendrier:

```python
calendar_mapping = {"St-Aug": "Ref St-Aug", "Chauveau": "Ref Chauveau"}
```

Le script extrait l'emplacement des parenthèses dans le champ surface (ex: "Surface 1 (St-Aug Int)") et utilise le premier mot pour déterminer quel calendrier utiliser.

## Utilisation

Exécuter le script lorsque vous recevez un nouvel email d'horaire:

```bash
python main.py
```

Le script va:
- Télécharger les PDFs du dernier email
- Analyser toutes les parties
- Créer des événements dans les calendriers appropriés
- Afficher un résumé de ce qui a été traité
- Nettoyer les fichiers téléchargés

## Exemple de sortie

```
Downloading PDFs from Gmail...
Downloaded PDF: downloads/Schedule.pdf
Downloaded 1 PDF(s).
Parsing PDF: downloads/Schedule.pdf
Found 25 games in the PDF
Parsed 25 games from PDFs.
Creating events in Apple Calendar...
Created 8 event(s) in calendar 'Ref St-Aug'
Created 3 event(s) in calendar 'Ref Chauveau'

Cleaning up temporary files...
Deleted downloads/Schedule.pdf

SUMMARY
Total games parsed: 25
Total events created: 11
Games skipped: 14

WARNING: 14 game(s) skipped due to unmapped locations:
  Locations: Other-Location
  Add these to calendar_mapping in main.py if needed.

Success! All events added to Apple Calendar.
```

## Format des événements

Chaque événement contient:
- **Titre**: Nombre de parties (ex: "3 games")
- **Heure**: De la première partie à la dernière partie + 50 minutes
- **Description**: Nombre de parties par surface (ex: "Surface 1: 2 games, Surface 2: 1 game")

Les événements sont groupés par jour - un événement par calendrier par jour contenant toutes les parties de cette journée.

## Dépannage

**Aucun PDF téléchargé**
- Vérifier que l'email `SENDER` dans `.env` est correct
- Vérifier que l'expéditeur a envoyé des emails avec des pièces jointes PDF
- Vérifier les identifiants de connexion Gmail

**Parties ignorées**
- Ajouter les emplacements manquants à `calendar_mapping` dans `main.py`
- Vérifier la sortie du résumé pour les noms d'emplacement non mappés

**Calendrier non créé**
- Vérifier que l'application Calendrier Apple est installée
- Accorder la permission au terminal/Python de contrôler Calendrier si demandé

**Erreurs d'analyse de date/heure**
- Le format du PDF a peut-être changé
- Vérifier que les dates sont au format AAAA-MM-JJ et les heures au format HH:MM

## Structure des fichiers

- `main.py` - Script principal, orchestre le workflow
- `download_pdf.py` - Télécharge les PDFs depuis Gmail via IMAP
- `parse_pdf.py` - Extrait les données de parties des tableaux PDF
- `.env` - Variables d'environnement (non committées dans git)
- `.env.example` - Modèle pour les variables d'environnement
