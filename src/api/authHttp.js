import http from "./http";

const login = (email, password) => {
	const path = '/auth/login'
	return http.post(path, {email, password})
}

const resetPwd = (oldpwd, pwd1, pwd2) => {
	const path = '/auth/restpwd'
	return http.post(path, {oldpwd, pwd1, pwd2})
}

const getIdcRegion = () => {
	const path = '/idc/region'
	return http.get(path)
}

const putIdcregion = (index, address, username, username_phone, server_count) => {
	const path = '/idc/region/' + index + '/'
	return http.put(path, {address, username, server_count, username_phone})
}

const addIdc = (address, username, username_phone, server_count) => {
	const path = '/idc/region/'
	return http.post(path, {address, username, server_count, username_phone})
}

const getIdcServer = () => {
	const path = '/idc/server'
	return http.get(path)
}

const deleteIdcServer = (index) => {
	const path = 'idc/server/' + index + '/'
	return http.delete(path)
}

const addIdcServer = (ip, password, func, region) => {
	const path = 'idc/server/'
	return http.post(path, {ip, password, func, region})
}

const updateIdcServer = (id, scan_status) => {
	const path = 'idc/server/update/' + id + '/'
	return http.patch(path, {scan_status})
}

const monitorPost = (ip) => {
	const path = 'idc/server/monitor/'
	return http.post(path, {ip})
}

export default {
	login,
	resetPwd,
	getIdcRegion,
	putIdcregion,
	addIdc,
	getIdcServer,
	deleteIdcServer,
	addIdcServer,
	updateIdcServer,
	monitorPost
}





