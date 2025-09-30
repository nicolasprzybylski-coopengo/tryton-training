from trytond.pool import Pool

from . import library
from . import wizard


def register():
    Pool.register(
        library.Floor,
        library.Room,
        library.Bookshelf,
        library.Exemplary,
        wizard.PutInBookshelfParameters,
        wizard.PutInStorageParameters,
        module='library_location', type_='model')

    Pool.register(
        wizard.PutInBookshelf,
        wizard.PutInStorage,
        module='library_location', type_='wizard')
