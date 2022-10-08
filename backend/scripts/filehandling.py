import logging

import click
from flask.cli import AppGroup

from dataparser.image import create_s3_url


logger = logging.getLogger(__name__)


product_cli = AppGroup('file')


@product_cli.command('upload')
@click.argument('fileloc', required=False)
def upload_file_s3(fileloc):
    extension = fileloc.split('.')[-1].lower()
    create_s3_url()
    