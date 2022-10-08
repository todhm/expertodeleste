from flask_admin.contrib.mongoengine import (
    ModelView,
)


class CollectionsView(ModelView):
    column_default_sort = ('_id', True)
    create_template = 'collectionsedit.html'
    edit_template = 'collectionsedit.html'
