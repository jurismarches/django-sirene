import csv
import io
import logging
import os
import zipfile
from datetime import datetime
from urllib.request import urlretrieve

from django.conf import settings
from django.core.management.base import BaseCommand

from django_sirene.importers import CSVEtablissementImporter, CSVUniteLegaleImporter
from django_sirene.db_utils import toggle_postgres_vacuum

logger = logging.getLogger(__name__)


uri_stocketablissement = "http://files.data.gouv.fr/insee-sirene/%sStockEtablissement_utf8.zip"
uri_stockunitelegale = "http://files.data.gouv.fr/insee-sirene/%sStockUniteLegale_utf8.zip"

filename_stocketablissement = "etablissement.zip"
filename_stockunitelegale = "unitelegale.zip"


class Command(BaseCommand):
    help = "Import SIREN database"
    local_csv_path = getattr(settings, "DJANGO_SIRENE_LOCAL_PATH", "/tmp")

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry", action="store_true", dest="dry", help="Just show filename that will be parsed",
        )
        parser.add_argument(
            "--force",
            "-f",
            action="store_true",
            dest="force",
            help="Force download files and parse every line",
        )
        parser.add_argument(
            "--skip-StockEtablissement",
            action="store_true",
            dest="skip_stocketablissement",
            help="Do not download nor process the stock etablissement file",
        )
        parser.add_argument(
            "--offset-StockEtablissement",
            action="store",
            dest="offset_etablissement",
            help=("Ignore the first rows of the stock etablissement file"),
        )
        parser.add_argument(
            "--skip-StockUniteLegale",
            action="store_true",
            dest="skip_stockunitelegale",
            help="Do not download nor process the stock unité legale file",
        )
        parser.add_argument(
            "--offset-StockUniteLegale",
            action="store",
            dest="offset_stock",
            help=("Ignore the first rows of the stock unité legale file"),
        )
        parser.add_argument(
            "--date-from",
            action="store",
            dest="date_from",
            help=("Date from which files lines will be processed."
                  "Default to one month ago."
                  "Format 31/12/1970"),
        )
        parser.add_argument(
            "--date-file",
            action="store",
            dest="date_file",
            help=("Date to to the file to take"
                  "Format 1970-12-31"),
        )

    def _import_csv(self, data, importer_class, **options):
        rows = io.TextIOWrapper(data, "iso-8859-1")
        rows = csv.DictReader(rows, delimiter=",")

        try:
            date_from = datetime.strptime(options["date_from"], "%d/%m/%Y")
        except (TypeError, ValueError):
            date_from = None

        importer_class(
            rows,
            date_from=date_from,
            offset=options.get("offset", "0"),
            force=options.get("force"),
            log=True,
        ).run()

    def _download_file(self, uri, filepath):
        """Retrieve a file from a uri

        :param uri: uri of file to download
        :param filepath: filepath to store downloaded file
        """
        logger.debug("Downloading %s ...", uri)
        urlretrieve(uri, filepath)

    def _get_file(self, filename, uri, **options):
        filepath = os.path.join(self.local_csv_path, filename)

        if options.get("force"):
            logger.debug("Downloading data to file %s", filepath)
            self._download_file(uri, filepath)
            return zipfile.ZipFile(filepath, "r")

        try:
            zfile = zipfile.ZipFile(filepath, "r")
            logger.debug("Using known file %s", filepath)
            return zfile
        except (zipfile.BadZipFile, FileNotFoundError):
            logger.debug("Failed to open local file %s", filepath)
            logger.debug("Downloading data to file %s", filepath)
            self._download_file(uri, filepath)
            return zipfile.ZipFile(filepath, "r")

    def populate_with_file(self, filename, uri, importer_class, offset="0", **options):
        if options["dry"]:
            print("%s in %s" % (uri, filename))
            return

        zfile = self._get_file(filename, uri, **options)
        csv_filename = zfile.namelist()[0]
        assert os.path.splitext(csv_filename)[-1].lower() == ".csv"

        try:
            offset = int(offset)
        except (TypeError, ValueError):
            logger.warning("offset %s ignored", offset)
            offset = 0
        options["offset"] = offset

        with zfile.open(csv_filename) as csv_file:
            self._import_csv(csv_file, importer_class, **options)
        zfile.close()

        logger.info("%s imported", csv_filename)

    def _handle(self, *args, **options):
        if options.get("date_file"):
            date_file = options.get("date_file") + "-"
        else:
            date_file = ""

        uri_stocketablissement_dated = uri_stocketablissement % date_file
        uri_stockunitelegale_dated = uri_stockunitelegale % date_file

        if not options["skip_stocketablissement"]:
            self.populate_with_file(
                filename_stocketablissement,
                uri_stocketablissement_dated,
                CSVEtablissementImporter,
                offset=options.get("offset_etablissement") or 0,
                **options,
            )

        if not options["skip_stockunitelegale"]:
            self.populate_with_file(
                filename_stockunitelegale,
                uri_stockunitelegale_dated,
                CSVUniteLegaleImporter,
                offset=options.get("offset_stock") or 0,
                **options,
            )

    def handle(self, *args, **options):
        try:
            toggle_postgres_vacuum(autovacuum_enabled=False)
            self._handle(*args, **options)
        except Exception:
            raise
        finally:
            toggle_postgres_vacuum(autovacuum_enabled=True)
