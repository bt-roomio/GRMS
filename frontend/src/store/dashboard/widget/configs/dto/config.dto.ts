interface IOccupancyConfigDto {
    data: IOccupancyData[],
    borderColor: IOccupancyBorderColor
    backgroundColor: IOccupancyBackgroundColor,
    label: IOccupancyLabel
}
interface IOccupancyData {
    date: Date
    year?: number,
    last_year?: number
}
interface IOccupancyBorderColor{
    year?: string,
    last_year?: string
}
interface IOccupancyBackgroundColor{
    year?: string,
    last_year?: string
}
interface IOccupancyLabel{
    year?: string,
    last_year?: string
}