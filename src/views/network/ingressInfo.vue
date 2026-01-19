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
							<el-input v-model="searchKeyword" placeholder="搜索 Ingress..." class="search-input" clearable
								size="large" :prefix-icon="Search" />
							<el-button size="large" :icon="Refresh" circle @click="fetchData" class="refresh-btn" />

							<el-tooltip content="创建路由" placement="top">
								<span>
									<el-button type="primary" size="large" :icon="Plus" @click="handleCreate">
										创建 Ingress
									</el-button>
								</span>
							</el-tooltip>
						</div>
					</div>

					<el-table :data="filteredList" v-loading="loading" style="width: 100%"
						header-cell-class-name="table-header-custom" row-class-name="table-row-custom">

						<el-table-column label="" width="50" align="center">
							<template #default>
								<el-icon color="#67C23A" size="18">
									<Link />
								</el-icon>
							</template>
						</el-table-column>

						<el-table-column prop="name" label="名称" min-width="180" show-overflow-tooltip>
							<template #default="{ row }">
								<span class="resource-name">{{ row.name }}</span>
								<div class="sub-text">{{ row.namespace }}</div>
							</template>
						</el-table-column>

						<el-table-column label="地址 (Address)" width="160" show-overflow-tooltip>
							<template #default="{ row }">
								<div v-if="row.addresses && row.addresses.length > 0">
									<div v-for="(addr, i) in row.addresses" :key="i" class="address-text">
										{{ addr }}
									</div>
								</div>
								<span v-else class="sub-text">--</span>
							</template>
						</el-table-column>

						<el-table-column prop="class" label="Class" width="120" show-overflow-tooltip>
							<template #default="{ row }">
								<el-tag v-if="row.class" type="info" size="small"
									effect="plain">{{ row.class }}</el-tag>
							</template>
						</el-table-column>

						<el-table-column label="转发规则 (Rules)" min-width="200">
							<template #default="{ row }">
								<el-popover placement="top" :width="400" trigger="hover">
									<template #default>
										<div class="rules-container">
											<div v-for="(rule, idx) in row.rules" :key="idx" class="rule-item">
												<div class="rule-host">
													<el-icon>
														<Monitor />
													</el-icon> Host: <strong>{{ rule.host }}</strong>
												</div>
												<div v-for="(path, pIdx) in rule.paths" :key="pIdx" class="rule-path">
													<span class="path-url">{{ path.path }}</span>
													<el-icon class="mx-2">
														<Right />
													</el-icon>
													<span class="path-backend">{{ path.backend }}</span>
												</div>
											</div>
										</div>
									</template>
									<template #reference>
										<el-tag effect="light" round style="cursor: pointer">
											{{ row.rules.length }} 个 host 规则
										</el-tag>
									</template>
								</el-popover>
								<div v-if="row.rules.length > 0" class="sub-text mt-1">
									{{ row.rules[0].host }} ...
								</div>
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

			<el-dialog v-model="createDialogVisible" title="创建 Ingress" width="60%" top="5vh" destroy-on-close>
				<el-alert title="请确保集群已安装 Ingress Controller (如 Nginx)" type="warning" show-icon :closable="false"
					class="mb-4" />
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
		Link,
		Monitor,
		Right
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

	// 默认 Ingress 模板 (V1)
	const defaultIngTemplate = `apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-ingress
  namespace: default
spec:
  ingressClassName: nginx
  rules:
  - host: example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: my-service
            port:
              number: 80
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
			const res = await networkHttp.getIngresses(queryParams.cluster_id, queryParams.namespace)
			dataList.value = res
			ElMessage.success('列表已刷新')
		} catch (err) {
			ElMessage.error('获取列表失败: ' + err)
			dataList.value = []
		} finally {
			loading.value = false
		}
	}

	// --- 操作逻辑 ---
	const handleCreate = () => {
		createYaml.value = defaultIngTemplate
		if (queryParams.namespace !== 'all') {
			createYaml.value = createYaml.value.replace(/namespace: default/g, `namespace: ${queryParams.namespace}`)
		}
		createDialogVisible.value = true
	}

	const submitCreate = async () => {
		createLoading.value = true
		try {
			await networkHttp.createIngress(queryParams.cluster_id, createYaml.value)
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
			const res = await networkHttp.getIngressYaml(queryParams.cluster_id, row.namespace, row.name)
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
			await networkHttp.updateIngressYaml(queryParams.cluster_id, currentRaw.value.namespace, currentRaw
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
		ElMessageBox.confirm(`确认删除 Ingress: ${row.name}?`, '高危警告', {
			type: 'warning',
			confirmButtonClass: 'el-button--danger'
		}).then(async () => {
			await networkHttp.deleteIngress(queryParams.cluster_id, row.namespace, row.name)
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

	.address-text {
		font-family: 'Consolas', monospace;
		color: #67C23A;
		font-weight: 500;
	}

	.mt-1 {
		margin-top: 4px;
	}

	.mx-2 {
		margin: 0 8px;
	}

	/* 规则 Popover 样式 */
	.rules-container {
		max-height: 300px;
		overflow-y: auto;
	}

	.rule-item {
		margin-bottom: 12px;
		padding-bottom: 12px;
		border-bottom: 1px dashed #ebeef5;
	}

	.rule-item:last-child {
		border-bottom: none;
	}

	.rule-host {
		font-size: 13px;
		color: #303133;
		margin-bottom: 6px;
		display: flex;
		align-items: center;
	}

	.rule-path {
		display: flex;
		align-items: center;
		font-size: 12px;
		color: #606266;
		padding-left: 20px;
		margin-bottom: 4px;
	}

	.path-url {
		color: #409EFF;
	}

	.path-backend {
		font-family: 'Consolas', monospace;
		background-color: #f4f4f5;
		padding: 1px 4px;
		border-radius: 3px;
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