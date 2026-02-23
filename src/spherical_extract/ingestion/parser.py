import logging

logger = logging.getLogger(__name__)

def parse_tables_from_pdf(filepath: str, pages: str = "all"):
    """
    Extracts tables using Camelot, utilizing local layout parsing without LLMs.
    Focuses parsing specifically to the pages indicated to contain tables.
    """
    try:
        import camelot
        # flavor 'lattice' is generally best for strict table borders,
        # 'stream' is used for whitespace-separated columns.
        tables = camelot.read_pdf(filepath, pages=pages, flavor='lattice') # type: ignore
        logger.info(f"Camelot extracted {tables.n} tables from {filepath} on pages {pages}")
        return tables
    except ImportError:
        logger.error("camelot-py is not installed properly. Ensure cv2 and ghostscript are available.")
        return []
    except Exception as e:
        logger.error(f"Camelot parsing failed for {filepath}: {e}")
        return []
