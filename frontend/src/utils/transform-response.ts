const addFieldSelect = (data: string) => {
    let response = JSON.parse(data)
    response.results = response?.results?.map((el: any) => {
        el.select = false
        return el
    })
    return response
}
const addFieldSelectArray = (data: string) => {
    let response = JSON.parse(data)
    if (Array.isArray(response)) {
        response = response?.map((el: any) => {
            el.select = false
            return el
        })
        return response
    }
    return []
}
export {addFieldSelect, addFieldSelectArray}