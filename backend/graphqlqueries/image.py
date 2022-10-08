UPLOAD_IMAGE_QUERY: str = """mutation($input: StagedUploadTargetGenerateInput!) {
      stagedUploadTargetGenerate(input: $input) {
      parameters{
          name
          value
      }
      url
      userErrors {
          field
          message
      }
    }
  }"""