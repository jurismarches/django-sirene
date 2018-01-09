import csv
import datetime
import os
import zipfile
from urllib.parse import urljoin
from urllib.request import urlretrieve

import io
import lxml.html as lhtml
from django.core.management.base import BaseCommand

from ...importers import CSVImporter
from ...models import Institution


class Command(BaseCommand):
    help = 'Import SIREN database'
    base_url = 'http://files.data.gouv.fr/sirene/'
    local_csv_path = '/tmp'
    re_extracted_from = r'(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{0,2})'

    def add_arguments(self, parser):
        parser.add_argument('--at', action='store', type=str,
                            help='Get DB at this date (YYYY-MM-DD)')

    def _import_csv(self, data, import_headquarters, batch_size=100):
        rows = io.TextIOWrapper(data, 'iso-8859-1')
        rows = csv.DictReader(rows, delimiter=';')
        # skip header from loop
        next(rows)

        CSVImporter(
            rows,
            filename=os.path.splitext(data.name)[0],
            import_headquarters=import_headquarters,
            batch_size=batch_size,
            log=True
        ).run()

    def _download_file(self, filename, filepath):
        """Retrieve a file from filename

        :param filename: filename of file to download
        :param filepath: filepath to store downloaded file
        """
        print('Downloading {} ...'.format(filename))
        urlretrieve(urljoin(self.base_url, filename), filepath)

    def _get_filenames(self, at=datetime.date.today()):
        """Return list filenames to parse to have database at date pass as param

        :param at: Date on which we want database, default now
        """
        listing = lhtml.parse(self.base_url)
        prev_month = at.replace(day=1) - datetime.timedelta(days=1)
        last_month_filename = listing.xpath(
            '//a[contains(text(), "{}{}_L_M")]/@href'.format(
                prev_month.year,
                str(prev_month.month).zfill(2)
            )
        )[-1]

        daily_filenames = []
        range_num_day = range(
            int(at.replace(day=1).strftime('%j')),
            int(at.strftime('%j')) + 1
        )
        for i in range_num_day:
            filename = listing.xpath('//a[contains(text(), "{}{}_E_Q")]/@href'.format(
                at.year,
                str(i).zfill(3)
            ))
            if filename:
                daily_filenames.append(filename[0])

        return [last_month_filename] + daily_filenames

    def handle(self, *args, **options):

        if options.get('at'):
            at = datetime.datetime.strptime(options['at'], '%Y-%m-%d')
            filenames = self._get_filenames(at=at)
        else:
            filenames = self._get_filenames()

        files_already_parsed = set(
            list(
                Institution.objects.values_list(
                    'last_viewed_filename',
                    flat=True
                ).distinct()
            )
        )

        for filename in filenames:

            filepath = os.path.join(self.local_csv_path, filename)

            if not os.path.exists(filepath):
                self._download_file(filename, filepath)
                zfile = zipfile.ZipFile(filepath, 'r')
            else:
                print('Using already created local file {}'.format(filepath))
                try:
                    zfile = zipfile.ZipFile(filepath, 'r')
                except zipfile.BadZipfile:
                    print('Failed to open already created local file {}'.format(filepath))
                    self._download_file(filename, filepath)
                    zfile = zipfile.ZipFile(filepath, 'r')

            csv_filename = zfile.namelist()[0]
            assert os.path.splitext(csv_filename)[-1].lower() == '.csv'

            if os.path.splitext(csv_filename)[0] in files_already_parsed:
                print('Ignore file already parsed {}'.format(csv_filename))
                continue

            print('Parsing file {}'.format(csv_filename))

            # create just headquarters for now
            with zfile.open(csv_filename) as csv_file:
                self._import_csv(csv_file, import_headquarters=True)

            print('--------------------------------------------------')

            # then create subsidiaries
            with zfile.open(csv_filename) as csv_file:
                self._import_csv(csv_file, import_headquarters=False)

            zfile.close()

        # TODO: Delete old zip
