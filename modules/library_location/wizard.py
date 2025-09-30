import datetime

from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval, PYSONEncoder
from trytond.transaction import Transaction
from trytond.model import ModelView, fields
from trytond.wizard import Wizard, StateView, StateTransition, StateAction
from trytond.wizard import Button

__all__ = [
    'PutInBookshelf',
    'PutInBookshelfParameters',
    'PutInStorageBookshelf',
    'PutInStorageBookshelfParameters',
    'CreateExemplaries',
    'CreateExemplariesParameters',
    'Return',
    'BorrowSelectBooks'
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
    
class PutInStorage(Wizard):
    'Put In Storage'

    __name__ = 'library.book.exemplary.put_in_storage'

    start_state = 'parameters'
    parameters = StateView(
        'library.book.exemplary.put_in_storage.parameters',
        'library_location.exemplary_put_in_storage_view_form', [
        Button('Cancel', 'end', 'tryton-cancel'),
        Button('Put in storage', 'put_in', 'tryton-go-next',
            default=True)]
    )
    put_in = StateTransition()

    def default_parameters(self, name):
        Exemplary = Pool().get('library.book.exemplary')
        exemplaries = Exemplary.browse(
                Transaction().context.get('active_ids'))

        return {
            'exemplaries': [e.id for e in exemplaries]
        }
    
    def transition_put_in(self):
        Exemplary = Pool().get('library.book.exemplary')

        Exemplary.write(list(self.parameters.exemplaries), {
                'bookshelf': None})
        
        return 'end'

class PutInStorageParameters(ModelView):
    'Take Ouf Of Bookshelf Parameters'

    __name__ = 'library.book.exemplary.put_in_storage.parameters'

    exemplaries = fields.Many2Many('library.book.exemplary', None, None,
        'Exemplaries', required=True)
    
class CreateExemplaries(metaclass=PoolMeta):
    'Create Exemplaries'
    __name__ = 'library.book.create_exemplaries'
    
    def transition_create_exemplaries(self):
        res = super().transition_create_exemplaries()

        Exemplary = Pool().get('library.book.exemplary')

        created_exemplaries = self.parameters.exemplaries
        to_bookshelf = created_exemplaries[self.parameters.nb_to_put_in_storage:]

        Exemplary.write(list(to_bookshelf), {'bookshelf': self.parameters.target_bookshelf.id})

        return res
        

class CreateExemplariesParameters(metaclass=PoolMeta):
    __name__ = 'library.book.create_exemplaries.parameters'

    target_bookshelf = fields.Many2One('library.floor.room.bookshelf', 'Target Bookshelf',
                                       help='The bookshelf the exemplaries will be stored in',
                                       required=True)
    
    nb_to_put_in_storage = fields.Integer('Nb to put in storage', help='Number of exemplaries to put in storage',
                                          required=True,
                                          depends=['number_of_exemplaries'],
                                          domain=[('nb_to_put_in_storage', '>=', 0),
                                                  ('nb_to_put_in_storage', '<=', Eval('number_of_exemplaries'))])

class BorrowSelectBooks(metaclass=PoolMeta):
    __name__ = 'library.user.borrow.select_books'

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.exemplaries.domain.append(('is_in_storage', '=', False))

class Return(metaclass=PoolMeta):
    __name__ = 'library.user.return'

    def transition_return_(self):
        res = super().transition_return_()

        QuanrantineZone = Pool().get('library.quarantine_zone')
        returned_exemplaries_ids = [c.exemplary.id for c in
                                                 list(self.select_checkouts.checkouts)]
        to_create = []

        for exemplary_id in returned_exemplaries_ids:
            quanrantine_zone = QuanrantineZone()
            quanrantine_zone.exemplary = exemplary_id
            quanrantine_zone.start_date = datetime.date.today()
            to_create.append(quanrantine_zone)
        
        QuanrantineZone.save(to_create)

        return res