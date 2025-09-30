import datetime

from sql import Window, Literal
from sql.conditionals import Coalesce
from sql.aggregate import Count, Max

from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction
from trytond.model import ModelSQL, ModelView, fields
from trytond.model import Unique
from trytond.pyson import Eval, If, Bool, Date


__all__ = [
    'Floor',
    'Room',
    'Bookshelf',
    'Exemplary',
    'QuarantineZone'
    ]

class Floor(ModelSQL, ModelView):
    'Floor'

    __name__ = 'library.floor'

    name = fields.Char('Name', required=True)
    rooms = fields.One2Many('library.floor.room', 'floor', 'Rooms')
    number_of_rooms = fields.Function(
        fields.Integer('Number of rooms', help='The number of rooms of this floor'),
        'getter_number_of_rooms'
    )

    @classmethod
    def getter_number_of_rooms(cls, floors, name):
        room = Pool().get('library.floor.room').__table__()
        result = {f.id: 0 for f in floors}
        cursor = Transaction().connection.cursor()

        cursor.execute(*room.select(room.floor, Count(room.floor),
                where=room.floor.in_([f.id for f in floors]),
                group_by=[room.floor]))
        
        for floor_id, count in cursor.fetchall():
            result[floor_id] = count

        return result

class Room(ModelSQL, ModelView):
    'Room'

    __name__ = 'library.floor.room'

    name = fields.Char('Name', required=True)
    floor = fields.Many2One('library.floor', 'Floor', required=True,
        ondelete='CASCADE', select=True)
    bookshelves = fields.One2Many('library.floor.room.bookshelf', 'room', 'Bookshelves')
    number_of_bookshelves = fields.Function(
        fields.Integer('Number of bookshelves', help='The number of bookshelves in this room'),
        'getter_number_of_bookshelves'
    )

    @classmethod
    def getter_number_of_bookshelves(cls, rooms, name):
        bookshelf = Pool().get('library.floor.room.bookshelf').__table__()
        result = {r.id: 0 for r in rooms}
        cursor = Transaction().connection.cursor()

        cursor.execute(*bookshelf.select(bookshelf.room, Count(bookshelf.room),
                where=bookshelf.room.in_([r.id for r in rooms]),
                group_by=[bookshelf.room]))
        
        for room_id, count in cursor.fetchall():
            result[room_id] = count

        return result

class Bookshelf(ModelSQL, ModelView):
    'Bookshelf'

    __name__ = 'library.floor.room.bookshelf'

    name = fields.Char('Name', required=True)
    room = fields.Many2One('library.floor.room', 'Room', required=True,
        ondelete='CASCADE', select=True)
    exemplaries = fields.One2Many('library.book.exemplary', 'bookshelf', 'Exemplaries',
                                  readonly=True)
    number_of_exemplaries= fields.Function(
        fields.Integer('Number of exemplaries', help='The number of exemplaries in this bookshelf'),
        'getter_number_of_exemplaries',
    )
    
    @classmethod
    def getter_number_of_exemplaries(cls, bookshelves, name):
        exemplary = Pool().get('library.book.exemplary').__table__()
        result = {b.id: 0 for b in bookshelves}
        cursor = Transaction().connection.cursor()

        cursor.execute(*exemplary.select(exemplary.bookshelf, Count(exemplary.bookshelf),
                where=exemplary.bookshelf.in_([b.id for b in bookshelves]),
                group_by=[exemplary.bookshelf]))
        
        for bookshelf_id, count in cursor.fetchall():
            result[bookshelf_id] = count

        return result
    
class Exemplary(metaclass=PoolMeta):
    __name__ = 'library.book.exemplary'

    bookshelf = fields.Many2One('library.floor.room.bookshelf', 'Bookshelf',
        ondelete='RESTRICT', select=True, readonly=True)
    is_in_storage = fields.Function(
        fields.Boolean('Is in storage', help='Boolean to true if the exemplary is currently in storage'),
        'getter_is_in_storage',
        searcher='search_is_in_storage'
    )

    @classmethod
    def getter_is_in_storage(cls, exemplaries, name):
        exemplary = Pool().get('library.book.exemplary').__table__()
        result = {e.id: False for e in exemplaries}
        cursor = Transaction().connection.cursor()
        
        cursor.execute(*exemplary.select(exemplary.id, exemplary.bookshelf,
                where=((exemplary.id.in_([e.id for e in exemplaries])) &
                       (exemplary.bookshelf == None))))
        
        for exemplary_id, _ in cursor.fetchall():
            result[exemplary_id] = True

        return result
    
    @classmethod
    def search_is_in_storage(cls, name, clause):
        _, operator, value = clause
        if operator == '!=':
            value = not value
        exemplary = Pool().get('library.book.exemplary').__table__()

        query = exemplary.select(exemplary.id, where=(exemplary.bookshelf == None))

        return [('id', 'in' if value else 'not in', query)]

class QuarantineZone(ModelSQL, ModelView):
    'Quarantine Zone'

    __name__ = 'library.quarantine_zone'

    exemplary = fields.Many2One('library.book.exemplary', 'Exemplary',
                                help='Exemplary being in quarantine zone',
                                required=True)
    start_date = fields.Date('Start Date', help='Beginning of quarantine',
                             domain=[('start_date', '>=', Date())],
                             required=True)
    end_date = fields.Function(
        fields.Date('End Date', help='End of quarantine'),
        'getter_end_date')
    
    def getter_end_date(self, name):
        return self.start_date + datetime.timedelta(days=7)

# class Bookshelf(ModelSQL, ModelView):
#     'Bookshelf'

#     __name__ = 'library.floor.room.bookshelf'

#     name = fields.Char('Name', required=True)
#     room = fields.Many2One('library.floor.room', 'Room', required=True,
#         ondelete='CASCADE', select=True)
#     exemplaries = fields.One2Many('library.book.exemplary', 'bookshelf', 'Exemplaries',
#                                   readonly=True)
#     number_of_exemplaries= fields.Function(
#         fields.Integer('Number of exemplaries', help='The number of exemplaries in this bookshelf'),
#         'getter_number_of_exemplaries',
#     )
#     capacity = fields.Integer('Capacity', help='The maximum number of exemplaries this bookshelf'
#                 'can contain', required=True)
#     available_slots = fields.Function(
#         fields.Integer('Available slots', help='The number of available slots in the bookshelf'),
#         'getter_available_slots',
#     )
#     is_full = fields.Function(
#         fields.Boolean('Is full', help='True if the bookshelf is full and' \
#         'cannot contain any additional exemplary'),
#         'getter_is_full',
#         searcher='search_is_full'
#     )
    
#     @classmethod
#     def getter_number_of_exemplaries(cls, bookshelves, name):
#         exemplary = Pool().get('library.book.exemplary').__table__()
#         result = {b.id: 0 for b in bookshelves}
#         cursor = Transaction().connection.cursor()

#         cursor.execute(*exemplary.select(exemplary.bookshelf, Count(exemplary.bookshelf),
#                 where=exemplary.bookshelf.in_([b.id for b in bookshelves]),
#                 group_by=[exemplary.bookshelf]))
        
#         for bookshelf_id, count in cursor.fetchall():
#             result[bookshelf_id] = count

#         return result
    
#     @classmethod
#     def getter_available_slots(cls, bookshelves, name):
#         exemplary = Pool().get('library.book.exemplary').__table__()
#         bookshelf = cls.__table__()
#         result = {b.id: 0 for b in bookshelves}
#         cursor = Transaction().connection.cursor()

#         subquery = exemplary.select(exemplary.bookshelf, Count(exemplary.bookshelf).as_('count'),
#                 where=exemplary.bookshelf.in_([b.id for b in bookshelves]),
#                 group_by=[exemplary.bookshelf])
        
#         cursor.execute(*bookshelf.join(subquery, 'LEFT OUTER', condition=(
#             bookshelf.id == subquery.bookshelf
#         )).select(bookshelf.id, (bookshelf.capacity - Coalesce(subquery.count, Literal(0)))
#                   ))

#         for bookshelf_id, count in cursor.fetchall():
#             result[bookshelf_id] = count

#         return result
    
#     @classmethod
#     def getter_is_full(cls, bookshelves, name):
#         exemplary = Pool().get('library.book.exemplary').__table__()
#         bookshelf = cls.__table__()
#         result = {b.id: False for b in bookshelves}
#         cursor = Transaction().connection.cursor()

#         subquery = exemplary.select(exemplary.bookshelf, Count(exemplary.bookshelf).as_('count'),
#                 where=exemplary.bookshelf.in_([b.id for b in bookshelves]),
#                 group_by=[exemplary.bookshelf])
        
#         cursor.execute(*bookshelf.join(subquery, condition=(
#             bookshelf.id == subquery.bookshelf
#         )).select(bookshelf.id, (subquery.count == bookshelf.capacity)
#                   ))
        
#         for bookshelf_id, is_full in cursor.fetchall():
#             result[bookshelf_id] = is_full

#         return result
    
#     @classmethod
#     def search_is_full(cls, name, clause):
#         _, operator, value = clause
#         if operator == '!=':
#             value = not value
#         exemplary = Pool().get('library.book.exemplary').__table__()
#         bookshelf = cls.__table__()

#         subquery = exemplary.select(exemplary.bookshelf, Count(exemplary.bookshelf).as_('count'),
#                 group_by=[exemplary.bookshelf])
        
#         query = bookshelf.join(subquery, condition=(
#             bookshelf.id == subquery.bookshelf
#         )).select(bookshelf.id, where=(subquery.count == bookshelf.capacity)
#                   )

#         return [('id', 'in' if value else 'not in', query)]