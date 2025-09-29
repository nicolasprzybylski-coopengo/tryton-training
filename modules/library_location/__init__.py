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
        wizard.TakeOutFromBookshelfParameters,
        module='library_location', type_='model')

    Pool.register(
        wizard.PutInBookshelf,
        wizard.TakeOutFromBookshelf,
        module='library_location', type_='wizard')
