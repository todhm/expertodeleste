from mongoengine import (
    DynamicDocument
)
from mongoengine.fields import (
    StringField,
)

class Collections(DynamicDocument):
    collectionimage: str = StringField()
    collectionDescription: str = StringField()
    collectionImageUrl: str = StringField()