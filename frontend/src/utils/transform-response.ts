const addFieldSelect = (data: string) => {
    let response = JSON.parse(data)
    response.results = response?.results?.map((el: any) => {
        el.select = false
        return el
    })
    return response
}
export {addFieldSelect}