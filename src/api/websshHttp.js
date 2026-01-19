import http from "./http";

const checkConnect = (user, ip, password) => {
	const path = '/ssh/check'
	return http.post(path, {user, ip, password})
}

export default{
	checkConnect
}