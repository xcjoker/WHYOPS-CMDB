import axios from "axios";
import {
	useAuthStore
} from "@/stores/auth";

class Http {
	constructor() {
		this.instance = axios.create({
			baseURL: import.meta.env.VITE_BASE_URL,
			timeout: 600000
		});

		this.instance.interceptors.request.use((config) => {
			const authStore = useAuthStore()
			const token = authStore.token
			if (token) {
				config.headers.Authorization = 'JWT ' + token
			} else {
				console.log('没有token')
			}
			return config
		})
	}

	post(path, data) {
		// return this.instance.post(path, data)
		return new Promise(async (resolve, reject) => {
			//axiox底层也是用的promise对象，在响应的状态码不是200时，调用reject，结果是外层函数会抛出异常
			try {
				console.log(path)
				console.log(data)
				let result = await this.instance.post(path, data)
				resolve(result.data)
			} catch (err) {
				try {
					let detail = err.response.data.detail
					reject(detail)
				} catch {
					reject('服务器错误!')
				}

			}
		})
	}

	get(path, config) {
		// ❌ 原来的写法：return this.instance.get(path, {params})
		// ✅ 修正后的写法：直接传递 config，不要再包一层 {params}
		return this.instance.get(path, config)
			.then((res) => {
				return res.data;
			})
			.catch((err) => {
				const detail = err.response ? err.response.data.detail : err.message;
				return Promise.reject(detail);
			});
	}

	put(path, data) {
		return new Promise(async (resolve, reject) => {
			try {
				console.log(data)
				let result = await this.instance.put(path, data)
				resolve(result.data)
			} catch (err) {
				let detail = err.response.data.detail
				reject(detail)
			}
		})
	}

	delete(path, params) {
		return new Promise(async (resolve, reject) => {
			try {
				// axios 的 delete 第二个参数是 config，params 需放在 config 里
				let result = await this.instance.delete(path, {
					params: params
				})
				resolve(result)
			} catch (err) {
				let detail = err.response.data.detail
				reject(detail)
			}
		})
	}

	// delete(path) {
	// 	return new Promise(async (resolve, reject) => {
	// 		try {
	// 			let result = await this.instance.delete(path)
	// 			//服务端的delete方法只是返回一个状态码，并没有数据，把result返回回去就可以了
	// 			resolve(result)
	// 		} catch (err) {
	// 			let detail = err.response.data.detail
	// 			reject(detail)
	// 		}
	// 	})
	// }

	patch(path, data) {
		return new Promise(async (resolve, reject) => {
			try {
				console.log(data);
				let result = await this.instance.patch(path, data); // 使用 patch 发送部分数据
				resolve(result.data);
			} catch (err) {
				let detail = err.response.data.detail // 获取错误详情，避免 undefined 错误
				reject(detail);
			}
		});
	}

	downloadFile(path, params) {
		return new Promise(async (resolve, reject) => {
			try {
				let result = await this.instance.get(path, {
					params: params || {},
					responseType: "blob"
				})
				resolve(result)
			} catch (err) {
				let detail = err.response.data.detail;
				reject(detail)
			}
		})
	}


}

export default new Http()