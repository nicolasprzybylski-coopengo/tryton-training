from trytond.pool import Pool

from . import library


def register():
    Pool.register(
        library.Floor,
        library.Room,
        library.Bookshelf,
        library.Exemplary,
        module='library_location', type_='model')

    # Pool.register(
    #     module='library_location', type_='wizard')
