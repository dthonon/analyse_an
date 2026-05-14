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
XML_DIR = Path(__file__).parent.parent / "data" / "xml"
XML_URL_COLUMN = "URL Amendement format XML"


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
        logger.info(
            f"CSV chargé avec succès: {len(df)} lignes, {len(df.columns)} colonnes"
        )
        logger.debug(f"Colonnes: {list(df.columns)}")

        return df

    except requests.RequestException as e:
        logger.error(f"Erreur lors du téléchargement: {e}")
        raise
    except pd.errors.ParserError as e:
        logger.error(f"Erreur lors du parsing du CSV: {e}")
        raise


def filter_amendements_by_designation(df: pd.DataFrame) -> pd.DataFrame:
    """Filtre les amendements relatifs à l'article 14 en vérifiant la colonne 'Désignation de l'article'."""
    return df[
        (df["Désignation de l'article"] == "Article 14")
        | (df["Désignation de l'article"] == "Avant l'article 14")
        | (df["Désignation de l'article"] == "Après l'article 14")
    ].copy()


def download_xml_amendements(df: pd.DataFrame, dest_dir: Path) -> list[Path]:
    """Télécharge les fichiers XML listés dans la colonne URL Amendement format XML."""
    logger = logging.getLogger(__name__)
    dest_dir.mkdir(parents=True, exist_ok=True)

    xml_paths: list[Path] = []
    for idx, url in df[XML_URL_COLUMN].dropna().items():
        if not isinstance(url, str) or not url.strip():
            continue

        filename = Path(url).name
        filename = f"{idx:04d}_{filename}" if filename else f"amendement_{idx}.xml"
        target_path = dest_dir / filename

        logger.debug(f"Téléchargement XML {idx} depuis {url}")
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            target_path.write_bytes(response.content)
            xml_paths.append(target_path)
            logger.info(f"Enregistré {target_path}")
        except requests.RequestException as e:
            logger.error(f"Erreur lors du téléchargement du XML {url}: {e}")

    return xml_paths


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

    df_amendements = filter_amendements_by_designation(df_amendements)
    logger.info(
        f"Amendements filtrés par 'Désignation de l'article' : {len(df_amendements)} lignes restantes."
    )
    print(df_amendements[["Désignation de l'article", XML_URL_COLUMN]].head())

    xml_paths = download_xml_amendements(df_amendements, XML_DIR)
    logger.info(
        f"Téléchargement terminé: {len(xml_paths)} fichiers XML enregistrés dans {XML_DIR}"
    )


if __name__ == "__main__":
    main()
