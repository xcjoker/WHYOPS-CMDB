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
							<el-input v-model="searchKeyword" placeholder="搜索 DaemonSet..." class="search-input"
								clearable size="large" :prefix-icon="Search" />
							<el-button size="large" :icon="Refresh" circle @click="fetchData" class="refresh-btn" />

							<el-tooltip content="创建新的 DaemonSet" placement="top">
								<span>
									<el-button type="primary" size="large" :icon="Plus" @click="handleCreate">
										创建守护进程
									</el-button>
								</span>
							</el-tooltip>
						</div>
					</div>

					<el-table :data="filteredList" v-loading="loading" style="width: 100%"
						header-cell-class-name="table-header-custom" row-class-name="table-row-custom">

						<el-table-column label="" width="50" align="center">
							<template #default="{ row }">
								<el-tooltip :content="`${row.ready} / ${row.desired} Ready`" placement="right">
									<div :class="['status-dot', getStatusColor(row)]"></div>
								</el-tooltip>
							</template>
						</el-table-column>

						<el-table-column prop="name" label="名称" min-width="200" show-overflow-tooltip>
							<template #default="{ row }">
								<span class="resource-name">{{ row.name }}</span>
								<div class="sub-text">{{ row.namespace }}</div>
							</template>
						</el-table-column>

						<el-table-column label="调度情况 (Ready/Desired)" width="220" align="center">
							<template #default="{ row }">
								<div class="replica-badge"
									:class="row.ready === row.desired ? 'is-success' : 'is-warning'">
									{{ row.ready }} / {{ row.desired }}
								</div>
								<div class="sub-text">Nodes Scheduled</div>
							</template>
						</el-table-column>

						<el-table-column label="镜像" min-width="220" show-overflow-tooltip>
							<template #default="{ row }">
								<div v-for="(img, idx) in row.images" :key="idx" class="image-tag">
									{{ img }}
								</div>
							</template>
						</el-table-column>

						<el-table-column prop="age" label="存活时间" width="100" align="center" />

						<el-table-column label="操作" width="180" fixed="right" align="center">
							<template #default="{ row }">
								<div class="action-box">
									<el-button link type="primary" size="small" :icon="Document"
										@click="handleViewYaml(row)">
										YAML
									</el-button>

									<el-divider direction="vertical" />

									<el-dropdown trigger="click">
										<el-button link type="primary" size="small" class="dropdown-btn">
											更多 <el-icon class="el-icon--right">
												<ArrowDown />
											</el-icon>
										</el-button>
										<template #dropdown>
											<el-dropdown-menu>
												<el-dropdown-item :icon="RefreshRight"
													@click="handleRestart(row)">滚动重启</el-dropdown-item>
												<el-dropdown-item divided :icon="Delete" class="text-danger"
													@click="handleDelete(row)">
													删除
												</el-dropdown-item>
											</el-dropdown-menu>
										</template>
									</el-dropdown>
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

			<el-dialog v-model="createDialogVisible" title="创建 DaemonSet" width="60%" top="5vh" destroy-on-close>
				<el-alert title="DaemonSet 将在所有(或符合条件的)节点上运行一个副本" type="info" show-icon :closable="false"
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
	// Grid 图标很适合 DaemonSet (矩阵/网络)
	import {
		Search,
		Refresh,
		Plus,
		ArrowDown,
		Document,
		Delete,
		RefreshRight,
		Grid
	} from '@element-plus/icons-vue'
	import {
		ElMessage,
		ElMessageBox,
		ElLoading
	} from 'element-plus'
	import clusterHttp from '@/api/clusterHttp'
	import workloadHttp from '@/api/workloadHttp'
	import frame from "@/views/main/frame.vue"

	// --- 状态定义 ---
	const loading = ref(false)
	const clusterList = ref([])
	const dataList = ref([])
	const namespaces = ref([])
	const searchKeyword = ref('')
	const queryParams = reactive({
		cluster_id: null,
		namespace: 'all'
	})

	// 弹窗相关
	const yamlDialogVisible = ref(false)
	const currentYaml = ref('')
	const currentRaw = ref(null)

	const createDialogVisible = ref(false)
	const createLoading = ref(false)
	const createYaml = ref('')

	// 默认 DaemonSet 模板
	const defaultDsTemplate = `apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: node-exporter-daemon
  namespace: default
  labels:
    app: node-exporter
spec:
  selector:
    matchLabels:
      app: node-exporter
  template:
    metadata:
      labels:
        app: node-exporter
    spec:
      tolerations:
      # 允许在 Master 节点运行
      - key: node-role.kubernetes.io/control-plane
        operator: Exists
        effect: NoSchedule
      containers:
      - name: node-exporter
        image: prom/node-exporter:latest
        ports:
        - containerPort: 9100
          hostPort: 9100
`

	// --- 计算属性 ---
	const filteredList = computed(() => {
		if (!searchKeyword.value) return dataList.value
		const lower = searchKeyword.value.toLowerCase()
		return dataList.value.filter(item => item.name.toLowerCase().includes(lower))
	})

	// --- 初始化 ---
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
			const res = await workloadHttp.getDaemonSets(queryParams.cluster_id, queryParams.namespace)
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
	const getStatusColor = (row) => {
		// DaemonSet: Desired 代表应该运行的节点数
		if (row.desired === 0) return 'bg-info'
		if (row.ready >= row.desired) return 'bg-success'
		return 'bg-warning'
	}

	// --- 操作逻辑 ---
	const handleCreate = () => {
		createYaml.value = defaultDsTemplate
		if (queryParams.namespace !== 'all') {
			createYaml.value = createYaml.value.replace(/namespace: default/g, `namespace: ${queryParams.namespace}`)
		}
		createDialogVisible.value = true
	}

	const submitCreate = async () => {
		createLoading.value = true
		try {
			await workloadHttp.createDaemonSet(queryParams.cluster_id, createYaml.value)
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
			const res = await workloadHttp.getDaemonSetYaml(queryParams.cluster_id, row.namespace, row.name)
			currentYaml.value = res.content
		} catch (e) {
			currentYaml.value = '# Error'
		}
	}

	// daemonsetInfo.vue

	const handleUpdateYaml = async () => {
		// 定义 loading 实例变量，以便在 finally 中关闭
		let loadingInst = null

		try {
			await ElMessageBox.confirm('确定更新配置吗？', '警告', {
				type: 'warning'
			})

			// 开启 Loading
			loadingInst = ElLoading.service({
				text: 'Updating...'
			})

			// 调用接口
			await workloadHttp.updateDaemonSetYaml(
				queryParams.cluster_id,
				currentRaw.value.namespace,
				currentRaw.value.name,
				currentYaml.value
			)

			ElMessage.success('更新成功')
			yamlDialogVisible.value = false // 成功才关闭弹窗
			fetchData() // 刷新列表

		} catch (e) {
			// 如果是用户点击了“取消”按钮，e 会是 'cancel'，不报错
			if (e !== 'cancel') {
				ElMessage.error('更新失败: ' + e)
				// 失败时【不要】关闭弹窗 (yamlDialogVisible.value = false)，
				// 这样用户可以根据错误提示修改 YAML
			}
		} finally {
			// 【关键修复】无论成功还是失败，只要 loading 实例存在，就强制关闭
			if (loadingInst) {
				loadingInst.close()
			}
		}
	}

	const handleRestart = (row) => {
		ElMessageBox.confirm(`确定要重启 ${row.name} 吗？`, '确认', {
			type: 'warning'
		}).then(async () => {
			try {
				await workloadHttp.restartDaemonSet(queryParams.cluster_id, row.namespace, row.name)
				ElMessage.success('重启指令已发送')
			} catch (e) {
				ElMessage.error(e)
			}
		})
	}

	const handleDelete = (row) => {
		ElMessageBox.confirm(`确认删除 ${row.name}?`, '高危警告', {
			type: 'warning',
			confirmButtonClass: 'el-button--danger'
		}).then(async () => {
			await workloadHttp.deleteDaemonSet(queryParams.cluster_id, row.namespace, row.name)
			ElMessage.success('删除成功')
			setTimeout(fetchData, 1000)
		})
	}

	onMounted(() => {
		initData()
	})
</script>

<style scoped>
	/* 复用之前的样式，保持一致性 */
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

	/* 状态点 */
	.status-dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		margin: 0 auto;
	}

	.bg-success {
		background-color: #67c23a;
		box-shadow: 0 0 4px rgba(103, 194, 58, 0.4);
	}

	.bg-warning {
		background-color: #e6a23c;
	}

	.bg-info {
		background-color: #909399;
	}

	/* 表格内容 */
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

	.image-tag {
		background: #ecf5ff;
		color: #409eff;
		border: 1px solid #d9ecff;
		border-radius: 4px;
		padding: 2px 6px;
		font-size: 12px;
		margin-bottom: 2px;
		display: inline-block;
	}

	.replica-badge {
		display: inline-block;
		padding: 2px 10px;
		border-radius: 12px;
		font-size: 13px;
		font-weight: 500;
	}

	.replica-badge.is-success {
		background-color: #f0f9eb;
		color: #67c23a;
	}

	.replica-badge.is-warning {
		background-color: #fdf6ec;
		color: #e6a23c;
	}

	/* Flex 修复 */
	.action-box {
		display: flex;
		justify-content: center;
		align-items: center;
		height: 100%;
	}

	.dropdown-btn {
		display: flex;
		align-items: center;
	}

	.text-danger {
		color: #f56c6c;
	}

	.yaml-editor :deep(.el-textarea__inner) {
		font-family: 'Consolas', monospace;
		background-color: #f9fafc;
	}
</style>