"""Script principal de l'application."""

import io
import logging
import logging.handlers
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path

import click
import pandas as pd
import requests
from bs4 import BeautifulSoup

# Configuration du logging
LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_FILE = LOG_DIR / "analyse_an.log"
CSV_DIR = Path(__file__).parent.parent.parent / "data" / "csv"
XML_DIR = Path(__file__).parent.parent.parent / "data" / "xml"
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
        logger.info(f"CSV chargé avec succès: {len(df)} lignes, {len(df.columns)} colonnes")
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
        if target_path.exists():
            logger.info(f"Fichier déjà existant, saut du téléchargement: {target_path}")
            xml_paths.append(target_path)
            continue
        else:
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


@click.group()
def main() -> None:
    """Application d'analyse des amendements de l'Assemblée Nationale."""
    pass
    return None


@main.command(
    name="download-xml",
    help="Télécharge les fichiers XML listés dans le CSV des amendements.",
)
@click.option(
    "--csv-url",
    default="https://data.assemblee-nationale.fr/static/openData/repository/17/dossiers_legislatifs_opendata/54085/libre_office.csv",
    show_default=True,
    help="URL du fichier CSV des amendements.",
)
@click.option(
    "--csv-dir",
    type=click.Path(path_type=Path, file_okay=False, resolve_path=True),
    default=CSV_DIR,
    show_default=True,
    help="Répertoire contenant le fichier CSV des amendements.",
)
@click.option(
    "--xml-dir",
    type=click.Path(path_type=Path, file_okay=False, resolve_path=True),
    default=XML_DIR,
    show_default=True,
    help="Répertoire de destination pour les fichiers XML téléchargés.",
)
def download_xml(
    csv_url: str,
    csv_dir: Path,
    xml_dir: Path,
) -> None:
    """Télécharge les fichiers XML listés dans le CSV fourni."""

    configure_logging()
    logger = logging.getLogger(__name__)

    logger.info("Démarrage de l'application analyse_an")
    logger.debug(f"Fichier de log: {LOG_FILE}")

    try:
        df_amendements = read_csv_from_http(csv_url)
        logger.info("Amendements chargés et prêts à être analysés.")
    except Exception as e:
        logger.error(f"Erreur lors du chargement des amendements: {e}")
        raise

    df_amendements = filter_amendements_by_designation(df_amendements)
    logger.info(f"Amendements filtrés par 'Désignation de l'article' : {len(df_amendements)} lignes restantes.")

    # Supprimer la colonne 'URL Dossier législatif' si elle existe
    if "URL Dossier législatif" in df_amendements.columns:
        df_amendements = df_amendements.drop(
            columns=[
                "Titre court",
                "Titre complet",
                "URL Dossier législatif",
                "URL Texte référence",
            ]
        )
        logger.debug("Colonnes supprimées du DataFrame")
    if csv_dir:
        csv_dir.mkdir(parents=True, exist_ok=True)
        csv_file = csv_dir / "amendements_filtrés.csv"
        df_amendements.to_csv(csv_file, index=False, encoding="utf-8")
        logger.info(f"Amendements filtrés sauvegardés dans {csv_file}")

    xml_paths = download_xml_amendements(df_amendements, xml_dir)
    logger.info(f"Téléchargement terminé: {len(xml_paths)} fichiers XML enregistrés dans {xml_dir}")


@main.command(
    name="analyse-xml",
    help="Analyse des fichiers XML pour extraire les informations.",
)
@click.option(
    "--xml-dir",
    type=click.Path(path_type=Path, file_okay=False, resolve_path=True),
    default=XML_DIR,
    show_default=True,
    help="Répertoire contenant les fichiers XML à analyser.",
)
@click.option(
    "--csv-dir",
    type=click.Path(path_type=Path, file_okay=False, resolve_path=True),
    default=CSV_DIR,
    show_default=True,
    help="Répertoire contenant le fichier CSV des amendements.",
)
def analyse_xml(xml_dir: Path, csv_dir: Path | None) -> None:
    """Recherche des textes dans les fichiers XML."""

    configure_logging()
    logger = logging.getLogger(__name__)

    xml_dir = Path(xml_dir)
    logger.info(f"Démarrage de l'analyse XML dans {xml_dir}")

    if not xml_dir.exists() or not xml_dir.is_dir():
        logger.error(f"Le répertoire {xml_dir} n'existe pas ou n'est pas un dossier")
        raise click.Abort()

    files = sorted(xml_dir.glob("*.xml"))
    if not files:
        logger.warning(f"Aucun fichier XML trouvé dans {xml_dir}")
        return None

    amend = pd.DataFrame(columns=["Numéro de l'amendement", "Sort", "Dispositif", "Exposé sommaire"])
    for f in files:
        try:
            num = None
            sort_amend = None
            disp = None
            expo = None
            tree = ET.parse(f)
            for c in list(tree.getroot().iter()):
                if c.tag == "{http://schemas.assemblee-nationale.fr/referentiel}numeroLong":
                    num = BeautifulSoup(str(c.text), "html.parser").get_text()
                    logger.debug(f"Tag 'numeroLong' : {num}")
                if c.tag == "{http://schemas.assemblee-nationale.fr/referentiel}sort":
                    sort_amend = BeautifulSoup(str(c.text), "html.parser").get_text()
                    logger.debug(f"Tag 'sort' : {sort_amend}")
                if c.tag == "{http://schemas.assemblee-nationale.fr/referentiel}dispositif":
                    disp = BeautifulSoup(str(c.text), "html.parser").get_text()
                    logger.debug(f"Tag 'dispositif' : {disp}")
                if c.tag == "{http://schemas.assemblee-nationale.fr/referentiel}exposeSommaire":
                    expo = BeautifulSoup(str(c.text), "html.parser").get_text()
                    logger.debug(f"Tag 'exposeSommaire' : {expo}")
                sort_amend = "Irrecevable" if (sort_amend == "None" and disp is None) else sort_amend
                sort_amend = "Non renseigné" if (sort_amend == "None") else sort_amend
            amend = pd.concat(
                [
                    amend,
                    pd.DataFrame(
                        [
                            {
                                "Numéro de l'amendement": num,
                                "Sort": sort_amend,
                                "Dispositif": disp,
                                "Exposé sommaire": expo,
                            }
                        ]
                    ),
                ],
                ignore_index=True,
            )
        except ET.ParseError as e:
            logger.error(f"Erreur de parsing pour {f}: {e}")

    if csv_dir:
        csv_dir.mkdir(parents=True, exist_ok=True)
        csv_file = csv_dir / "amendements_filtrés.csv"
        amend1 = pd.read_csv(csv_file) if csv_file.exists() else pd.DataFrame()
        logger.info(f"Amendements chargés : {amend1.shape[0]} lignes, {amend1.shape[1]} colonnes")
        logger.info(f"Amendements complets : {amend.shape[0]} lignes, {amend.shape[1]} colonnes")
        amend2 = amend1.merge(amend, how="inner", on="Numéro de l'amendement")
        logger.info(f"Amendements fusionnés : {amend2.shape[0]} lignes, {amend2.shape[1]} colonnes")
        csv_file = csv_dir / "amendements_complétés.csv"
        amend2.to_csv(csv_file, index=False, encoding="utf-8")
        logger.info(f"Amendements extraits sauvegardés dans {csv_file}")
    else:
        logger.info("Aucun chemin de sauvegarde CSV fourni, résultats non sauvegardés.")

    return None


def print_sort_summary(df: pd.DataFrame) -> None:
    """Affiche un résumé par valeur de la colonne 'Sort'."""
    logger = logging.getLogger(__name__)
    if "Sort" not in df.columns:
        logger.warning("Aucune colonne 'Sort' dans le DataFrame, résumé non affiché.")
        return

    summary = df["Sort"].fillna("Non renseigné").astype(str).value_counts(dropna=False)

    click.echo("Résumé par 'Sort':")
    for sort_value, count in summary.items():
        click.echo(f"  {sort_value}: {count}")


@main.command(
    name="sort-csv",
    help="Lit et classe le fichier CSV des amendements filtrés par dispositif.",
)
@click.option(
    "--csv-file",
    type=click.Path(path_type=Path, exists=True, resolve_path=True),
    default=CSV_DIR / "amendements_complétés.csv",
    show_default=True,
    help="Chemin du fichier CSV à lire.",
)
@click.option(
    "--rows",
    type=int,
    default=10,
    show_default=True,
    help="Nombre de lignes à afficher (0 pour toutes).",
)
def sort_csv(csv_file: Path, rows: int) -> None:
    """Lit et affiche les amendements depuis un fichier CSV."""

    configure_logging()
    logger = logging.getLogger(__name__)

    csv_file = Path(csv_file)
    logger.info(f"Lecture du fichier CSV: {csv_file}")

    if not csv_file.exists():
        logger.error(f"Le fichier {csv_file} n'existe pas")
        raise click.FileError(str(csv_file), hint="Fichier non trouvé")

    try:
        df = pd.read_csv(csv_file, encoding="utf-8")
        logger.info(f"Fichier chargé: {len(df)} lignes, {len(df.columns)} colonnes")

        if "Dispositif" not in df.columns:
            logger.error("La colonne 'Dispositif' est introuvable dans le CSV")
            raise click.Abort()

        def normalize(value: str) -> str:
            if pd.isna(value):
                return ""
            text = str(value).strip().lower()
            text = unicodedata.normalize("NFKD", text)
            text = "".join(ch for ch in text if not unicodedata.combining(ch))
            text = re.sub(r"[^a-z0-9\s]", "", text)
            return re.sub(r"\s+", " ", text).strip()

        df["_dispositif_key"] = df["Dispositif"].apply(normalize)
        df = df.sort_values(by=["_dispositif_key", "Dispositif"])
        df = df.drop(columns=["_dispositif_key"])
        logger.info("Amendements triés par dispositif similaire.")

        print_sort_summary(df)

        sorted_file = csv_file.parent / "amendements_triés.csv"
        df.to_csv(sorted_file, index=False, encoding="utf-8")
        logger.info(f"Amendements triés sauvegardés dans {sorted_file}")

    except Exception as e:
        logger.error(f"Erreur lors de la lecture du fichier CSV: {e}")
        raise


if __name__ == "__main__":
    main()
