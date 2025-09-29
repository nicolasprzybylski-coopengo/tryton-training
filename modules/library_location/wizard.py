import datetime

from trytond.pool import Pool
from trytond.pyson import Eval, PYSONEncoder
from trytond.transaction import Transaction
from trytond.model import ModelView, fields
from trytond.wizard import Wizard, StateView, StateTransition, StateAction
from trytond.wizard import Button

__all__ = [
    'PutInBookshelf',
    'PutInBookshelfParameters',
    'TakeOutFromBookshelf',
    'TakeOutFromBookshelfParameters'
    ]


class PutInBookshelf(Wizard):
    'Put In Bookshelf'
    __name__ = 'library.book.exemplary.put_in_bookshelf'

    start_state = 'parameters'
    parameters = StateView('library.book.exemplary.put_in_bookshelf.parameters',
    'library_location.put_in_bookshelf_parameters_view_form', [
        Button('Cancel', 'end', 'tryton-cancel'),
        Button('Put', 'put', 'tryton-go-next',
            default=True)])
    put = StateTransition()

class PutInBookshelfParameters(ModelView):
    'Put In bookshelf Parameters'
    __name__ = 'library.book.exemplary.put_in_bookshelf.parameters'

    exemplaries = fields.Many2Many('library.book.exemplary', None, None,
        'Exemplaries', required=True)
    target_bookshelf = fields.Many2One('library.floor.room.bookshelf', 'Target Bookshelf',
                                       required=True)
    
class TakeOutFromBookshelf(Wizard):
    'Take Ouf Of Bookshelf'
    __name__ = 'library.book.exemplary.take_out_from_bookshelf'

    start_state = 'parameters'
    parameters = StateView(
        'library.book.exemplary.take_out_from_bookshelf.parameters',
        'library_location.exemplary_take_out_of_bookshelf_view_form', [
        Button('Cancel', 'end', 'tryton-cancel'),
        Button('Take Out', 'take_out', 'tryton-go-next',
            default=True)]
    )
    take_out = StateTransition()

class TakeOutFromBookshelfParameters(ModelView):
    __name__ = 'library.book.exemplary.take_out_from_bookshelf.parameters'

    exemplaries = fields.Many2Many('library.book.exemplary', None, None,
        'Exemplaries', required=True)