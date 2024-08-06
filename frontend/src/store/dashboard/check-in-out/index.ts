import useApiFetch from '@/composables/useApiFetch.ts'
import router from '@/router'
import { useConfirm } from '@store/dashboard/useConfirm.ts'
import { addFieldSelect } from '@utils/transform-response.ts'
import useVuelidate from '@vuelidate/core'
import { minLength, required } from '@vuelidate/validators'
import moment from 'moment'
import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue3-toastify'
import {useConfigurationRoomsStore} from "@store/dashboard/configuration/rooms.ts";

export const useCheckInOutStore = defineStore('check-in-out', () => {
	const confirmStore = useConfirm()
	const storeRoom = useConfigurationRoomsStore()
	const { t } = useI18n()
	const loading = ref(false)
	const error = ref({ code: null, msg: null })
	const size = ref(10)
	const guest = ref(null)
	const guests = ref<IServerResponse<any>>({ count: 0, results: [] })
	const searchValue = ref('')
	const searchType = ref('name')
	const sortedData = ref({})
	const state = ref({
		name: '',
		lastname: '',
		gender: 'Man',
		nationality: '',
		birthday: null,
		is_active: true,
		room: '',
		check_in: moment().format('YYYY-MM-DDTHH:mm'),
		check_out: moment().format('YYYY-MM-DDTHH:mm'),
		auto_check_out: true,
		reservation_number: null,
	})

	const rules = computed(() => ({
		name: { required, minLength: minLength(2) },
		lastname: { required, minLength: minLength(2) },
		check_out: { required },
	}))

	const v$ = useVuelidate(rules, state, { $scope: false })

	const getGuests = async (params: IParams) => {
		loading.value = true
		error.value.code = null
		error.value.msg = null
		try {
			const { data } = await useApiFetch<IServerResponse<any>>(
				'/main/guest/',
				{
					method: 'GET',
					params: {
						...params,
						size: size.value,
						room: router.currentRoute.value.params.id
					},
					transformResponse: [data => addFieldSelect(data)],
				}
			)
			guests.value = data
		} catch (e: any) {
			if (e.response?.status) {
				error.value.code = e.response.status
				error.value.msg = e.response.data.detail
				guests.value = { results: [], count: 0 }
			}
			throw e
		} finally {
			loading.value = false
		}
	}

	const sortList = async (output: ISortOutput) => {
		sortedData.value = output
		await getGuests(
			searchValue.value
				? {
						...output,
						...router.currentRoute.value.query,
						search_value: searchValue.value,
						search_field: searchType.value,
				  }
				: { ...output, ...router.currentRoute.value.query }
		)
	}
	const loadMore = async () => {
		size.value += 10
		await getGuests(
			searchValue.value
				? {
						...sortedData.value,
						...router.currentRoute.value.query,
						search_value: searchValue.value,
						search_field: searchType.value,
				  }
				: { ...router.currentRoute.value.query }
		)
	}

	const checkIn = async (callback: () => void) => {
		const isFormCorrect = await v$.value.$validate()
		if (!isFormCorrect) return
		try {
			const newState = JSON.parse(JSON.stringify(state.value))
			newState.check_in = moment(newState.check_in).unix()
			newState.check_out = moment(newState.check_out).unix()
			newState.room = router.currentRoute.value.params.id as string
			const {data} = await useApiFetch('/main/guest/', {method: 'POST', data: newState})
			await Promise.all([
				getGuests(searchValue.value ? {
					...sortedData.value,
					...router.currentRoute.value.query,
					search_value: searchValue.value,
					search_field: searchType.value,
				} : {...sortedData.value, ...router.currentRoute.value.query}),
				storeRoom.getItem(router.currentRoute.value.params.id as string, false)
			])
			callback()
			await $reset()
			toast.success(t('toast.save_success') as string)
			return data
		} catch (e) {
			throw e
		}
	}

	const checkOut = async (id: string) => {
		await confirmStore.showConfirm({
			title: 'Checkout',
			content: 'Are you sure want to checkout selected guests in the room?',
			callback: async confirmed => {
				if (confirmed) {
					await useApiFetch(`/main/guest/${id}/`, {method: 'PUT', data: {is_active: false, room: null}})
					await updateState()
					toast.success(t('toast.save_success') as string)
				}
			},
		})
	}

	const moveAll = async (args: any, callback: () => void) => {
		callback()
		await confirmStore.showConfirm({
			title: 'Are you sure?',
			content: 'The guests will be checked into the specified room!',
			callback: async confirmed => {
				if (confirmed) {
					await useApiFetch(`/main/guest/move/room/`, {method: 'PUT', params: args})
					await updateState()
					toast.success(t('toast.save_success') as string)
				}
			},
		})
	}

	const move = async (args: any, callback: () => void) => {
		callback()
		await confirmStore.showConfirm({
			title: 'Are you sure?',
			content: 'The guests will be checked into the specified room!',
			callback: async confirmed => {
				if (confirmed) {
					await useApiFetch(`/main/guest/${args.id}/`, {method: 'PUT', data: args})
					await updateState()

					toast.success(t('toast.save_success') as string)
				}
			},
		})
	}
	const $reset = async () => {
		state.value = {
			name: '',
			lastname: '',
			gender: 'Man',
			nationality: '',
			birthday: null,
			is_active: true,
			room: '',
			check_in: moment().format('YYYY-MM-DDTHH:mm'),
			check_out: moment().format('YYYY-MM-DDTHH:mm'),
			auto_check_out: true,
			reservation_number: null,
		}
		v$.value.$reset()
	}
	watch(searchType, async value => {
		if (searchValue.value) {
			await getGuests({
				...sortedData.value,
				...router.currentRoute.value.query,
				search_value: searchValue.value,
				search_field: value,
			})
		}
	})
	watch(searchValue, async value => {
		await getGuests(
			searchValue.value
				? {
						...sortedData.value,
						...router.currentRoute.value.query,
						search_value: value,
						search_field: searchType.value,
				  }
				: { ...sortedData.value, ...router.currentRoute.value.query }
		)
	})
	const updateState = async () => {
		await Promise.all([
			getGuests(searchValue.value ? {
				...sortedData.value,
				...router.currentRoute.value.query,
				search_value: searchValue.value,
				search_field: searchType.value,
			} : {...sortedData.value, ...router.currentRoute.value.query}),
			storeRoom.getItem(router.currentRoute.value.params.id as string, false)
		])
	}
	return {
		guest,
		guests,
		loading,
		error,
		searchValue,
		searchType,
		sortedData,
		getGuests,
		loadMore,
		sortList,
		checkIn,
		checkOut,
		moveAll,
		move,
		$reset,
		state,
	}
})
