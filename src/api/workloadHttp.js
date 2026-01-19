import http from "./http";

const workloadHttp = {
	// 获取 Pod 列表 (包含资源使用率)
	getPods(clusterId, namespace = 'default') {
		// 对应后端 workload/views.py 中的 PodViewSet
		const path = "/workload/pods/"
		return http.get(path, {
			params: {
				cluster_id: clusterId,
				namespace: namespace
			}
		})
	},


	getPodYaml(clusterId, namespace, podName) {
		return http.get("/workload/pods/yaml/", {
			params: {
				cluster_id: clusterId,
				namespace: namespace,
				name: podName
			}
		})
	},

	updatePodYaml(clusterId, namespace, podName, yamlContent) {
		return http.put("/workload/pods/yaml/", {
			cluster_id: clusterId,
			namespace: namespace,
			name: podName,
			content: yamlContent
		})
	},

	getPodLogs(clusterId, namespace, podName, container = '') {
		return http.get("/workload/pods/logs/", {
			params: {
				cluster_id: clusterId,
				namespace: namespace,
				name: podName,
				container: container
			}
		})
	},

	getPodLogs(clusterId, namespace, podName, container = '') {
		return http.get("/workload/pods/logs/", {
			params: {
				cluster_id: clusterId,
				namespace: namespace,
				name: podName,
				container: container
			}
		})
	},

	deletePod(clusterId, namespace, podName) {
		// 路径拼上 Pod 名称
		const path = `/workload/pods/${podName}/`
		// 传参
		return http.delete(path, {
			cluster_id: clusterId,
			namespace: namespace
		})
	},

	createPod(clusterId, yamlContent) {
		return http.post("/workload/pods/", {
			cluster_id: clusterId,
			yaml: yamlContent
		})
	},

	deletePod(clusterId, namespace, podName) {
		const path = `/workload/pods/${podName}/`
		return http.delete(path, {
			cluster_id: clusterId,
			namespace: namespace
		})
	},

	getDeployments(clusterId, namespace = 'default') {
		return http.get("/workload/deployments/", {
			params: {
				cluster_id: clusterId,
				namespace: namespace
			}
		})
	},

	getDeploymentYaml(clusterId, namespace, name) {
		return http.get("/workload/deployments/yaml/", {
			params: {
				cluster_id: clusterId,
				namespace: namespace,
				name: name
			}
		})
	},

	updateDeploymentYaml(clusterId, namespace, name, yamlContent) {
		return http.put("/workload/deployments/yaml/", {
			cluster_id: clusterId,
			namespace: namespace,
			name: name,
			content: yamlContent
		})
	},

	createDeployment(clusterId, yamlContent) {
		return http.post("/workload/deployments/", {
			cluster_id: clusterId,
			yaml: yamlContent
		})
	},

	deleteDeployment(clusterId, namespace, name) {
		const path = `/workload/deployments/${name}/`
		return http.delete(path, {
			cluster_id: clusterId,
			namespace: namespace
		})
	},

	scaleDeployment(clusterId, namespace, name, replicas) {
		return http.post("/workload/deployments/scale/", {
			cluster_id: clusterId,
			namespace: namespace,
			name: name,
			replicas: replicas
		})
	},

	restartDeployment(clusterId, namespace, name) {
		return http.post("/workload/deployments/restart/", {
			cluster_id: clusterId,
			namespace: namespace,
			name: name
		})
	},


	getStatefulSets(clusterId, namespace = 'default') {
		return http.get("/workload/statefulsets/", {
			params: {
				cluster_id: clusterId,
				namespace: namespace
			}
		})
	},

	createStatefulSet(clusterId, yamlContent) {
		return http.post("/workload/statefulsets/", {
			cluster_id: clusterId,
			yaml: yamlContent
		})
	},

	deleteStatefulSet(clusterId, namespace, name) {
		const path = `/workload/statefulsets/${name}/`
		return http.delete(path, {
			cluster_id: clusterId,
			namespace: namespace
		})
	},

	getStatefulSetYaml(clusterId, namespace, name) {
		return http.get("/workload/statefulsets/yaml/", {
			params: {
				cluster_id: clusterId,
				namespace: namespace,
				name: name
			}
		})
	},

	updateStatefulSetYaml(clusterId, namespace, name, yamlContent) {
		return http.put("/workload/statefulsets/yaml/", {
			cluster_id: clusterId,
			namespace: namespace,
			name: name,
			content: yamlContent
		})
	},

	scaleStatefulSet(clusterId, namespace, name, replicas) {
		return http.post("/workload/statefulsets/scale/", {
			cluster_id: clusterId,
			namespace: namespace,
			name: name,
			replicas: replicas
		})
	},

	restartStatefulSet(clusterId, namespace, name) {
		return http.post("/workload/statefulsets/restart/", {
			cluster_id: clusterId,
			namespace: namespace,
			name: name
		})
	},

	getDaemonSets(clusterId, namespace = 'default') {
		return http.get("/workload/daemonsets/", {
			params: {
				cluster_id: clusterId,
				namespace: namespace
			}
		})
	},

	createDaemonSet(clusterId, yamlContent) {
		return http.post("/workload/daemonsets/", {
			cluster_id: clusterId,
			yaml: yamlContent
		})
	},

	deleteDaemonSet(clusterId, namespace, name) {
		const path = `/workload/daemonsets/${name}/`
		return http.delete(path, {
			cluster_id: clusterId,
			namespace: namespace
		})
	},

	getDaemonSetYaml(clusterId, namespace, name) {
		return http.get("/workload/daemonsets/yaml/", {
			params: {
				cluster_id: clusterId,
				namespace: namespace,
				name: name
			}
		})
	},

	updateDaemonSetYaml(clusterId, namespace, name, yamlContent) {
		return http.put("/workload/daemonsets/yaml/", {
			cluster_id: clusterId,
			namespace: namespace,
			name: name,
			content: yamlContent
		})
	},

	restartDaemonSet(clusterId, namespace, name) {
		return http.post("/workload/daemonsets/restart/", {
			cluster_id: clusterId,
			namespace: namespace,
			name: name
		})
	},


	getJobs(clusterId, namespace = 'default') {
		return http.get("/workload/jobs/", {
			params: {
				cluster_id: clusterId,
				namespace: namespace
			}
		})
	},

	createJob(clusterId, yamlContent) {
		return http.post("/workload/jobs/", {
			cluster_id: clusterId,
			yaml: yamlContent
		})
	},

	deleteJob(clusterId, namespace, name) {
		const path = `/workload/jobs/${name}/`
		return http.delete(path, {
			cluster_id: clusterId,
			namespace: namespace
		})
	},

	getJobYaml(clusterId, namespace, name) {
		return http.get("/workload/jobs/yaml/", {
			params: {
				cluster_id: clusterId,
				namespace: namespace,
				name: name
			}
		})
	},

	updateJobYaml(clusterId, namespace, name, yamlContent) {
		return http.put("/workload/jobs/yaml/", {
			cluster_id: clusterId,
			namespace: namespace,
			name: name,
			content: yamlContent
		})
	},

	// ================== CronJob 相关接口 ==================

	getCronJobs(clusterId, namespace = 'default') {
		return http.get("/workload/cronjobs/", {
			params: {
				cluster_id: clusterId,
				namespace: namespace
			}
		})
	},

	createCronJob(clusterId, yamlContent) {
		return http.post("/workload/cronjobs/", {
			cluster_id: clusterId,
			yaml: yamlContent
		})
	},

	deleteCronJob(clusterId, namespace, name) {
		const path = `/workload/cronjobs/${name}/`
		return http.delete(path, {
			cluster_id: clusterId,
			namespace: namespace
		})
	},

	getCronJobYaml(clusterId, namespace, name) {
		return http.get("/workload/cronjobs/yaml/", {
			params: {
				cluster_id: clusterId,
				namespace: namespace,
				name: name
			}
		})
	},

	updateCronJobYaml(clusterId, namespace, name, yamlContent) {
		return http.put("/workload/cronjobs/yaml/", {
			cluster_id: clusterId,
			namespace: namespace,
			name: name,
			content: yamlContent
		})
	},

	// 切换暂停状态
	toggleCronJobSuspend(clusterId, namespace, name, suspendStatus) {
		return http.post("/workload/cronjobs/toggle_suspend/", {
			cluster_id: clusterId,
			namespace: namespace,
			name: name,
			suspend: suspendStatus // true or false
		})
	}


}

export default workloadHttp