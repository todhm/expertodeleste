from mongoengine import (
    EmbeddedDocument,
    DynamicDocument
)
from mongoengine.fields import (
    StringField,
    IntField,
    FloatField,   
    ListField,
    EmbeddedDocumentField,
    BooleanField
)
from data_types.shipping import FREIGHT, FIXED
from data_types.ship_type import PARCEL, LTL


class ReviewData(EmbeddedDocument):
    reviewTitle: str = StringField()
    reviewText: str = StringField()
    reviewTime: str = StringField()
    writer: str = StringField()
    reviewPoint: float = FloatField()
    reviewImageList: list = ListField(StringField(), default=list)


class QuestionData(EmbeddedDocument):
    questionTitle: str = StringField()
    answer: str = StringField()
    questionTime: str = StringField()
    writer: str = StringField()
    questionImageList: list = ListField(StringField(), default=list)

class DeliveryData(EmbeddedDocument):
    deliveryId: int = IntField()
    price: float = FloatField()
    cost: float = FloatField()
    deliveryType: str = StringField(choices=[FIXED, FREIGHT])
    deliveryName: str = StringField()
    deliveryDescription: str = StringField()
    minDays: int = IntField()
    maxDays: int = IntField()
    freightDiscountRate: float = FloatField()


class MustInfo(EmbeddedDocument):
    key = StringField(verbose_name='키')
    valueList = ListField(StringField(), default=list)


class WarehouseData(EmbeddedDocument):
    warehouseId = StringField()
    warehouseName = StringField()
    stock = IntField()


class OptionData(EmbeddedDocument):
    optionId = StringField()
    optionName = StringField()
    optionValue = StringField()
    optionImage = StringField()


class DefaultSetList(EmbeddedDocument):
    productName = StringField()
    defaultCount = IntField()
    thumbnailImage = StringField()

class AdditionalProductList(EmbeddedDocument):
    productId = StringField()
    shopifyVariantId = StringField()
    goodsUrl = StringField()
    productName = StringField()
    beforeSalePrice = FloatField()
    price = FloatField()
    thumbnailImage = StringField()
    defaultCount = IntField()
    isSoldOut = BooleanField(default=False)


class BrandDataCollection(DynamicDocument):
    meta = {
        'collection': 'brand_data',
    }
    brandId = StringField(default="")
    brandName = StringField(default="")
    brandDescription = StringField(default="")
    warranty = StringField()
    videoUrl = StringField(default="")
    brandLogo = StringField(default="")


class BrandData(EmbeddedDocument):
    brandId = StringField()
    brandName = StringField()
    brandDescription = StringField()
    warranty = StringField()
    videoUrl = StringField()
    brandLogo = StringField()


class WeightInfo(EmbeddedDocument):
    weight = FloatField()
    cuft = FloatField(null=True)
    packageWeight = FloatField()
    width = FloatField()
    height = FloatField()
    length = FloatField()
    packageWidth = FloatField()
    packageHeight = FloatField()
    packageLength = FloatField()


class Sku(EmbeddedDocument):
    shopifyId = StringField()
    skuId = StringField()
    upcCode = StringField(null=True, default='')
    supplierSku = StringField()
    cost = FloatField()
    price = FloatField()
    weight = FloatField()
    beforeSalePrice = FloatField()
    deliveryCost = FloatField()
    deliveryPrice = FloatField()
    optionList = ListField(
        EmbeddedDocumentField(OptionData),
        db_field="optionList"
    )
    warehouseInfo =  ListField(
        EmbeddedDocumentField(WarehouseData),
        db_field="warehouseInfo"
    )
    isSoldOut = BooleanField()
    weightInfo = EmbeddedDocumentField(WeightInfo, db_field="weightInfo", default=None)
    weightInfoList =  ListField(
        EmbeddedDocumentField(WeightInfo),
        db_field="weightInfoList",
        default=list
    )


class Product(DynamicDocument):
    meta = {
        'collection': 'product',
    }
    goodsUrl = StringField()
    collectionProductUrl = StringField()
    productId = StringField()
    additionalGroupId = StringField(null=True, default='')
    upcCode = StringField(null=True, default='')
    shopifyId = StringField()
    videoUrlList = ListField(StringField(), verbose_name="비디오UrlList", default=list)
    goodsName = StringField()
    shortDescription = StringField()
    deliveryInfo = StringField()
    description = StringField()
    manual = StringField()
    ingredient = StringField(verbose_name="재료설명")
    warranty = StringField()
    included = StringField()
    productType = StringField()
    additionalParentVariantId = StringField()
    tagList = ListField(StringField(), default=list)
    goodsMustInfo = ListField(
        EmbeddedDocumentField(MustInfo),
        db_field="goodsMustInfo",
        default=list
    )
    additionalProductList = ListField(
        EmbeddedDocumentField(AdditionalProductList),
        db_field="additionalProductList"
    )
    defaultSetList = ListField(
        EmbeddedDocumentField(DefaultSetList),
        db_field="defaultSetList"
    )
    mainImageList = ListField(StringField(), default=list)
    brandName = StringField()
    brandData = EmbeddedDocumentField(BrandData, db_field="brandData", default=None)
    weightInfo = EmbeddedDocumentField(WeightInfo, db_field="weightInfo", default=None)
    weightInfoList =  ListField(
        EmbeddedDocumentField(WeightInfo),
        db_field="weightInfoList",
        default=list
    )
    cost = FloatField()
    price = FloatField()
    beforeSalePrice = FloatField()
    optionNameList = ListField(StringField(), default=list)
    featureList = ListField(StringField(), default=list)
    skuList = ListField(
        EmbeddedDocumentField(Sku),
        db_field="skuList"
    )
    reviewList =  ListField(
        EmbeddedDocumentField(ReviewData),
        db_field="reviewList"
    )
    questionList =  ListField(
        EmbeddedDocumentField(QuestionData),
        db_field="questionList"
    )
    deliveryDataList =  ListField(
        EmbeddedDocumentField(DeliveryData),
        db_field="deliveryDataList"
    )
    stock = IntField()
    trackInventory: bool = BooleanField()
    shipType: str = StringField(
        choices=[
            PARCEL,
            LTL
        ]
    )
    isSoldOut = BooleanField()
    regDt: str = StringField()
    modDt: str = StringField()

    @property
    def to_json(self):
        return self.to_mongo().to_dict()
