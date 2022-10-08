from typing import Dict

VideoUrl: str = '''
fragment fieldsForMediaTypes on Media {
  ... on Video {
    id
    mediaContentType
    status
    originalSource{
      url
    }
    preview {
      image {
        altText
        originalSrc
      }
    }
  }
}'''

ImageUrl: str = '''
fragment fieldsForImageType on Media {
  ... on MediaImage {
    id
    mediaContentType
    status
    image{
      url
    }
  }
}'''

AllProductInfo: str = '''
    fragment AllProductInfo on Product {
        createdAt,
        descriptionHtml,
        featuredImage{
          url,
        },
        feedback{
          details{
            messages{
              message
            }
          },
          summary
        },
        handle,
        id,
        metafields(first: 20){
          edges{
            node{
              id,
              namespace,
              key,
              value
            }
          }
        },
        options{
          name
          values
        },
        productType,
        status,
        tags,
        title,
        totalInventory,
        vendor,
        images(first: 20){
          edges{
          	node {
              url
            }
          }
        },
        media(first: 20){
          edges{
            node{
              ...fieldsForMediaTypes
            }
          }
        },
        privateMetafields(first:20){
      		edges{
            node{
            	value
          	}
          }
      
    		},
        variants(first: 100){
          edges{
            node{
              sku,
              id,
              compareAtPrice,
              price,
              inventoryQuantity,
              weight,
              inventoryItem{
                unitCost{
                  amount,                	
                },
              },
              selectedOptions{
                name,
                value
              },
              image{
                url
              },
            }
          }
        }
    }
'''


def shopify_product_query(handle: str) -> str:
    return f'''
        query {{
            productByHandle(handle: "{handle}"){{
                ...AllProductInfo
            }}
        }}
        {AllProductInfo}
        {VideoUrl}
    '''


def shopify_get_first_variant(handle: str) -> str:
    return f'''
        query {{
            productByHandle(handle: "{handle}"){{
               variants(first: 1){{
                edges{{
                  node{{
                    sku,
                    id
                  }}
                }}
              }}
        }}
      }}
    '''

def create_product_query() -> str:
    return '''
    mutation productCreate($input: ProductInput!) {
            productCreate(input: $input) {
                product {
                    id
                }
                userErrors {
                  field
                  message
                }
            }
    }
    '''

def delete_product_query() -> str:
    return '''
    mutation productDelete($input: ProductDeleteInput!) {
            productDelete(input: $input) {
                deletedProductId
                userErrors {
                  field
                  message
                }
            }
    }
    '''


def update_product_query() -> str:
    return '''
    mutation productUpdate($input: ProductInput!) {
            productUpdate(input: $input) {
                product {
                    id
                }
                userErrors {
                  field
                  message
                }
            }
    }
    '''


UPDATE_METAFIELD_QUERIES: str = '''
mutation metafieldsSet($metafields: [MetafieldsSetInput!]!) {
  metafieldsSet(metafields: $metafields) {
    metafields {
      id
    }
    userErrors {
      field
      message
    }
  }
}
'''