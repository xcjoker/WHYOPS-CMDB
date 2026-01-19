import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import authHttp from '@/api/authHttp'

export const useMonitorData = defineStore('monitor', () => {
	let remaining_mem = ref(0)
	
	
	async function PostMonitorData(ip) {
		const res = await authHttp.monitorPost(ip)
		remaining_mem.value = res.data
	}

  return { PostMonitorData, remaining_mem }
})
