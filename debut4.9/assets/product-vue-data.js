const shopId = "locamusica";
const shopifyenjoy = "8c8a16ae65f92b757b32bf55128ccea1";
const headers = {
    'Content-Type': 'application/json',
    'X-Shopify-Storefront-Access-Token': shopifyenjoy
}
const descriptionListingState = Vue.reactive({
    hidden: true,
    index: 0,
    mobileProductListing: [
        {name:"Description", show: true},
        {name:"Brand", show: false},
        {name:"Specs", show: false},
        {name:"Warranty & Return Policy", show: false}
    ]
})

const nestedCopy=(array)=>{
    return JSON.parse(JSON.stringify(array));
}

const store = Vue.reactive({
    state: {
        additionalProductList: []
    },
    matchAdditionalData(addditionalSetList) {
    if(addditionalSetList){
        axios.get('/cart.js')
        .then(response => {
            const itemsCount = response.data.items;
            Object.assign(this.state.additionalProductList,nestedCopy(addditionalSetList.map(x=>{
                const filteredCounts = itemsCount.filter(cartItem=>{
                    return cartItem.id === parseInt(x.shopifyVariantId);
                })
                if(filteredCounts.length > 0){
                    x.currentCount = filteredCounts[0].quantity
                }
                else{
                    x.currentCount = 0;
                }
                return x;
            })));
        })
        .catch(error => {
          console.log(error)
        })
    } 
    }
})
  

const toggleDescriptionButton = {
    clickListing() {
        descriptionListingState.hidden = !descriptionListingState.hidden
    },
    changeIndex(number){
        descriptionListingState.index = number;
    }
}

const slideImage = (e)=>{
    $(this).toggle("slide:right");
}