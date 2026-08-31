import logging

from django.contrib.staticfiles.storage import StaticFilesStorage
from whitenoise.storage import CompressedManifestStaticFilesStorage

logger = logging.getLogger(__name__)


class ResilientStaticFilesStorage(CompressedManifestStaticFilesStorage):
    """Serve a missing static file as a broken asset, not a broken page.

    The manifest storage raises ValueError when a template asks for a file
    that collectstatic never saw. Django turns that into a 500, so one logo
    forgotten during install takes down the whole login page and the operator
    sees only "Server Error (500)" with nothing pointing at the cause.

    Here the failure is logged and the tag falls back to the plain, unhashed
    path: the browser gets a 404 for that one file, the page still renders,
    and the gap is visible on screen instead of fatal. Hashing, compression
    and far-future caching are untouched for every file that was collected.
    """

    def url(self, name, force=False):
        try:
            return super().url(name, force=force)
        except ValueError:
            logger.warning(
                'Static file %r is not in the manifest. Serving its unhashed '
                'path; run "manage.py collectstatic" after adding the file.',
                name,
            )
            return StaticFilesStorage.url(self, name)