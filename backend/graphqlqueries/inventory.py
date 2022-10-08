

INVENTORY_FETCH_QUERIES: str = '''
query{
  shop{
    locations(first: 100){
      edges{
        node{
          id,
          name,
        }
      }
    }
  }
}
'''