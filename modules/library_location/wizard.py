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

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._error_messages.update({
                'not_enough_space': 'There is not enough space in the selected bookshelf'
                'to put the exemplaries in',
                })

    def default_parameters(self, name):
        Exemplary = Pool().get('library.book.exemplary')
        exemplaries = Exemplary.browse(
                Transaction().context.get('active_ids'))

        return {
            'exemplaries': [e.id for e in exemplaries]
        }
    
    def transition_put(self):
        Exemplary = Pool().get('library.book.exemplary')

        Exemplary.write(list(self.parameters.exemplaries), {
                'bookshelf': self.parameters.target_bookshelf})
        
        return 'end'


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

    def default_parameters(self, name):
        Exemplary = Pool().get('library.book.exemplary')
        exemplaries = Exemplary.browse(
                Transaction().context.get('active_ids'))

        return {
            'exemplaries': [e.id for e in exemplaries]
        }
    
    def transition_take_out(self):
        Exemplary = Pool().get('library.book.exemplary')

        Exemplary.write(list(self.parameters.exemplaries), {
                'bookshelf': None})
        
        return 'end'

class TakeOutFromBookshelfParameters(ModelView):
    'Take Ouf Of Bookshelf Parameters'

    __name__ = 'library.book.exemplary.take_out_from_bookshelf.parameters'

    exemplaries = fields.Many2Many('library.book.exemplary', None, None,
        'Exemplaries', required=True)