import http from "./http"

const getDepartment = () => {
	const path = '/staff/department'
	return http.get(path)
}

const addStaff = (realname, email, password, department_id) => {
	const path = "/staff/staff"
	return http.post(path, {realname, email, password, department_id})
}

const getStaffList = (page=1, size=10, params) => {
	const path = `staff/staff`
	params = params?params:{},
	params['page'] = page
	params['size'] = size
	return http.get(path, params)
}

const updateStaffStatus = (staff_id, status) => {
	const path = "/staff/staff/" + staff_id
	return http.put(path, {status})
}

const downloadStaffs = (pks) => {
	const path = "/staff/download"
	return http.downloadFile(path, {"pks": JSON.stringify(pks)})
}

export default{
	getDepartment,
	addStaff,
	getStaffList,
	updateStaffStatus,
	downloadStaffs
}