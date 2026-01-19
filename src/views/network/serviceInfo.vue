<template>
	<frame>
		<div class="main-frame">
			<div class="workload-container">
				<el-card shadow="never" class="main-card">
					<div class="header-actions">
						<div class="left-panel">
							<span class="filter-label">集群：</span>
							<el-select v-model="queryParams.cluster_id" placeholder="请选择集群" size="large"
								class="filter-select" @change="handleClusterChange">
								<el-option v-for="item in clusterList" :key="item.id" :label="item.name"
									:value="item.id" />
							</el-select>

							<span class="filter-label ml-4">命名空间：</span>
							<el-select v-model="queryParams.namespace" placeholder="Namespace" size="large"
								class="filter-select" filterable @change="fetchData">
								<el-option label="全部 (All)" value="all" />
								<el-option v-for="ns in namespaces" :key="ns" :label="ns" :value="ns" />
							</el-select>
						</div>

						<div class="right-panel">
							<el-input v-model="searchKeyword" placeholder="搜索 Service..." class="search-input" clearable
								size="large" :prefix-icon="Search" />
							<el-button size="large" :icon="Refresh" circle @click="fetchData" class="refresh-btn" />

							<el-tooltip content="创建网络服务" placement="top">
								<span>
									<el-button type="primary" size="large" :icon="Plus" @click="handleCreate">
										创建 Service
									</el-button>
								</span>
							</el-tooltip>
						</div>
					</div>

					<el-table :data="filteredList" v-loading="loading" style="width: 100%"
						header-cell-class-name="table-header-custom" row-class-name="table-row-custom">

						<el-table-column label="" width="50" align="center">
							<template #default>
								<el-icon color="#409EFF" size="18">
									<Connection />
								</el-icon>
							</template>
						</el-table-column>

						<el-table-column prop="name" label="名称" min-width="180" show-overflow-tooltip>
							<template #default="{ row }">
								<span class="resource-name">{{ row.name }}</span>
								<div class="sub-text">{{ row.namespace }}</div>
							</template>
						</el-table-column>

						<el-table-column label="类型 (Type)" width="140" align="center">
							<template #default="{ row }">
								<el-tag :type="getTypeTag(row.type)" effect="plain" size="small">{{ row.type }}</el-tag>
							</template>
						</el-table-column>

						<el-table-column prop="cluster_ip" label="Cluster IP" width="140" show-overflow-tooltip />

						<el-table-column label="端口 (Port:Target/Node)" min-width="180">
							<template #default="{ row }">
								<el-tag v-for="(port, idx) in row.ports" :key="idx" size="small" type="info"
									class="port-tag">
									{{ port }}
								</el-tag>
							</template>
						</el-table-column>

						<el-table-column label="External IP" width="140" show-overflow-tooltip>
							<template #default="{ row }">
								<div v-if="row.external_ips && row.external_ips.length > 0">
									<div v-for="(ip, idx) in row.external_ips" :key="idx" class="sub-text"
										style="color:#67C23A">
										{{ ip }}
									</div>
								</div>
								<span v-else class="sub-text">--</span>
							</template>
						</el-table-column>

						<el-table-column label="选择器 (Selector)" width="180" show-overflow-tooltip>
							<template #default="{ row }">
								<div v-if="row.selector && row.selector.length > 0">
									<span v-for="(s, i) in row.selector" :key="i" class="selector-item">{{ s }}</span>
								</div>
								<span v-else class="sub-text">None</span>
							</template>
						</el-table-column>

						<el-table-column prop="age" label="存活时间" width="100" align="center" />

						<el-table-column label="操作" width="160" fixed="right" align="center">
							<template #default="{ row }">
								<div class="action-box">
									<el-button link type="primary" size="small" :icon="Document"
										@click="handleViewYaml(row)">
										YAML
									</el-button>
									<el-divider direction="vertical" />
									<el-button link type="danger" size="small" :icon="Delete"
										@click="handleDelete(row)">
										删除
									</el-button>
								</div>
							</template>
						</el-table-column>
					</el-table>
				</el-card>
			</div>

			<el-dialog v-model="yamlDialogVisible" :title="`YAML: ${currentRaw?.name}`" width="60%" top="5vh"
				destroy-on-close>
				<el-input v-model="currentYaml" type="textarea" :rows="20" placeholder="Loading..."
					class="yaml-editor" />
				<template #footer>
					<span class="dialog-footer">
						<el-button @click="yamlDialogVisible = false">关闭</el-button>
						<el-button type="primary" @click="handleUpdateYaml">提交修改</el-button>
					</span>
				</template>
			</el-dialog>

			<el-dialog v-model="createDialogVisible" title="创建 Service" width="60%" top="5vh" destroy-on-close>
				<el-alert title="Service 用于暴露一组 Pod 的网络访问" type="info" show-icon :closable="false" class="mb-4" />
				<el-input v-model="createYaml" type="textarea" :rows="20" class="yaml-editor" spellcheck="false" />
				<template #footer>
					<span class="dialog-footer">
						<el-button @click="createDialogVisible = false">取消</el-button>
						<el-button type="primary" @click="submitCreate" :loading="createLoading">确认创建</el-button>
					</span>
				</template>
			</el-dialog>
		</div>
	</frame>
</template>

<script setup>
	import {
		ref,
		reactive,
		onMounted,
		computed
	} from 'vue'
	import {
		Search,
		Refresh,
		Plus,
		Document,
		Delete,
		Connection
	} from '@element-plus/icons-vue'
	import {
		ElMessage,
		ElMessageBox,
		ElLoading
	} from 'element-plus'
	import clusterHttp from '@/api/clusterHttp'
	import networkHttp from '@/api/networkHttp'
	import frame from "@/views/main/frame.vue"

	// --- 状态 ---
	const loading = ref(false)
	const clusterList = ref([])
	const dataList = ref([])
	const namespaces = ref([])
	const searchKeyword = ref('')
	const queryParams = reactive({
		cluster_id: null,
		namespace: 'all'
	})

	const yamlDialogVisible = ref(false)
	const currentYaml = ref('')
	const currentRaw = ref(null)

	const createDialogVisible = ref(false)
	const createLoading = ref(false)
	const createYaml = ref('')

	// 默认 Service 模板 (ClusterIP 示例)
	const defaultSvcTemplate = `apiVersion: v1
kind: Service
metadata:
  name: my-service
  namespace: default
spec:
  selector:
    app: my-app
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8080
  type: ClusterIP
`

	const filteredList = computed(() => {
		if (!searchKeyword.value) return dataList.value
		const lower = searchKeyword.value.toLowerCase()
		return dataList.value.filter(item => item.name.toLowerCase().includes(lower))
	})

	const initData = async () => {
		try {
			const res = await clusterHttp.getClusters()
			clusterList.value = res.results || res || []
			if (clusterList.value.length > 0) {
				queryParams.cluster_id = clusterList.value[0].id
				fetchNamespaces()
				fetchData()
			}
		} catch (e) {
			ElMessage.error('初始化失败')
		}
	}

	const handleClusterChange = () => {
		fetchNamespaces()
		queryParams.namespace = 'all'
		fetchData()
	}

	const fetchNamespaces = async () => {
		if (!queryParams.cluster_id) return
		const res = await clusterHttp.getClusterNamespace(queryParams.cluster_id)
		namespaces.value = res
	}

	const fetchData = async () => {
		if (!queryParams.cluster_id) return
		loading.value = true
		try {
			const res = await networkHttp.getServices(queryParams.cluster_id, queryParams.namespace)
			dataList.value = res
			ElMessage.success('列表已刷新')
		} catch (err) {
			ElMessage.error('获取列表失败: ' + err)
			dataList.value = []
		} finally {
			loading.value = false
		}
	}

	// --- 样式逻辑 ---
	const getTypeTag = (type) => {
		switch (type) {
			case 'ClusterIP':
				return ''; // 默认蓝
			case 'NodePort':
				return 'warning';
			case 'LoadBalancer':
				return 'success';
			case 'ExternalName':
				return 'info';
			default:
				return 'info';
		}
	}

	// --- 操作逻辑 ---
	const handleCreate = () => {
		createYaml.value = defaultSvcTemplate
		if (queryParams.namespace !== 'all') {
			createYaml.value = createYaml.value.replace(/namespace: default/g, `namespace: ${queryParams.namespace}`)
		}
		createDialogVisible.value = true
	}

	const submitCreate = async () => {
		createLoading.value = true
		try {
			await networkHttp.createService(queryParams.cluster_id, createYaml.value)
			ElMessage.success('创建成功')
			createDialogVisible.value = false
			setTimeout(fetchData, 1000)
		} catch (e) {
			ElMessage.error(e)
		} finally {
			createLoading.value = false
		}
	}

	const handleViewYaml = async (row) => {
		currentRaw.value = row
		yamlDialogVisible.value = true
		currentYaml.value = 'Loading...'
		try {
			const res = await networkHttp.getServiceYaml(queryParams.cluster_id, row.namespace, row.name)
			currentYaml.value = res.content
		} catch (e) {
			currentYaml.value = '# Error'
		}
	}

	const handleUpdateYaml = async () => {
		let loadingInst = null
		try {
			await ElMessageBox.confirm('确定更新 YAML 配置吗？', '警告', {
				type: 'warning'
			})
			loadingInst = ElLoading.service({
				text: 'Updating...'
			})
			await networkHttp.updateServiceYaml(queryParams.cluster_id, currentRaw.value.namespace, currentRaw
				.value.name, currentYaml.value)
			ElMessage.success('更新成功')
			yamlDialogVisible.value = false
			fetchData()
		} catch (e) {
			if (e !== 'cancel') ElMessage.error('更新失败: ' + e)
		} finally {
			if (loadingInst) loadingInst.close()
		}
	}

	const handleDelete = (row) => {
		ElMessageBox.confirm(`确认删除 Service: ${row.name}?`, '高危警告', {
			type: 'warning',
			confirmButtonClass: 'el-button--danger'
		}).then(async () => {
			await networkHttp.deleteService(queryParams.cluster_id, row.namespace, row.name)
			ElMessage.success('删除成功')
			setTimeout(fetchData, 1000)
		})
	}

	onMounted(() => {
		initData()
	})
</script>

<style scoped>
	.workload-container {
		padding: 24px;
		background-color: #f0f2f5;
		min-height: calc(100vh - 60px);
	}

	.main-card {
		border-radius: 8px;
		border: none;
	}

	.header-actions {
		display: flex;
		justify-content: space-between;
		margin-bottom: 24px;
	}

	.left-panel,
	.right-panel {
		display: flex;
		align-items: center;
	}

	.filter-label {
		font-size: 14px;
		font-weight: 500;
		color: #606266;
		margin-right: 8px;
	}

	.filter-select {
		width: 200px;
	}

	.search-input {
		width: 240px;
		margin-right: 12px;
	}

	.refresh-btn {
		margin-right: 12px;
	}

	.ml-4 {
		margin-left: 24px;
	}

	.mb-4 {
		margin-bottom: 16px;
	}

	.resource-name {
		font-weight: 600;
		color: #409EFF;
		font-size: 14px;
	}

	.sub-text {
		font-size: 12px;
		color: #909399;
		margin-top: 4px;
		line-height: 1.2;
	}

	/* 端口 Tag 样式 */
	.port-tag {
		margin-right: 4px;
		margin-bottom: 2px;
		font-family: 'Consolas', monospace;
	}

	.selector-item {
		display: inline-block;
		background-color: #f4f4f5;
		border-radius: 4px;
		padding: 2px 6px;
		font-size: 12px;
		color: #606266;
		margin-right: 4px;
		margin-bottom: 2px;
	}

	.action-box {
		display: flex;
		justify-content: center;
		align-items: center;
		height: 100%;
	}

	.yaml-editor :deep(.el-textarea__inner) {
		font-family: 'Consolas', monospace;
		background-color: #f9fafc;
	}
</style>