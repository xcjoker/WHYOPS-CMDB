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
								class="filter-select" filterable @change="fetchDeployments">
								<el-option label="全部 (All)" value="all" />
								<el-option v-for="ns in namespaces" :key="ns" :label="ns" :value="ns" />
							</el-select>
						</div>

						<div class="right-panel">
							<el-input v-model="searchKeyword" placeholder="搜索 Deployment..." class="search-input"
								clearable size="large" :prefix-icon="Search" />
							<el-button size="large" :icon="Refresh" circle @click="fetchDeployments"
								class="refresh-btn" />
							<el-button type="primary" size="large" :icon="Plus" @click="handleCreate">
								创建部署
							</el-button>
						</div>
					</div>

					<el-table :data="filteredList" v-loading="loading" style="width: 100%"
						header-cell-class-name="table-header-custom" row-class-name="table-row-custom">

						<el-table-column label="" width="50" align="center">
							<template #default="{ row }">
								<el-tooltip :content="`${row.available} / ${row.replicas} Ready`" placement="right">
									<div :class="['status-dot', getStatusColor(row)]"></div>
								</el-tooltip>
							</template>
						</el-table-column>

						<el-table-column prop="name" label="名称" min-width="200" show-overflow-tooltip>
							<template #default="{ row }">
								<span class="pod-name">{{ row.name }}</span>
								<div class="sub-text">{{ row.namespace }}</div>
							</template>
						</el-table-column>

						<el-table-column label="副本数 (Ready/Desired)" width="180" align="center">
							<template #default="{ row }">
								<div class="replica-badge"
									:class="row.available === row.replicas ? 'is-success' : 'is-warning'">
									{{ row.available }} / {{ row.replicas }}
								</div>
								<div class="sub-text">Updated: {{ row.up_to_date }}</div>
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

						<el-table-column label="操作" width="200" fixed="right" align="center">
							<template #default="{ row }">
								<div class="action-box">
									<el-button link type="primary" size="small" @click="handleScaleDialog(row)">
										扩缩容
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
												<el-dropdown-item :icon="Document" @click="handleViewYaml(row)">查看
													YAML</el-dropdown-item>
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

			<el-dialog v-model="yamlDialogVisible" :title="`YAML: ${currentRaw?.name}`" width="60%" destroy-on-close>
				<el-input v-model="currentYaml" type="textarea" :rows="20" placeholder="Loading..."
					class="yaml-editor" />
				<template #footer>
					<span class="dialog-footer">
						<el-button @click="yamlDialogVisible = false">关闭</el-button>
						<el-button type="primary" @click="handleUpdateYaml">提交修改</el-button>
					</span>
				</template>
			</el-dialog>

			<el-dialog v-model="scaleDialogVisible" title="调整副本数 (Scale)" width="30%">
				<div style="text-align: center; padding: 20px;">
					<p class="mb-4">调整 Deployment <strong>{{ currentRaw?.name }}</strong> 的副本数量</p>
					<el-input-number v-model="scaleNum" :min="0" :max="50" label="副本数"></el-input-number>
				</div>
				<template #footer>
					<span class="dialog-footer">
						<el-button @click="scaleDialogVisible = false">取消</el-button>
						<el-button type="primary" @click="submitScale" :loading="scaleLoading">确认调整</el-button>
					</span>
				</template>
			</el-dialog>

			<el-dialog v-model="createDialogVisible" title="创建 Deployment" width="60%" destroy-on-close>
				<el-alert title="请编写标准的 Kubernetes Deployment YAML 配置" type="info" show-icon :closable="false"
					style="margin-bottom: 15px;" />
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
		ArrowDown,
		Document,
		Delete,
		RefreshRight
	} from '@element-plus/icons-vue'
	import {
		ElMessage,
		ElMessageBox,
		ElLoading
	} from 'element-plus'

	// 假设你已经在 workloadHttp 中封装好了 Deployment 相关的 API
	// 方法名对应: getDeployments, getDeploymentYaml, updateDeploymentYaml, createDeployment, deleteDeployment, scaleDeployment, restartDeployment
	import clusterHttp from '@/api/clusterHttp'
	import workloadHttp from '@/api/workloadHttp'
	import frame from "@/views/main/frame.vue"

	// --- 状态定义 ---
	const loading = ref(false)
	const clusterList = ref([])
	const deploymentList = ref([])
	const searchKeyword = ref('')
	const namespaces = ref([])
	const queryParams = reactive({
		cluster_id: null,
		namespace: 'all'
	})

	// YAML 相关
	const yamlDialogVisible = ref(false)
	const currentYaml = ref('')
	const currentRaw = ref(null)

	// Scale 相关
	const scaleDialogVisible = ref(false)
	const scaleNum = ref(1)
	const scaleLoading = ref(false)

	// Create 相关
	const createDialogVisible = ref(false)
	const createLoading = ref(false)
	const createYaml = ref('')

	const defaultDepTemplate = `apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
  namespace: default
  labels:
    app: nginx
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.14.2
        ports:
        - containerPort: 80
`

	// --- 计算属性 ---
	const filteredList = computed(() => {
		if (!searchKeyword.value) return deploymentList.value
		const lower = searchKeyword.value.toLowerCase()
		return deploymentList.value.filter(item => item.name.toLowerCase().includes(lower))
	})

	// --- 初始化 ---
	const initData = async () => {
		try {
			const res = await clusterHttp.getClusters()
			clusterList.value = res.results || res || []
			if (clusterList.value.length > 0) {
				queryParams.cluster_id = clusterList.value[0].id
				fetchNamespaces()
				fetchDeployments()
			}
		} catch (e) {
			ElMessage.error('初始化失败')
		}
	}

	const handleClusterChange = () => {
		fetchNamespaces()
		queryParams.namespace = 'all'
		fetchDeployments()
	}

	const fetchNamespaces = async () => {
		if (!queryParams.cluster_id) return
		const res = await clusterHttp.getClusterNamespace(queryParams.cluster_id)
		namespaces.value = res
	}

	const fetchDeployments = async () => {
		if (!queryParams.cluster_id) return
		loading.value = true
		try {
			// 调用后端 list 接口
			const res = await workloadHttp.getDeployments(queryParams.cluster_id, queryParams.namespace)
			deploymentList.value = res
			ElMessage.success('刷新成功')
		} catch (err) {
			ElMessage.error('获取列表失败: ' + err)
			deploymentList.value = []
		} finally {
			loading.value = false
		}
	}

	// --- 辅助逻辑 ---
	const getStatusColor = (row) => {
		if (row.replicas === 0) return 'bg-info'
		if (row.available === row.replicas) return 'bg-success'
		return 'bg-warning' // 副本数不一致，显示黄色警告
	}

	// --- YAML 操作 ---
	const handleViewYaml = async (row) => {
		currentRaw.value = row
		yamlDialogVisible.value = true
		currentYaml.value = 'Loading...'
		try {
			// 这里记得后端 API 路径里要区分是 pods 还是 deployments
			const res = await workloadHttp.getDeploymentYaml(queryParams.cluster_id, row.namespace, row.name)
			currentYaml.value = res.content
		} catch (e) {
			currentYaml.value = '# Error'
		}
	}

	const handleUpdateYaml = async () => {
		try {
			await ElMessageBox.confirm('确定更新 YAML 配置吗？', '警告', {
				type: 'warning'
			})
			const loadingInst = ElLoading.service({
				text: '正在更新...'
			})
			await workloadHttp.updateDeploymentYaml(queryParams.cluster_id, currentRaw.value.namespace, currentRaw
				.value.name, currentYaml.value)
			loadingInst.close()
			ElMessage.success('更新成功')
			yamlDialogVisible.value = false
			fetchDeployments()
		} catch (e) {
			if (e !== 'cancel') ElMessage.error('更新失败: ' + e)
		}
	}

	// --- 扩缩容 (Scale) ---
	const handleScaleDialog = (row) => {
		currentRaw.value = row
		scaleNum.value = row.replicas
		scaleDialogVisible.value = true
	}

	const submitScale = async () => {
		scaleLoading.value = true
		try {
			await workloadHttp.scaleDeployment(
				queryParams.cluster_id,
				currentRaw.value.namespace,
				currentRaw.value.name,
				scaleNum.value
			)
			ElMessage.success('扩缩容指令已发送')
			scaleDialogVisible.value = false
			setTimeout(fetchDeployments, 1000)
		} catch (e) {
			ElMessage.error(e)
		} finally {
			scaleLoading.value = false
		}
	}

	// --- 滚动重启 (Restart) ---
	const handleRestart = (row) => {
		ElMessageBox.confirm(`确定要重启 ${row.name} 吗？这将触发滚动更新。`, '重启确认', {
			type: 'warning'
		}).then(async () => {
			try {
				await workloadHttp.restartDeployment(queryParams.cluster_id, row.namespace, row.name)
				ElMessage.success('重启指令已发送')
				fetchDeployments()
			} catch (e) {
				ElMessage.error(e)
			}
		})
	}

	// --- 创建 & 删除 ---
	const handleCreate = () => {
		createYaml.value = defaultDepTemplate
		if (queryParams.namespace !== 'all') {
			createYaml.value = createYaml.value.replace('namespace: default', `namespace: ${queryParams.namespace}`)
		}
		createDialogVisible.value = true
	}

	const submitCreate = async () => {
		createLoading.value = true
		try {
			await workloadHttp.createDeployment(queryParams.cluster_id, createYaml.value)
			ElMessage.success('创建成功')
			createDialogVisible.value = false
			setTimeout(fetchDeployments, 1000)
		} catch (e) {
			ElMessage.error(e)
		} finally {
			createLoading.value = false
		}
	}

	const handleDelete = (row) => {
		ElMessageBox.confirm(`确认删除 Deployment: ${row.name}?`, '警告', {
			type: 'warning',
			confirmButtonClass: 'el-button--danger'
		}).then(async () => {
			await workloadHttp.deleteDeployment(queryParams.cluster_id, row.namespace, row.name)
			ElMessage.success('已删除')
			setTimeout(fetchDeployments, 1000)
		})
	}

	onMounted(() => {
		initData()
	})
</script>

<style scoped>
	/* 复用 Pod 页面的大部分样式，此处省略重复部分，只写新增/修改的 */
	.workload-container {
		padding: 24px;
		background-color: #f0f2f5;
		min-height: calc(100vh - 60px);
	}

	.main-card {
		border-radius: 8px;
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

	.filter-select {
		width: 200px;
		margin-right: 12px;
	}

	.ml-4 {
		margin-left: 24px;
	}

	.search-input {
		width: 240px;
		margin-right: 12px;
	}

	.refresh-btn {
		margin-right: 12px;
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

	/* 文本 */
	.pod-name {
		font-weight: 600;
		color: #409EFF;
		font-size: 14px;
	}

	.sub-text {
		font-size: 12px;
		color: #909399;
		margin-top: 4px;
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

	/* 副本数徽章 */
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

	.text-danger {
		color: #f56c6c;
	}

	.yaml-editor :deep(.el-textarea__inner) {
		font-family: 'Consolas', monospace;
		background-color: #f9fafc;
	}

	.mb-4 {
		margin-bottom: 16px;
	}

	.action-box {
		display: flex;
		justify-content: center;
		align-items: center;
		height: 100%;
		/* 撑满单元格高度 */
	}

	/* 修正 Dropdown 按钮内部文字和图标的对齐 */
	.dropdown-btn {
		display: flex;
		align-items: center;
	}
</style>