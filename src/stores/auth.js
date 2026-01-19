import {
	ref,
	computed
} from 'vue'
import {
	defineStore
} from 'pinia'

const USER_KEY = "OA_USER_KEY"
const TOKEN_KEY = "OA_TOKEN_KEY"
 
export const useAuthStore = defineStore('auth', () => {
	let _user = ref({})
	let _token = ref("")

	function setUserToken(user, token) {
		// 保存到对象上（内存中）
		_user.value = user;
		_token.value = token;

		// 存储到浏览器的localStorge中（硬盘上）
		localStorage.setItem(USER_KEY, JSON.stringify(user))
		localStorage.setItem(TOKEN_KEY, token);
	}
	
	function clearUserToken(){
		_user.value = {}
		_token.value = ""
		localStorage.removeItem(USER_KEY)
		localStorage.removeItem(TOKEN_KEY)
	}

	// 计算属性
	let user = computed(() => {
		// _user.value = {}
		// 在JS中
		// 1. 空对象{}：用if判断，会返回true，Object.keys(_user.value).length==0
		// 2. 空字符串""：用if判断，会返回false
		if (Object.keys(_user.value) == 0) {
			let user_str = localStorage.getItem(USER_KEY)
			if (user_str) {
				_user.value = JSON.parse(user_str)
			}
		}
		return _user.value
	})

	let token = computed(() => {
		if (!_token.value) {
			let token_str = localStorage.getItem(TOKEN_KEY)
			if (token_str) {
				_token.value = token_str
			}
		}
		return _token.value;
	})
	
	let is_logined = computed(() => {
		if(Object.keys(user.value).length>0 && token.value){
			return true
		}
		return false
	})

	return {
		setUserToken,
		user,
		token,
		is_logined,
		clearUserToken
	}
})