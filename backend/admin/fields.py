import itertools

from flask_admin.model.fields import InlineFieldList
from wtforms.fields import _unset_value as unset_value



class NewInlineFieldList(InlineFieldList):

    def __init__(self, *args, initial_show=False, **kwargs):
        self.initial_show = initial_show
        super(NewInlineFieldList, self).__init__(*args, **kwargs)


    def populate_obj(self, obj, name):
        values = getattr(obj, name, None)
        try:
            ivalues = iter(values)
        except TypeError:
            ivalues = iter([])

        candidates = itertools.chain(ivalues, itertools.repeat(None))
        _fake = type(str('_fake'), (object, ), {})
        output = []

        for field, data in zip(self.entries, candidates):
            if not self.should_delete(field) and data:
                fake_obj = _fake()
                fake_obj.data = field.data
                field.populate_obj(fake_obj, 'data')
                output.append(fake_obj.data)
        values = getattr(obj, name, [])
        if len(self.entries) > len(values):
            for field in self.entries[len(values):]:
                if not self.should_delete(field) and type(field.data) is not dict:
                    fake_obj = _fake()
                    fake_obj.data = field.data
                    field.populate_obj(fake_obj, 'data')
                    output.append(fake_obj.data)
        setattr(obj, name, output)