from datetime import datetime as dt

from dataclasses import asdict, dataclass, field, fields, _MISSING_TYPE
from typing import List, Optional
from data_types.shipping import DELIVERY_TYPE, FIXED
from data_types.ship_type import ShipTypeType


@dataclass
class DefaultDataClass:
    def __init__(self, **kwargs):
        names = set([f.name for f in fields(self)])
        added_names = set()
        for k, v in kwargs.items():
            if k in names:
                added_names.add(k)
                setattr(self, k, v)
        for f in fields(self):
            if f.name not in added_names:
                if f.default_factory is list:
                    setattr(self, f.name, [])
                elif f.default_factory is dict:
                    setattr(self, f.name, {})
                else:
                    setattr(self, f.name, f.default)
    @property
    def to_json(self):
        return asdict(self)

@dataclass
class DeliveryData:
    deliveryId: int = None
    price: float = 0.0
    cost: float = 0.0
    freightDiscountRate: float = 0.0
    deliveryType: DELIVERY_TYPE = FIXED
    deliveryName: str = ""
    deliveryDescription: str = ""
    minDays: int = 0
    maxDays: int = 0


@dataclass
class OptionData(DefaultDataClass):
    optionId: str = ""
    optionName: str = ""
    optionValue: str = ""
    optionImage: str = ""

@dataclass
class WarehouseData(DefaultDataClass):
    warehouseId: str = ""
    warehouseName: str = ""
    stock: int = None
    

@dataclass
class WeightInfo(DefaultDataClass):
    weight: float = 0.0
    width: float = 0.0
    height: float = 0.0
    length: float = 0.0
    cuft: float = 0.0
    packageWeight: float = 0.0
    packageWidth: float = 0.0
    packageHeight: float = 0.0
    packageLength: float = 0.0

@dataclass
class Sku(DefaultDataClass):
    shopifyId: str = None
    skuId: str = None
    supplierSku: str = None
    upcCode: str = ""
    cost: float = 0.0
    price: float = 0.0
    weight: float = 0.0
    weightInfo: Optional[WeightInfo] = None
    beforeSalePrice: float = 0.0
    deliveryCost: float = 0.0
    deliveryPrice: float = 0.0
    optionList: List[OptionData] = field(default_factory=list)
    warehouseInfo: List[WarehouseData] = field(default_factory=list)
    weightInfoList: List[WeightInfo] = field(default_factory=list)
    isSoldOut: bool = False

    def __hash__(self):
        return hash(''.join([x.optionName for x in self.optionList]))

    def __eq__(self, other):
        if not self.SalePrice != other.SalePrice:
            return False
        if len(self.optionList) != len(other.optionList):
            return False
        for first_opt, second_opt in zip(self.optionList, other.optionList):
            is_same_option = all([
                first_opt.optionValue == second_opt.optionValue,
                first_opt.optionImage == second_opt.optionImage,
                first_opt.originalImage == second_opt.originalImage
            ])
            if not is_same_option:
                return False
        return True

    def __init__(self, **kwargs):
        names = set([f.name for f in fields(self)])
        added_names = set()
        for k, v in kwargs.items():
            if k == 'optionList':
                option_list = [OptionData(**od) for od in v]
                self.optionList = option_list
                added_names.add(k)
            elif k == "weightInfo" and v:
                self.weightInfo = WeightInfo(**v)
                added_names.add(k)
            elif k == 'warehouseInfo':
                warehouse_list = [WarehouseData(**od) for od in v]
                self.warehouseInfo = warehouse_list
                added_names.add(k)
            elif k == 'weightInfoList' and v and type(v) is list and type(v[0]) is dict:
                self.weightInfoList = [WeightInfo(**rd) for rd in v]
                added_names.add(k)
            elif k in names:
                added_names.add(k)
                setattr(self, k, v)
        for f in fields(self):
            if f.name not in added_names:
                if f.default_factory is list:
                    setattr(self, f.name, [])
                elif f.default_factory is dict:
                    setattr(self, f.name, {})
                else:
                    setattr(self, f.name, f.default)
@dataclass
class ReviewData(DefaultDataClass):
    reviewTitle: str = ""
    reviewText: str = ""
    reviewTime: str = ""
    writer: str = ""
    reviewPoint: float = 5.0
    reviewImageList: list = field(default_factory=list)
    
    
@dataclass
class QuestionData(DefaultDataClass):
    questionTitle: str = ""
    answer: str = ""
    questionTime: str = ""
    writer: str = ""
    questionImageList: list = field(default_factory=list)
    

                    
@dataclass
class MustInfo(DefaultDataClass):
    key: str = ""
    valueList: list = field(default_factory=list)
        
        
@dataclass
class BrandData(DefaultDataClass):
    brandId: str = ""
    brandName: str = ""
    brandDescription: str = ""
    warranty: str = ""
    videoUrl: str = ""
    brandLogo: str = ""


@dataclass
class DefaultSetList(DefaultDataClass):
    productName: str = ""
    defaultCount: int = 0
    thumbnailImage: str = ""

@dataclass
class AdditionalProductList(DefaultDataClass):
    productId: str = ""
    shopifyVariantId: str = ""
    goodsUrl: str = ""
    productName: str = ""
    price: float = 0.0
    beforeSalePrice: float = 0.0
    thumbnailImage: str = ""
    defaultCount: int = 0
    isSoldOut: bool = False
    

@dataclass
class ProductData(DefaultDataClass):
    # 상품리뷰그룹
    goodsUrl: str = ""
    productId: str = "" # 내가 지정한 productId
    collectionProductUrl: str = "" # 내가 지정한 productId
    additionalGroupId: str = "" # 내가 지정한 productId
    upcCode: str = ""
    shopifyId: str = None # shopify에서 상품생성시 생기는 ID
    videoUrlList: list = field(default_factory=list)
    goodsName: str = ""
    shortDescription: str = ""
    deliveryInfo: str = ""
    description: str = ""
    manual: str = ""
    ingredient: str = ""
    warranty: str = ""
    additionalParentVariantId: str = ""
    included: str = ""
    productType: str = ""
    tagList: List[str] = field(default_factory=list)
    goodsMustInfo: List[MustInfo] = field(default_factory=list)
    featureList: List = field(default_factory=list)
    additionalProductList: List[AdditionalProductList] = field(default_factory=list)
    defaultSetList: List[DefaultSetList] = field(default_factory=list)
    mainImageList: list = field(default_factory=list)
    brandName: str = ""
    brandData: BrandData = None
    weightInfo: Optional[WeightInfo] = None
    weightInfoList: List[WeightInfo] = field(default_factory=list)
    cost: float = 0.0
    price: float = 0.0
    beforeSalePrice: float = 0.0
    optionNameList: List = field(default_factory=list)
    skuList: List[Sku] = field(default_factory=list)
    reviewList: List[ReviewData] = field(default_factory=list)
    questionList: List[QuestionData] = field(default_factory=list)
    deliveryDataList: List[DeliveryData] = field(default_factory=list)
    stock: int = 100
    isSoldOut: bool = False
    taxable: bool = True
    trackInventory: bool = False
    shipType: Optional[ShipTypeType] = None
    regDt: str = ""
    modDt: str = ""

    def __init__(self, **kwargs):
        names = set([f.name for f in fields(self)])
        added_names = set()
        for k, v in kwargs.items():
            if k == 'skuList':
                lately_option_list = [Sku(**od) for od in v]
                self.skuList = lately_option_list
                added_names.add(k)
            elif k == "reviewList":
                review_list = [ReviewData(**rd) for rd in v]
                self.reviewList = review_list
                added_names.add(k)
            elif k == "questionList":
                review_list = [QuestionData(**rd) for rd in v]
                self.questionList = review_list
                added_names.add(k)
            elif k == 'goodsMustInfo':
                must_info_list = [MustInfo(**rd) for rd in v]
                self.goodsMustInfo = must_info_list
                added_names.add("goodsMustInfo")
            elif k == "deliveryDataList":
                delivery_list = [DeliveryData(**rd) for rd in v]
                self.deliveryDataList = delivery_list
                added_names.add(k)
            elif k == "brandData" and v and type(v) is dict:
                self.brandData = BrandData(**v)
                added_names.add(k)
            elif k == 'weightInfo' and v and type(v) is dict:
                self.weightInfo = WeightInfo(**v)
                added_names.add(k)
            elif k == 'weightInfoList' and v and type(v) is list and type(v[0]) is dict:
                self.weightInfoList = [WeightInfo(**rd) for rd in v]
                added_names.add(k)
            elif k == "additionalProductList":
                self.additionalProductList = [AdditionalProductList(**rd) for rd in v]
                added_names.add(k)
            elif k == "defaultSetList":
                self.defaultSetList = [DefaultSetList(**rd) for rd in v]
                added_names.add(k)
            elif k in names:
                added_names.add(k)
                setattr(self, k, v)
        for f in fields(self):
            if f.name not in added_names:
                if f.default_factory is list:
                    setattr(self, f.name, [])
                elif f.default_factory is dict:
                    setattr(self, f.name, {})
                else:
                    setattr(self, f.name, f.default)
    
    def add_tag(self, tag: str):
        if tag not in self.tagList:
            self.tagList.append(tag)
                    
    def remove_tag(self, tag: str):
        tag_sets = set(self.tagList)
        tag_sets = tag_sets - set([tag])
        self.tagList = list(tag_sets)
            
                    
