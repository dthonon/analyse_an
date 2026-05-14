"""Script principal de l'application."""

import io
import logging
import logging.handlers
import sys
from pathlib import Path

import pandas as pd
import requests

# Configuration du logging
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_FILE = LOG_DIR / "analyse_an.log"


def configure_logging() -> None:
    """
    Configure le système de logging.

    Crée un logger avec :
    - Un fichier de log rotatif
    - Un affichage en console
    - Un format standardisé avec timestamp, niveau et message
    """
    LOG_DIR.mkdir(exist_ok=True)

    # Créer le logger racine
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # Format commun
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Handler pour fichier rotatif
    file_handler = logging.handlers.RotatingFileHandler(
        filename=LOG_FILE,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,  # 10 MB
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Handler pour console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)


def read_csv_from_http(url: str) -> pd.DataFrame:
    """
    Télécharge et lit un fichier CSV depuis une URL HTTP.

    Args:
        url: L'URL HTTP du fichier CSV

    Returns:
        Un DataFrame pandas contenant les données du CSV

    Raises:
        requests.RequestException: En cas d'erreur lors du téléchargement
        pd.errors.ParserError: En cas d'erreur lors du parsing du CSV
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Téléchargement du fichier CSV depuis: {url}")

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        logger.debug(f"Réponse HTTP: {response.status_code}")
        # Lire le CSV depuis le contenu téléchargé
        csv_content = io.StringIO(response.content.decode("utf-8"))
        df = pd.read_csv(csv_content)
        logger.info(f"CSV chargé avec succès: {len(df)} lignes, {len(df.columns)} colonnes")
        logger.debug(f"Colonnes: {list(df.columns)}")

        return df

    except requests.RequestException as e:
        logger.error(f"Erreur lors du téléchargement: {e}")
        raise
    except pd.errors.ParserError as e:
        logger.error(f"Erreur lors du parsing du CSV: {e}")
        raise


def main() -> None:
    """
    Point d'entrée principal de l'application.

    Initialise le journal, enregistre le démarrage de l'application,
    l'étape courante, et le chemin à partir duquel les variables
    d'environnement sont chargées.
    """
    configure_logging()
    logger = logging.getLogger(__name__)

    logger.info("Démarrage de l'application analyse_an")
    logger.debug(f"Fichier de log: {LOG_FILE}")

    # Lecture de la liste des amendements depuis une URL HTTP
    csv_url = "https://data.assemblee-nationale.fr/static/openData/repository/17/dossiers_legislatifs_opendata/54085/libre_office.csv"
    try:
        df_amendements = read_csv_from_http(csv_url)
        logger.info("Amendements chargés et prêts à être analysés.")
    except Exception as e:
        logger.error(f"Erreur lors du chargement des amendements: {e}")
        raise

    print(df_amendements.head())


if __name__ == "__main__":
    main()
