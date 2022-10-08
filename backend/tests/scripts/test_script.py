import pytest
from scripts.naver import naver_smartstore_script



@pytest.mark.asyncio()
async def test_smartstore_script(test_app):
    link = "https://smartstore.naver.com/lkbeautyshop/products/6485131412"
    tag_list = ['SECA']
    result = await naver_smartstore_script(
        link,
        brand_name="더랩바이블랑두",
        tag_list=tag_list
    )
    assert result.tagList == tag_list
    assert len(result.description) > 0
    assert result.cost > 0
    assert result.price > 0
    assert result.price > result.cost
    with open('datacollections/test.html', 'w') as f:
        f.write(result.description)
