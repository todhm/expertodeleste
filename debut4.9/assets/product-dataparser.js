const AvailableStyleTagList = [
    "Classics",
    "Breakfast Nook",
    "Modern",
    "Outdoor",
    "Simple"
]

const AvailableBrightnessMap = {
    "Bright": "Bright",
    "Dark": "Dark"
}
const OtherBrightnessMap = {
    "Bright": "Dark",
    "Dark": "Bright"
}

const AvailableSizeMap = {
    "Big": "Big",
    "Small": "Small",
    "Medium": "Medium"
};
const OppositeSizeMap = {
    "Big": "Small",
    "Small": "Big",
    "Medium": "Small"
}

const recommendNameMap = {
    "Bright:similarBrightness": "Other Bright Mood Sets",
    "Bright:otherBrightness": "Do you want more brighter sets?",
    "Dark:similarBrightness": "Other dark mood sets",
    "Dark:otherBrightness": "You want more darker sets?",
    "Small:similarSize": "Other Small Size Sets",
    "Medium:similarSize": "Bigger size sets",
    "Medium:otherSize": "Lookiing for smaller sets?",
    "Small:otherSize": "You want more smaller sets?",
    "Big:similarSize": "Other Big Size Sets",
    "Big:otherSize": "You want bigger sets?",
}

const renderTagName = (tag, loc)=>{
    if(loc === "similarStyle"){
        return `${tag} sets we recommend`
    }    
    return recommendNameMap[`${tag}:${loc}`]
}

const makeQueryWithTags=(tag)=>{
    let innerQueryTag = "";
    if(tag.includes("Small")){
        innerQueryTag = "tag:'Small' OR tag:'Medium'";
    }else{
        innerQueryTag = `tag:'${tag}'`;
    }

    return {
        query: `query {     
            products(query: "${innerQueryTag} AND available_for_sale:true", first:16, sortKey: BEST_SELLING){
                edges{
                  node{
                    id,
                    handle,
                    title,
                    featuredImage{
                        url(transform: {preferredContentType:WEBP, maxWidth: 500})
                    },
                    
                    priceRange{
                      minVariantPrice{
                        amount,
                        currencyCode
                      }
                    },
                    compareAtPriceRange{
                      minVariantPrice{
                        amount,
                        currencyCode
                      }
                    }
                    reviewCount:metafield(namespace: "reviews", key: "rating_count"){
                        value
                    }
                    reviewValue:metafield(namespace: "reviews", key: "rating"){
                      value
                    }
                  }
                  
                }
              }
        }`
    }
}


const returnAvailableTags = (tagList) => {
    const dataList = [
        "similarStyle",
        "similarBrightness",
        "otherBrightness",
        "similarSize",
        "otherSize"
    ]
    let tagMap = {}
    tagList.forEach((tag)=>{
        if (AvailableStyleTagList.includes(tag)){
            tagMap["similarStyle"] = tag;
        }
        if(Object.keys(AvailableBrightnessMap).includes(tag)){
            tagMap["similarBrightness"] = AvailableBrightnessMap[tag];
            tagMap["otherBrightness"] = OtherBrightnessMap[tag];
        }
        if(Object.keys(AvailableSizeMap).includes(tag)){
            tagMap["similarSize"] = AvailableSizeMap[tag];
            tagMap["otherSize"] = OppositeSizeMap[tag];
        }
    })
    return dataList.filter((x)=> tagMap[x]).map((x)=>{
        return {
            tagName: renderTagName(tagMap[x], x),
            query: makeQueryWithTags(tagMap[x])
        }
    })
}