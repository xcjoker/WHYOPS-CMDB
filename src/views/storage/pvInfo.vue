<template>
	<frame>
		<div class="main-frame">
			<div class="workload-container">
				<el-card shadow="never" class="main-card">
					<div class="header-actions">
						<div class="left-panel">
							<span class="filter-label">集群：</span>
							<el-select v-model="queryParams.cluster_id" placeholder="请选择集群" size="large"
								class="filter-select" @change="fetchData">
								<el-option v-for="item in clusterList" :key="item.id" :label="item.name"
									:value="item.id" />
							</el-select>

							<el-alert title="PersistentVolume (PV) 是集群级别的存储资源" type="info" :closable="false" show-icon
								class="ml-4" style="width: auto; padding: 8px 16px;" />
						</div>

						<div class="right-panel">
							<el-input v-model="searchKeyword" placeholder="搜索 PV 名称..." class="search-input" clearable
								size="large" :prefix-icon="Search" />
							<el-button size="large" :icon="Refresh" circle @click="fetchData" class="refresh-btn" />

							<el-tooltip content="创建持久卷" placement="top">
								<span>
									<el-button type="primary" size="large" :icon="Plus" @click="handleCreate">
										创建 PV
									</el-button>
								</span>
							</el-tooltip>
						</div>
					</div>

					<el-table :data="filteredList" v-loading="loading" style="width: 100%"
						header-cell-class-name="table-header-custom" row-class-name="table-row-custom">

						<el-table-column label="" width="50" align="center">
							<template #default="{ row }">
								<el-tooltip :content="row.status" placement="right">
									<div :class="['status-dot', getStatusColor(row.status)]"></div>
								</el-tooltip>
							</template>
						</el-table-column>

						<el-table-column prop="name" label="名称" min-width="180" show-overflow-tooltip>
							<template #default="{ row }">
								<span class="resource-name">{{ row.name }}</span>
							</template>
						</el-table-column>

						<el-table-column label="容量" width="100">
							<template #default="{ row }">
								<span class="capacity-text">{{ row.capacity }}</span>
							</template>
						</el-table-column>

						<el-table-column label="Access Modes" width="140" show-overflow-tooltip>
							<template #default="{ row }">
								<el-tag v-for="mode in row.access_modes" :key="mode" size="small" type="info"
									class="mr-1">
									{{ getShortAccessMode(mode) }}
								</el-tag>
							</template>
						</el-table-column>

						<el-table-column prop="reclaim_policy" label="回收策略" width="120" align="center" />

						<el-table-column prop="status" label="状态" width="100" align="center">
							<template #default="{ row }">
								<el-tag :type="getStatusTagType(row.status)" effect="light"
									size="small">{{ row.status }}</el-tag>
							</template>
						</el-table-column>

						<el-table-column label="绑定 (Claim)" min-width="180" show-overflow-tooltip>
							<template #default="{ row }">
								<div class="sub-text" v-if="row.claim">{{ row.claim }}</div>
								<span v-else style="color: #909399;">--</span>
							</template>
						</el-table-column>

						<el-table-column prop="storage_class" label="StorageClass" width="140" show-overflow-tooltip />

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

			<el-dialog v-model="createDialogVisible" title="创建 PersistentVolume" width="60%" top="5vh" destroy-on-close>
				<el-alert title="PV 是集群资源，不属于任何 Namespace" type="warning" show-icon :closable="false" class="mb-4" />
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
		Coin
	} from '@element-plus/icons-vue'
	import {
		ElMessage,
		ElMessageBox,
		ElLoading
	} from 'element-plus'
	import clusterHttp from '@/api/clusterHttp'
	import storageHttp from '@/api/storageHttp' // 引入新的 API
	import frame from "@/views/main/frame.vue"

	// --- 状态 ---
	const loading = ref(false)
	const clusterList = ref([])
	const dataList = ref([])
	const searchKeyword = ref('')
	const queryParams = reactive({
		cluster_id: null
	})

	const yamlDialogVisible = ref(false)
	const currentYaml = ref('')
	const currentRaw = ref(null)

	const createDialogVisible = ref(false)
	const createLoading = ref(false)
	const createYaml = ref('')

	// 默认 PV 模板 (NFS 示例)
	const defaultPvTemplate = `apiVersion: v1
kind: PersistentVolume
metadata:
  name: pv-nfs-10g
spec:
  capacity:
    storage: 10Gi
  volumeMode: Filesystem
  accessModes:
    - ReadWriteMany
  persistentVolumeReclaimPolicy: Retain
  storageClassName: nfs-storage
  nfs:
    path: /data/k8s
    server: 192.168.1.100
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
				fetchData()
			}
		} catch (e) {
			ElMessage.error('初始化失败')
		}
	}

	const fetchData = async () => {
		if (!queryParams.cluster_id) return
		loading.value = true
		try {
			const res = await storageHttp.getPVs(queryParams.cluster_id)
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
	const getStatusColor = (status) => {
		switch (status) {
			case 'Bound':
				return 'bg-success';
			case 'Available':
				return 'bg-primary';
			case 'Released':
				return 'bg-warning';
			case 'Failed':
				return 'bg-danger';
			default:
				return 'bg-info';
		}
	}

	const getStatusTagType = (status) => {
		switch (status) {
			case 'Bound':
				return 'success';
			case 'Available':
				return 'primary';
			case 'Released':
				return 'warning';
			case 'Failed':
				return 'danger';
			default:
				return 'info';
		}
	}

	const getShortAccessMode = (mode) => {
		const map = {
			'ReadWriteOnce': 'RWO',
			'ReadOnlyMany': 'ROX',
			'ReadWriteMany': 'RWX',
			'ReadWriteOncePod': 'RWOP'
		}
		return map[mode] || mode
	}

	// --- 操作逻辑 ---
	const handleCreate = () => {
		createYaml.value = defaultPvTemplate
		createDialogVisible.value = true
	}

	const submitCreate = async () => {
		createLoading.value = true
		try {
			await storageHttp.createPV(queryParams.cluster_id, createYaml.value)
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
			const res = await storageHttp.getPVYaml(queryParams.cluster_id, row.name)
			currentYaml.value = res.content
		} catch (e) {
			currentYaml.value = '# Error'
		}
	}

	const handleUpdateYaml = async () => {
		let loadingInst = null
		try {
			await ElMessageBox.confirm('PV 的部分字段 (如 Capacity) 通常不可变。确定尝试更新吗？', '警告', {
				type: 'warning'
			})
			loadingInst = ElLoading.service({
				text: 'Updating...'
			})
			await storageHttp.updatePVYaml(queryParams.cluster_id, currentRaw.value.name, currentYaml.value)
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
		ElMessageBox.confirm(`确认删除 PV: ${row.name}? 数据可能会根据回收策略被删除。`, '高危警告', {
			type: 'warning',
			confirmButtonClass: 'el-button--danger'
		}).then(async () => {
			await storageHttp.deletePV(queryParams.cluster_id, row.name)
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

	.mr-1 {
		margin-right: 4px;
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

	.bg-primary {
		background-color: #409EFF;
		box-shadow: 0 0 4px rgba(64, 158, 255, 0.4);
	}

	.bg-warning {
		background-color: #e6a23c;
	}

	.bg-danger {
		background-color: #f56c6c;
	}

	.bg-info {
		background-color: #909399;
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

	.capacity-text {
		font-family: 'Consolas', monospace;
		font-weight: 600;
		color: #303133;
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