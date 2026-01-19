<template>
	<frame>
		<div class="main-frame">
			<div class="cluster-container">
				<el-card shadow="never" class="main-card">
					<div class="header-actions">
						<div class="left-panel">
							<el-button type="primary" size="large" :icon="Plus" @click="handleCreate"
								class="create-btn">
								导入集群
							</el-button>
						</div>
						<div class="right-panel">
							<el-input v-model="queryParams.search" placeholder="请输入完整的集群名称..." class="search-input"
								clearable size="large" @keyup.enter="handleSearchAction" @clear="handleSearchAction">
								<template #prefix>
									<el-icon class="search-icon">
										<Search />
									</el-icon>
								</template>
							</el-input>
							<el-button size="large" :icon="Search" type="primary" plain @click="handleSearchAction"
								class="search-btn">搜索</el-button>
							<el-tooltip content="刷新数据" placement="top">
								<el-button size="large" :icon="Refresh" circle @click="() => fetchData(false)"
									class="refresh-btn" />
							</el-tooltip>
						</div>
					</div>

					<el-table :data="paginatedData" style="width: 100%;" v-loading="loading"
						header-cell-class-name="table-header-custom" row-class-name="table-row-custom"
						@expand-change="handleExpandChange" row-key="id" border>

						<el-table-column type="expand">
							<template #default="scope">
								<div class="nested-wrapper">
									<div class="nested-card">
										<div class="nested-header">
											<div class="nested-title-group">
												<div class="vertical-bar"></div>
												<span class="nested-title">
													<el-icon class="monitor-icon">
														<Monitor />
													</el-icon>
													节点资源透视
												</span>
												<el-tag type="info" size="small" effect="plain" round class="count-tag">
													{{ nodeMap[scope.row.id] ? nodeMap[scope.row.id].length : 0 }} Nodes
												</el-tag>
											</div>
											<el-button link type="primary" size="small" :icon="Refresh"
												:loading="nodeLoading[scope.row.id]"
												@click="refreshNodes(scope.row.id)">同步最新状态</el-button>
										</div>

										<el-table :data="nodeMap[scope.row.id] || []" :key="scope.row.id"
											v-loading="nodeLoading[scope.row.id]" size="small" class="node-table" border
											empty-text="暂无节点数据或未同步">

											<el-table-column prop="name" label="主机名" min-width="160"
												show-overflow-tooltip>
												<template #default="innerScope">
													<span class="node-name">{{ innerScope.row.name }}</span>
												</template>
											</el-table-column>

											<el-table-column prop="ip_address" label="IP地址" width="140">
												<template #default="innerScope">
													<span class="mono-text">{{ innerScope.row.ip_address }}</span>
												</template>
											</el-table-column>

											<el-table-column prop="role" label="角色" width="100" align="center">
												<template #default="innerScope">
													<el-tag
														:type="innerScope.row.role === 'master' ? 'primary' : 'info'"
														size="small"
														:effect="innerScope.row.role === 'master' ? 'dark' : 'plain'"
														round>
														{{ innerScope.row.role ? innerScope.row.role.toUpperCase() : '-' }}
													</el-tag>
												</template>
											</el-table-column>

											<el-table-column prop="status" label="节点状态" width="100" align="center">
												<template #default="innerScope">
													<div class="node-status-badge"
														:class="innerScope.row.status === 'Ready' ? 'ready' : 'not-ready'">
														{{ innerScope.row.status }}
													</div>
												</template>
											</el-table-column>

											<el-table-column label="CPU配置" width="120" prop="cpu_cores">
												<template #default="innerScope">
													<div class="resource-cell">
														<el-icon class="resource-icon cpu">
															<Cpu />
														</el-icon>
														<span class="spec-text" v-if="innerScope.row.cpu_cores > 0">
															{{ innerScope.row.cpu_cores }} <span
																class="unit">Cores</span>
														</span>
														<span v-else class="unknown-text">Unknown</span>
													</div>
												</template>
											</el-table-column>

											<el-table-column label="内存配置" width="120" prop="memory">
												<template #default="innerScope">
													<div class="resource-cell">
														<el-icon class="resource-icon mem">
															<Odometer />
														</el-icon>
														<span class="spec-text">{{ innerScope.row.memory }}</span>
													</div>
												</template>
											</el-table-column>

											<el-table-column label="磁盘总量" width="120" prop="disk_total">
												<template #default="innerScope">
													<div class="resource-cell">
														<el-icon class="resource-icon disk">
															<Files />
														</el-icon>
														<span class="spec-text">{{ innerScope.row.disk_total }}</span>
													</div>
												</template>
											</el-table-column>

											<el-table-column label="操作系统" prop="os_image" min-width="180"
												show-overflow-tooltip>
												<template #default="innerScope">
													<div class="os-cell">
														<el-icon>
															<Platform />
														</el-icon>
														<span>{{ innerScope.row.os_image }}</span>
													</div>
												</template>
											</el-table-column>

											<el-table-column label="操作" width="80" align="center" fixed="right">
												<template #default="innerScope">
													<el-button link type="primary" size="small"
														@click="handleNodeDetail(innerScope.row)">监控</el-button>
												</template>
											</el-table-column>
										</el-table>
									</div>
								</div>
							</template>
						</el-table-column>

						<el-table-column prop="name" label="集群名称" min-width="180" show-overflow-tooltip>
							<template #default="scope">
								<div class="cluster-name-cell">
									<span class="cluster-title">{{ scope.row.name }}</span>
								</div>
							</template>
						</el-table-column>

						<el-table-column prop="version" label="Kubernetes 版本" width="160">
							<template #default="scope">
								<span class="version-badge">{{ scope.row.version || '-' }}</span>
							</template>
						</el-table-column>

						<el-table-column prop="cluster_status" label="运行状态" width="140" align="center">
							<template #default="scope">
								<div class="status-cell">
									<span class="dot-pulse" :class="scope.row.cluster_status"></span>
									<span :class="['status-text', scope.row.cluster_status]">
										{{ getClusterStatusText(scope.row.cluster_status) }}
									</span>
								</div>
							</template>
						</el-table-column>

						<el-table-column prop="import_status" label="导入状态" width="140" align="center">
							<template #default="scope">
								<el-tag :type="getImportStatusType(scope.row.import_status)" size="small" effect="plain"
									round>
									{{ getImportStatusText(scope.row.import_status) }}
								</el-tag>
							</template>
						</el-table-column>

						<el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip>
							<template #default="scope">
								<span class="desc-text">{{ scope.row.description || '-' }}</span>
							</template>
						</el-table-column>

						<el-table-column prop="created_at" label="创建时间" width="170" align="center">
							<template #default="scope">
								<span class="time-text">{{ scope.row.created_at }}</span>
							</template>
						</el-table-column>

						<el-table-column label="操作" width="160" fixed="right" align="center">
							<template #default="scope">
								<div class="action-group">
									<el-button link type="primary" size="small" :icon="View"
										@click="handleView(scope.row)">
										详情
									</el-button>
									<el-button link type="danger" size="small" :icon="Delete"
										@click="handleDelete(scope.row)">
										删除
									</el-button>
								</div>
							</template>
						</el-table-column>
					</el-table>

					<div class="pagination-wrapper">
						<el-pagination v-model:current-page="queryParams.page" v-model:page-size="queryParams.page_size"
							:page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next, jumper"
							:total="filteredData.length" @size-change="handleSizeChange"
							@current-change="handleCurrentChange" background />
					</div>
				</el-card>
			</div>
		</div>
	</frame>
</template>

<script setup>
	import {
		ref,
		reactive,
		onMounted,
		onUnmounted,
		computed,
		watch
	} from 'vue'
	import {
		Plus,
		Refresh,
		Search,
		View,
		Delete,
		Monitor,
		Cpu,
		Odometer,
		Files,
		Platform
	} from '@element-plus/icons-vue'
	import {
		useRouter
	} from 'vue-router'
	import {
		ElMessage,
		ElMessageBox
	} from 'element-plus'

	import clusterHttp from "@/api/clusterHttp"
	import frame from "@/views/main/frame.vue"

	const router = useRouter()
	const loading = ref(false)

	// 1. 全量数据源
	const allTableData = ref([])
	const activeSearchKey = ref('')
	let timer = null

	// 3. 修改：使用 ref 代替 reactive 来处理动态键值对，解决响应式丢失问题
	const nodeMap = ref({})
	const nodeLoading = ref({})

	const queryParams = reactive({
		page: 1,
		page_size: 10,
		search: ''
	})

	// 计算属性：搜索过滤
	const filteredData = computed(() => {
		const search = activeSearchKey.value.trim()
		if (!search) {
			return allTableData.value
		}
		return allTableData.value.filter(item => {
			return item.name.includes(search)
		})
	})

	// 计算属性：分页切片
	const paginatedData = computed(() => {
		const start = (queryParams.page - 1) * queryParams.page_size
		const end = start + queryParams.page_size
		return filteredData.value.slice(start, end)
	})

	const handleSearchAction = () => {
		activeSearchKey.value = queryParams.search
		queryParams.page = 1
	}

	watch(() => queryParams.search, (newVal) => {
		if (!newVal) {
			handleSearchAction()
		}
	})

	// 获取集群列表
	const fetchData = async (isBackground = false) => {
		if (!isBackground) loading.value = true
		try {
			const res = await clusterHttp.getClusters()
			if (res.results) {
				allTableData.value = res.results
			} else if (Array.isArray(res)) {
				allTableData.value = res
			} else {
				allTableData.value = []
			}
		} catch (err) {
			console.error('获取集群列表失败', err)
			if (!isBackground) ElMessage.error(err || '获取数据失败')
		} finally {
			loading.value = false
		}
	}

	// 核心修改：使用 .value 赋值
	const fetchNodes = async (clusterId) => {
		nodeLoading.value[clusterId] = true
		try {
			const res = await clusterHttp.getClusterNodes(clusterId)
			console.log(`集群 ${clusterId} 的节点数据:`, res)

			let validNodes = []
			if (Array.isArray(res)) {
				validNodes = res
			} else if (res && Array.isArray(res.results)) {
				validNodes = res.results
			} else if (res && Array.isArray(res.data)) {
				validNodes = res.data
			} else {
				console.warn('获取到的节点数据格式非数组，已重置为空', res)
				validNodes = []
			}

			// 必须通过 .value[key] 赋值
			nodeMap.value[clusterId] = validNodes
			// 强制输出以确认
			console.log('nodeMap updated:', nodeMap.value)

		} catch (err) {
			console.error('获取节点失败', err)
			ElMessage.error('获取节点信息失败')
			nodeMap.value[clusterId] = []
		} finally {
			nodeLoading.value[clusterId] = false
		}
	}

	const handleExpandChange = async (row, expandedRows) => {
		console.log('展开事件触发，当前行:', row);

		// 核心修改：类型安全检查 (String转换)
		const isExpanded = expandedRows.some(r => String(r.id) === String(row.id));

		if (isExpanded) {
			console.log('正在请求节点数据...');
			await refreshNodes(row.id);
		} else {
			console.log('这是折叠操作，不请求数据');
		}
	}

	const refreshNodes = async (clusterId) => {
		nodeLoading.value[clusterId] = true
		try {
			ElMessage.info('正在连接集群与Prometheus同步数据...')
			await clusterHttp.syncClusterNodes(clusterId)
			ElMessage.success('节点资源监控已刷新')
		} catch (err) {
			console.error('刷新失败', err)
			const errMsg = err.detail || err.message || '同步失败'
			ElMessage.error(errMsg)
		} finally {
			// 移到这里：无论同步成功还是失败，都会去重新拉取一下列表
			await fetchNodes(clusterId)
			await fetchData()
			nodeLoading.value[clusterId] = false
		}
	}

	const handleNodeDetail = (nodeRow) => {
		console.log(nodeRow.ip_address)
		const ip = nodeRow.ip_address + ':27684'
		router.push({
			name: 'monitor',
			params: {
				ip
			}
		})
	}

	const getClusterStatusText = (status) => {
		const map = {
			'running': '运行正常',
			'abnormal': '状态异常',
			'unknown': '下线'
		}
		return map[status] || status
	}

	const getImportStatusText = (status) => {
		const map = {
			'success': '导入成功',
			'failed': '导入失败',
			'pending': '导入中'
		}
		return map[status] || status
	}

	const getImportStatusType = (status) => {
		const map = {
			'success': 'success',
			'failed': 'danger',
			'pending': 'warning'
		}
		return map[status] || 'info'
	}

	const handleDelete = (row) => {
		ElMessageBox.confirm(
			`确定要删除集群 "${row.name}" 吗? 此操作不可逆。`, '删除确认', {
				confirmButtonText: '确定删除',
				cancelButtonText: '取消',
				type: 'warning',
				confirmButtonClass: 'el-button--danger'
			}
		).then(async () => {
			try {
				await clusterHttp.deleteCluster(row.id)
				ElMessage.success('删除成功')
				fetchData(false)
			} catch (err) {
				ElMessage.error(err || '删除失败')
			}
		})
	}

	const handleCreate = () => {
		router.push({
			name: 'create'
		})
	}

	const handleView = (row) => {
		router.push({
			name: 'detailView',
			params: {
				id: row.id
			}
		});
	}

	const handleSizeChange = (val) => {
		queryParams.page_size = val
		queryParams.page = 1
	}

	const handleCurrentChange = (val) => {
		queryParams.page = val
	}

	onMounted(() => {
		fetchData(false)
		timer = setInterval(() => {
			fetchData(true)
		}, 30000)
	})

	onUnmounted(() => {
		if (timer) {
			clearInterval(timer)
			timer = null
		}
	})
</script>

<style scoped>
	/* 基础容器 */
	.cluster-container {
		padding: 24px;
		background-color: #f0f2f5;
		min-height: calc(100vh - 60px);
	}

	.main-card {
		border: none;
		border-radius: 12px;
		box-shadow: 0 4px 20px 0 rgba(0, 0, 0, 0.05);
	}

	/* 顶部操作区 */
	.header-actions {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 24px;
		padding-bottom: 24px;
		border-bottom: 1px solid #f0f0f0;
	}

	.right-panel {
		display: flex;
		align-items: center;
		gap: 12px;
	}

	.search-input {
		width: 280px;
	}

	.search-btn {
		background-color: #f2f3f5;
		border-color: #f2f3f5;
		color: #606266;
	}

	.search-btn:hover {
		background-color: #e4e7ed;
		color: #409EFF;
	}

	.refresh-btn {
		margin-left: 0 !important;
	}

	/* 表格样式优化 */
	:deep(.table-header-custom) {
		background-color: #f8f9fb !important;
		color: #1f2d3d;
		font-weight: 600;
		height: 54px;
		font-size: 14px;
	}

	:deep(.table-row-custom) {
		height: 60px;
	}

	/* 展开行区域 - 美化重点 */
	.nested-wrapper {
		padding: 10px 20px 20px 60px;
		/* 左侧留白给展开箭头 */
		background-color: #fbfbfc;
	}

	.nested-card {
		background: #fff;
		border: 1px solid #ebeef5;
		border-radius: 8px;
		overflow: hidden;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
	}

	.nested-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 12px 16px;
		background-color: #fafafa;
		border-bottom: 1px solid #ebeef5;
	}

	.nested-title-group {
		display: flex;
		align-items: center;
		gap: 10px;
	}

	.vertical-bar {
		width: 4px;
		height: 16px;
		background: #409EFF;
		border-radius: 2px;
	}

	.nested-title {
		font-size: 14px;
		font-weight: 600;
		color: #303133;
		display: flex;
		align-items: center;
	}

	.monitor-icon {
		margin-right: 6px;
		font-size: 16px;
		color: #606266;
	}

	.count-tag {
		font-weight: normal;
	}

	/* 节点表格微调 */
	.node-table {
		/* 去除内部表格边框，使用外层卡片的边框 */
		--el-table-border-color: #f0f0f0;
	}

	.node-name {
		font-weight: 500;
		color: #303133;
	}

	.mono-text {
		font-family: 'Consolas', 'Monaco', monospace;
		color: #606266;
		font-size: 13px;
	}

	/* 资源列样式 */
	.resource-cell {
		display: flex;
		align-items: center;
		gap: 6px;
	}

	.resource-icon {
		font-size: 14px;
	}

	.resource-icon.cpu {
		color: #E6A23C;
	}

	.resource-icon.mem {
		color: #67C23A;
	}

	.resource-icon.disk {
		color: #409EFF;
	}

	.spec-text {
		font-family: 'Roboto', sans-serif;
		font-weight: 500;
		color: #303133;
	}

	.unit {
		font-size: 12px;
		color: #909399;
		font-weight: normal;
	}

	.unknown-text {
		color: #C0C4CC;
		font-size: 12px;
	}

	.os-cell {
		display: flex;
		align-items: center;
		gap: 6px;
		color: #606266;
	}

	/* 节点状态 Badge */
	.node-status-badge {
		display: inline-block;
		padding: 2px 8px;
		border-radius: 4px;
		font-size: 12px;
		font-weight: 600;
	}

	.node-status-badge.ready {
		background-color: #f0f9eb;
		color: #67c23a;
	}

	.node-status-badge.not-ready {
		background-color: #fef0f0;
		color: #f56c6c;
	}

	/* 集群主表信息样式 */
	.cluster-name-cell {
		display: flex;
		flex-direction: column;
	}

	.cluster-title {
		font-weight: 600;
		font-size: 15px;
		color: #303133;
		margin-bottom: 2px;
	}

	.cluster-id {
		font-size: 12px;
		color: #909399;
	}

	.version-badge {
		background: #f4f4f5;
		padding: 2px 8px;
		border-radius: 4px;
		color: #555;
		font-family: monospace;
		font-size: 12px;
	}

	.desc-text {
		color: #909399;
		font-size: 13px;
	}

	.time-text {
		color: #606266;
		font-size: 13px;
	}

	/* --- 状态样式 --- */
	.status-cell {
		display: inline-flex;
		align-items: center;
		justify-content: center;
	}

	/* 呼吸灯动画点基础样式 */
	.dot-pulse {
		display: inline-block;
		width: 8px;
		height: 8px;
		border-radius: 50%;
		margin-right: 8px;
		position: relative;
	}

	/* 1. 就绪 (running) - 绿色 */
	.dot-pulse.running {
		background-color: #67C23A;
		box-shadow: 0 0 0 rgba(103, 194, 58, 0.4);
		animation: pulse-green 2s infinite;
	}

	.status-text.running {
		color: #67C23A;
	}

	/* 2. 异常 (abnormal) - 黄色 */
	.dot-pulse.abnormal {
		background-color: #E6A23C;
		/* Element Plus 的 Warning 黄色 */
		box-shadow: 0 0 0 rgba(230, 162, 60, 0.4);
		animation: pulse-yellow 2s infinite;
	}

	.status-text.abnormal {
		color: #E6A23C;
	}

	/* 3. 下线/未知 (unknown) - 红色 */
	.dot-pulse.unknown {
		background-color: #F56C6C;
		/* Element Plus 的 Danger 红色 */
		box-shadow: 0 0 0 rgba(245, 108, 108, 0.4);
		animation: pulse-red 2s infinite;
	}

	.status-text.unknown {
		color: #F56C6C;
	}

	/* 定义呼吸灯动画的关键帧 */
	@keyframes pulse-green {
		0% {
			box-shadow: 0 0 0 0 rgba(103, 194, 58, 0.7);
		}

		70% {
			box-shadow: 0 0 0 6px rgba(103, 194, 58, 0);
		}

		100% {
			box-shadow: 0 0 0 0 rgba(103, 194, 58, 0);
		}
	}

	@keyframes pulse-yellow {
		0% {
			box-shadow: 0 0 0 0 rgba(230, 162, 60, 0.7);
		}

		70% {
			box-shadow: 0 0 0 6px rgba(230, 162, 60, 0);
		}

		100% {
			box-shadow: 0 0 0 0 rgba(230, 162, 60, 0);
		}
	}

	@keyframes pulse-red {
		0% {
			box-shadow: 0 0 0 0 rgba(245, 108, 108, 0.7);
		}

		70% {
			box-shadow: 0 0 0 6px rgba(245, 108, 108, 0);
		}

		100% {
			box-shadow: 0 0 0 0 rgba(245, 108, 108, 0);
		}
	}

	.status-text {
		font-size: 13px;
	}

	.status-text.running {
		color: #67C23A;
	}

	.status-text.abnormal {
		color: #F56C6C;
	}

	.status-text.unknown {
		color: #E6A23C;
	}

	/* 底部页码 */
	.pagination-wrapper {
		margin-top: 24px;
		display: flex;
		justify-content: flex-end;
	}
</style>