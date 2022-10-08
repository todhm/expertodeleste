PUBLICATION_QUERY: str = '''mutation productPublish($input: ProductPublishInput!) {
  productPublish(input: $input) {
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