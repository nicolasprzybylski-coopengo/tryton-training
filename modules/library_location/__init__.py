from trytond.pool import Pool

from . import library
from . import wizard


def register():
    Pool.register(
        library.Floor,
        library.Room,
        library.Bookshelf,
        library.Exemplary,
        library.QuarantineZone,
        library.Book,
        library.Checkout,
        wizard.PutInBookshelfParameters,
        wizard.PutInStorageParameters,
        wizard.CreateExemplariesParameters,
        wizard.ReserveSelectBooks,
        module='library_location', type_='model')

    Pool.register(
        wizard.PutInBookshelf,
        wizard.PutInStorage,
        wizard.Reserve,
        wizard.CreateExemplaries,
        wizard.Borrow,
        wizard.Return,
        module='library_location', type_='wizard')
