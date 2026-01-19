import http from "./http";

const storageHttp = {
	// ================== PV 相关接口 ==================
	getPVs(clusterId) {
		return http.get("/storage/pvs/", {
			params: {
				cluster_id: clusterId
			}
		})
	},

	createPV(clusterId, yamlContent) {
		return http.post("/storage/pvs/", {
			cluster_id: clusterId,
			yaml: yamlContent
		})
	},

	deletePV(clusterId, name) {
		const path = `/storage/pvs/${name}/`
		return http.delete(path, {
			cluster_id: clusterId
		})
	},

	getPVYaml(clusterId, name) {
		return http.get("/storage/pvs/yaml/", {
			params: {
				cluster_id: clusterId,
				name: name
			}
		})
	},

	updatePVYaml(clusterId, name, yamlContent) {
		return http.put("/storage/pvs/yaml/", {
			cluster_id: clusterId,
			name: name,
			content: yamlContent
		})
	},

	// ================== PVC 相关接口 ==================

	getPVCs(clusterId, namespace = 'default') {
		return http.get("/storage/pvcs/", {
			params: {
				cluster_id: clusterId,
				namespace: namespace
			}
		})
	},

	createPVC(clusterId, yamlContent) {
		return http.post("/storage/pvcs/", {
			cluster_id: clusterId,
			yaml: yamlContent
		})
	},

	deletePVC(clusterId, namespace, name) {
		const path = `/storage/pvcs/${name}/`
		return http.delete(path, {
			cluster_id: clusterId,
			namespace: namespace
		})
	},

	getPVCYaml(clusterId, namespace, name) {
		return http.get("/storage/pvcs/yaml/", {
			params: {
				cluster_id: clusterId,
				namespace: namespace,
				name: name
			}
		})
	},

	updatePVCYaml(clusterId, namespace, name, yamlContent) {
		return http.put("/storage/pvcs/yaml/", {
			cluster_id: clusterId,
			namespace: namespace,
			name: name,
			content: yamlContent
		})
	},

	// ================== StorageClass 相关接口 ==================

	getStorageClasses(clusterId) {
		return http.get("/storage/storageclasses/", {
			params: {
				cluster_id: clusterId
			}
		})
	},

	createStorageClass(clusterId, yamlContent) {
		return http.post("/storage/storageclasses/", {
			cluster_id: clusterId,
			yaml: yamlContent
		})
	},

	deleteStorageClass(clusterId, name) {
		const path = `/storage/storageclasses/${name}/`
		return http.delete(path, {
			cluster_id: clusterId
		})
	},

	getStorageClassYaml(clusterId, name) {
		return http.get("/storage/storageclasses/yaml/", {
			params: {
				cluster_id: clusterId,
				name: name
			}
		})
	},

	updateStorageClassYaml(clusterId, name, yamlContent) {
		return http.put("/storage/storageclasses/yaml/", {
			cluster_id: clusterId,
			name: name,
			content: yamlContent
		})
	}
}

export default storageHttp