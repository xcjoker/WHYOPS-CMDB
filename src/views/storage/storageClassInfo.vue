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

							<el-alert title="StorageClass 是集群级别的存储模板" type="info" :closable="false" show-icon
								class="ml-4" style="width: auto; padding: 8px 16px;" />
						</div>

						<div class="right-panel">
							<el-input v-model="searchKeyword" placeholder="搜索 StorageClass..." class="search-input"
								clearable size="large" :prefix-icon="Search" />
							<el-button size="large" :icon="Refresh" circle @click="fetchData" class="refresh-btn" />

							<el-tooltip content="创建存储类" placement="top">
								<span>
									<el-button type="primary" size="large" :icon="Plus" @click="handleCreate">
										创建 SC
									</el-button>
								</span>
							</el-tooltip>
						</div>
					</div>

					<el-table :data="filteredList" v-loading="loading" style="width: 100%"
						header-cell-class-name="table-header-custom" row-class-name="table-row-custom">

						<el-table-column label="" width="50" align="center">
							<template #default>
								<el-icon color="#909399" size="18">
									<Box />
								</el-icon>
							</template>
						</el-table-column>

						<el-table-column prop="name" label="名称" min-width="180" show-overflow-tooltip>
							<template #default="{ row }">
								<span class="resource-name">{{ row.name }}</span>
							</template>
						</el-table-column>

						<el-table-column prop="provisioner" label="供应者 (Provisioner)" min-width="220"
							show-overflow-tooltip>
							<template #default="{ row }">
								<span class="code-text">{{ row.provisioner }}</span>
							</template>
						</el-table-column>

						<el-table-column label="回收策略" width="120" align="center">
							<template #default="{ row }">
								<el-tag :type="row.reclaim_policy === 'Delete' ? 'danger' : 'success'" effect="plain"
									size="small">
									{{ row.reclaim_policy }}
								</el-tag>
							</template>
						</el-table-column>

						<el-table-column label="绑定模式" width="180" align="center">
							<template #default="{ row }">
								<el-tag type="info" size="small">{{ row.binding_mode }}</el-tag>
							</template>
						</el-table-column>

						<el-table-column label="允许扩容" width="100" align="center">
							<template #default="{ row }">
								<el-icon v-if="row.allow_expansion" color="#67C23A" size="18">
									<CircleCheck />
								</el-icon>
								<el-icon v-else color="#909399" size="18">
									<CircleClose />
								</el-icon>
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

			<el-dialog v-model="createDialogVisible" title="创建 StorageClass" width="60%" top="5vh" destroy-on-close>
				<el-alert title="定义存储的供应方式 (Provisioner) 和行为" type="info" show-icon :closable="false" class="mb-4" />
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
		Box,
		CircleCheck,
		CircleClose
	} from '@element-plus/icons-vue'
	import {
		ElMessage,
		ElMessageBox,
		ElLoading
	} from 'element-plus'
	import clusterHttp from '@/api/clusterHttp'
	import storageHttp from '@/api/storageHttp'
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

	// 默认 SC 模板 (NFS Client 示例)
	const defaultScTemplate = `apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: nfs-client
provisioner: k8s-sigs.io/nfs-subdir-external-provisioner
parameters:
  archiveOnDelete: "false"
reclaimPolicy: Delete
allowVolumeExpansion: true
volumeBindingMode: Immediate
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
			const res = await storageHttp.getStorageClasses(queryParams.cluster_id)
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
		createYaml.value = defaultScTemplate
		createDialogVisible.value = true
	}

	const submitCreate = async () => {
		createLoading.value = true
		try {
			await storageHttp.createStorageClass(queryParams.cluster_id, createYaml.value)
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
			const res = await storageHttp.getStorageClassYaml(queryParams.cluster_id, row.name)
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
			await storageHttp.updateStorageClassYaml(queryParams.cluster_id, currentRaw.value.name, currentYaml
				.value)
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
		ElMessageBox.confirm(`确认删除 StorageClass: ${row.name}? 依赖此 SC 的 PVC 将无法创建新的 PV。`, '高危警告', {
			type: 'warning',
			confirmButtonClass: 'el-button--danger'
		}).then(async () => {
			await storageHttp.deleteStorageClass(queryParams.cluster_id, row.name)
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

	.code-text {
		font-family: 'Consolas', monospace;
		font-size: 12px;
		color: #606266;
		background: #f4f4f5;
		padding: 2px 4px;
		border-radius: 4px;
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