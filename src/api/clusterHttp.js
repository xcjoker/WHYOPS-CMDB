import http from "./http";


const clusterHttp = {
	// 1. 创建/导入集群
	createCluster(data) {
		const path = "/cluster/clusters/"
		return http.post(path, data)
	},

	// 2. 获取集群列表 (供 info 页面使用)
	getClusters() {
		const path = "/cluster/clusters/"
		return http.get(path)
	},

	// // 3. 获取单个集群详情
	// getClusterDetail(id) {
	//     return http.get(`${CLUSTER_API}${id}/`)
	// },

	// 4. 删除集群
	deleteCluster(id) {
		const path = "/cluster/clusters/" + id
		return http.delete(path)
	},

	syncClusterNodes(clusterId) {
		return http.post(`/cluster/clusters/${clusterId}/sync_nodes/`)
	},

	getClusterNodes(clusterId) {
		// 1. 路径改为基础路径 /nodes/ (对应后端 router.register(r'nodes', ...))
		// 注意：不要在路径后面拼接 ID
		const path = "/cluster/nodes/"

		// 2. 使用 params 传递过滤参数
		// axios 会自动将 params 拼接到 URL 后面，变成: /nodes/?cluster=3
		return http.get(path, {
			params: {
				cluster: clusterId
			}
		})
	},

	getDashboardStats(clusterId, namespace = '') {
		// 直接拼接到 clusters 路径后面
		const path = `/cluster/clusters/${clusterId}/dashboard/`

		return http.get(path, {
			params: {
				namespace: namespace // 支持传递 namespace 参数
			}
		})
	},
	getRecentEvents(clusterId, namespace = '') {
		const path = `/cluster/clusters/${clusterId}/events/`
		return http.get(path, {
			params: {
				namespace: namespace
			}
		})
	},
	getClusterNamespace(clusterId){
		const path = `/cluster/clusters/${clusterId}/get_namespaces/`
		return http.get(path)
	}
}

export default clusterHttp