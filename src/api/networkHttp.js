import http from "./http";

const networkHttp = {
	// ================== Service 相关接口 ==================

	getServices(clusterId, namespace = 'default') {
		return http.get("/network/services/", {
			params: {
				cluster_id: clusterId,
				namespace: namespace
			}
		})
	},

	createService(clusterId, yamlContent) {
		return http.post("/network/services/", {
			cluster_id: clusterId,
			yaml: yamlContent
		})
	},

	deleteService(clusterId, namespace, name) {
		const path = `/network/services/${name}/`
		return http.delete(path, {
			cluster_id: clusterId,
			namespace: namespace
		})
	},

	getServiceYaml(clusterId, namespace, name) {
		return http.get("/network/services/yaml/", {
			params: {
				cluster_id: clusterId,
				namespace: namespace,
				name: name
			}
		})
	},

	updateServiceYaml(clusterId, namespace, name, yamlContent) {
		return http.put("/network/services/yaml/", {
			cluster_id: clusterId,
			namespace: namespace,
			name: name,
			content: yamlContent
		})
	},
	
	// ================== Ingress 相关接口 ==================
	
		getIngresses(clusterId, namespace = 'default') {
			return http.get("/network/ingresses/", {
				params: { cluster_id: clusterId, namespace: namespace }
			})
		},
	
		createIngress(clusterId, yamlContent) {
			return http.post("/network/ingresses/", {
				cluster_id: clusterId,
				yaml: yamlContent
			})
		},
	
		deleteIngress(clusterId, namespace, name) {
			const path = `/network/ingresses/${name}/`
			return http.delete(path, { cluster_id: clusterId, namespace: namespace })
		},
	
		getIngressYaml(clusterId, namespace, name) {
			return http.get("/network/ingresses/yaml/", {
				params: { cluster_id: clusterId, namespace: namespace, name: name }
			})
		},
	
		updateIngressYaml(clusterId, namespace, name, yamlContent) {
			return http.put("/network/ingresses/yaml/", {
				cluster_id: clusterId, namespace: namespace, name: name, content: yamlContent
			})
		}
}

export default networkHttp