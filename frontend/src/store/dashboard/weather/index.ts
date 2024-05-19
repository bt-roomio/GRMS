import {defineStore} from "pinia";
import axios from "axios";
import {ref} from "vue";

export const useWeather = defineStore('weather', () => {
    const weatherData = ref({
        country_name: '',
        name: '',
        icon: '',
        temp: 0
    })
    const getWeather = async () => {
        try {
            const {capital, name: country_name} = (await axios.get('https://api.vatcomply.com/geolocate')).data
            const {lat, lon, name} = (await axios('https://api.openweathermap.org/geo/1.0/direct', {
                method: 'GET',
                params: {
                    q: capital,
                    appid: '852fea6c8191e19d3d72f836adf3521f'
                }
            })).data[0]
            const {data} = await axios('https://api.openweathermap.org/data/2.8/onecall', {
                method: 'GET',
                params: {
                    exclude: 'minutely,hourly',
                    lat: lat,
                    lon: lon,
                    lang: 'en',
                    units: 'metric',
                    appid: '852fea6c8191e19d3d72f836adf3521f'
                }
            })
            weatherData.value.country_name = country_name
            weatherData.value.name = name
            weatherData.value.temp = Math.ceil(data.current.temp)
            weatherData.value.icon = data.current?.weather?.at(0)?.main.toLowerCase()
        }catch (e: any) {
            console.log(e)
        }
    }

    return { getWeather, weatherData }
})