import http from "./http";

const getDepartmentStaffCount = () => {
	const path = "home/department/staff/count";
	return http.get(path);
}

const getLatestInforms = () => {
	const path = "/home/latest/inform"
	return http.get(path)
}

const getIDC = () => {
	const path = "/home/latest/idc"
	return http.get(path)
}

const getClusters = () => {
	const path = "/cluster/clusters/"
	return http.get(path)
}

const getIdcServer = () => {
	const path = '/idc/server'
	return http.get(path)
}

const getIdcRegion = () => {
	const path = '/idc/region/' 
	return http.get(path)
}

const getInformList = (page=1) => {
	const path = "/inform/inform?page=" + page
	return http.get(path)
}
export default {
	getDepartmentStaffCount,
	getLatestInforms,
	getIDC,
	getClusters,
	getIdcServer,
	getIdcRegion,
	getInformList
};