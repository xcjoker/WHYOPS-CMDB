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
								class="filter-select" filterable @change="fetchPods">
								<el-option label="全部 (All)" value="all" />
								<el-option v-for="ns in namespaces" :key="ns" :label="ns" :value="ns" />
							</el-select>
						</div>

						<div class="right-panel">
							<el-input v-model="searchKeyword" placeholder="搜索 Pod 名称..." class="search-input" clearable
								size="large" :prefix-icon="Search" />
							<el-button size="large" :icon="Refresh" circle @click="fetchPods" class="refresh-btn" />
							<el-button type="primary" size="large" :icon="Plus" @click="handleCreate">
								创建 Pod
							</el-button>
						</div>
					</div>

					<el-table :data="filteredPodList" v-loading="loading" style="width: 100%"
						header-cell-class-name="table-header-custom" row-class-name="table-row-custom">
						<el-table-column label="" width="50" align="center">
							<template #default="{ row }">
								<el-tooltip :content="row.status" placement="right">
									<div :class="['status-dot', getStatusColor(row.status)]"></div>
								</el-tooltip>
							</template>
						</el-table-column>

						<el-table-column prop="name" label="名称" min-width="200" show-overflow-tooltip>
							<template #default="{ row }">
								<span class="pod-name">{{ row.name }}</span>
								<div class="sub-text">{{ row.namespace }}</div>
							</template>
						</el-table-column>

						<el-table-column prop="ip" label="IP / 节点" width="160" show-overflow-tooltip>
							<template #default="{ row }">
								<div class="main-text">{{ row.ip || '--' }}</div>
								<div class="sub-text">{{ row.node || 'Pending' }}</div>
							</template>
						</el-table-column>

						<el-table-column label="CPU使用率(最大值)" width="180">
							<template #default="{ row }">
								<div class="capsule-container">
									<div class="capsule-track">
										<div class="capsule-bar" :style="{
                        width: Math.min(row.cpu.percent, 100) + '%',
                        backgroundColor: getUsageColor(row.cpu.percent)
                      }"></div>
									</div>
									<div class="capsule-text">
										<span :style="{ color: getUsageColor(row.cpu.percent) }">
											{{ row.cpu.limit > 0 ? row.cpu.percent + '%' : '无限制' }}
										</span>
										<span class="unit-text">{{ row.cpu.usage }} C</span>
									</div>
								</div>
							</template>
						</el-table-column>

						<el-table-column label="内存使用率(最大值)" width="180">
							<template #default="{ row }">
								<div class="capsule-container">
									<div class="capsule-track">
										<div class="capsule-bar" :style="{
                        width: Math.min(row.memory.percent, 100) + '%',
                        backgroundColor: getUsageColor(row.memory.percent)
                      }"></div>
									</div>
									<div class="capsule-text">
										<span :style="{ color: getUsageColor(row.memory.percent) }">
											{{ row.memory.limit > 0 ? row.memory.percent + '%' : '无限制' }}
										</span>
										<span class="unit-text">{{ Math.round(row.memory.usage) }} Mi</span>
									</div>
								</div>
							</template>
						</el-table-column>

						<el-table-column prop="restarts" label="重启" width="80" align="center" />

						<el-table-column prop="age" label="存活时间" width="100" align="center" />

						<el-table-column label="操作" width="180" fixed="right" align="center">
							<template #default="{ row }">
								<el-dropdown trigger="click">
									<el-button link type="primary" size="small">
										更多操作 <el-icon class="el-icon--right">
											<ArrowDown />
										</el-icon>
									</el-button>
									<template #dropdown>
										<el-dropdown-menu>
											<el-dropdown-item :icon="Document" @click="handleViewYaml(row)">查看
												YAML</el-dropdown-item>
											<el-dropdown-item :icon="Notebook"
												@click="handleLogs(row)">查看日志</el-dropdown-item>
											<el-dropdown-item divided :icon="Delete" class="text-danger"
												@click="handleDelete(row)">
												删除 Pod
											</el-dropdown-item>
										</el-dropdown-menu>
									</template>
								</el-dropdown>
							</template>
						</el-table-column>
					</el-table>
				</el-card>
			</div>

			<el-dialog v-model="dialogVisible" :title="`YAML: ${currentPod?.name}`" width="60%" destroy-on-close>
				<el-input v-model="currentYaml" type="textarea" :rows="20" placeholder="Loading..."
					class="yaml-editor" />
				<template #footer>
					<span class="dialog-footer">
						<el-button @click="dialogVisible = false">关闭</el-button>
						<el-button type="primary" @click="handleUpdateYaml">提交修改</el-button>
					</span>
				</template>
			</el-dialog>

			<el-dialog v-model="logDialogVisible" title="容器日志 (Last 1000 lines)" width="70%" top="5vh" destroy-on-close
				class="log-dialog">
				<div class="log-toolbar">
					<div class="log-tools-left">
						<span class="log-label">Pod: {{ currentPod?.name }}</span>

						<span class="log-label ml-4">容器:</span>
						<el-select v-model="currentContainer" placeholder="选择容器" size="small" style="width: 160px;"
							@change="refreshLogs">
							<el-option v-for="c in containerOptions" :key="c" :label="c" :value="c" />
						</el-select>
					</div>

					<el-button size="small" :icon="Refresh" @click="refreshLogs" :loading="logLoading">刷新</el-button>
				</div>

				<div class="terminal-window" v-loading="logLoading" element-loading-text="正在拉取日志...">
					<pre class="terminal-content" ref="logContentRef">{{ logContent }}</pre>
				</div>

				<template #footer>
					<el-button @click="logDialogVisible = false">关闭</el-button>
				</template>
			</el-dialog>

			<el-dialog v-model="createDialogVisible" title="创建 Pod" width="60%" destroy-on-close>
				<el-alert title="请编写标准的 Kubernetes Pod YAML 配置" type="info" show-icon :closable="false"
					style="margin-bottom: 15px;" />

				<el-input v-model="createYaml" type="textarea" :rows="20" placeholder="在此输入 YAML..." class="yaml-editor"
					spellcheck="false" />

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
		computed,
		nextTick,
	} from 'vue'
	import {
		Search,
		Refresh,
		Plus,
		ArrowDown,
		Document,
		Delete,
		Notebook
	} from '@element-plus/icons-vue'
	import {
		ElMessage,
		ElMessageBox,
		ElLoading
	} from 'element-plus'

	// 引入 API 模块
	import clusterHttp from '@/api/clusterHttp' // 复用获取集群列表
	import workloadHttp from '@/api/workloadHttp' // 新建的 workload API
	import frame from "@/views/main/frame.vue" // 保持你的布局结构
	

	const yamlLoading = ref(false) //控制 Dialog 内容加载状态

	// --- 状态定义 ---
	const loading = ref(false)
	const clusterList = ref([])
	const podList = ref([])
	const searchKeyword = ref('')
	const dialogVisible = ref(false)
	const currentYaml = ref('')
	const currentPod = ref(null)
	const namespaces = ref([])

	const createDialogVisible = ref(false)
	const createLoading = ref(false)
	const createYaml = ref('')
	// 默认模板
	const defaultPodTemplate = `apiVersion: v1
	kind: Pod
	metadata:
	  name: my-demo-pod
	  namespace: default
	  labels:
	    app: demo
	spec:
	  containers:
	  - name: nginx
	    image: nginx:latest
	    ports:
	    - containerPort: 80
	    resources:
	      limits:
	        memory: "128Mi"
	        cpu: "500m"
	`

	const logDialogVisible = ref(false)
	const logLoading = ref(false)
	const logContent = ref('')
	const logContentRef = ref(null) // 用于绑定 DOM 元素实现自动滚动

	const currentContainer = ref('') // 当前选中的容器
	const containerOptions = ref([]) // 容器列表

	// 日志处理逻辑
	const handleLogs = async (row) => {
		currentPod.value = row

		// 1. 初始化容器列表
		// 后端返回的 row.containers 是一个数组 ['prometheus', 'config-reloader']
		if (row.containers && row.containers.length > 0) {
			containerOptions.value = row.containers
			currentContainer.value = row.containers[0] // 默认选中第一个
		} else {
			containerOptions.value = []
			currentContainer.value = ''
		}

		logDialogVisible.value = true
		await fetchLogs()
	}

	const refreshLogs = () => {
		fetchLogs()
	}

	// fetchLogs 逻辑微调，传入 currentContainer
	const fetchLogs = async () => {
		logLoading.value = true
		logContent.value = ''

		try {
			const res = await workloadHttp.getPodLogs(
				queryParams.cluster_id,
				currentPod.value.namespace,
				currentPod.value.name,
				currentContainer.value // <--- 【重点】传入当前选中的容器名
			)
			logContent.value = res.logs || '暂无日志输出'

			nextTick(() => {
				if (logContentRef.value) {
					const parent = logContentRef.value.parentElement
					parent.scrollTop = parent.scrollHeight
				}
			})
		} catch (err) {
			logContent.value = `获取日志失败: ${err}`
		} finally {
			logLoading.value = false
		}
	}

	const fetchNamespaces = async () => {
		try {
			const res = await clusterHttp.getClusterNamespace(queryParams.cluster_id)
			namespaces.value = res;
		} catch (err) {
			console.error("获取命名空间失败", err);
		}
	};

	const queryParams = reactive({
		cluster_id: null,
		namespace: 'all' // 默认值改为 'all'
	})

	// --- 计算属性：前端搜索过滤 ---
	const filteredPodList = computed(() => {
		if (!searchKeyword.value) return podList.value
		const lowerKey = searchKeyword.value.toLowerCase()
		return podList.value.filter(item =>
			item.name.toLowerCase().includes(lowerKey) ||
			item.node?.toLowerCase().includes(lowerKey)
		)
	})

	// --- 初始化数据 ---
	const initData = async () => {
		try {
			// 1. 获取集群列表
			const res = await clusterHttp.getClusters()
			clusterList.value = res.results || res || []

			// 2. 默认选中第一个集群并加载 Pod
			if (clusterList.value.length > 0) {
				queryParams.cluster_id = clusterList.value[0].id
				console.log(clusterList.value[0].id)
				console.log(queryParams.cluster_id)
				fetchNamespaces()
				fetchPods()
			}
		} catch (err) {
			ElMessage.error('初始化数据失败')
		}
	}

	const handleClusterChange = () => {
		// 切换集群时，也需要重新获取该集群的命名空间
		fetchNamespaces()
		// 重置为 'all'
		queryParams.namespace = 'all'
		fetchPods()
	}

	// 获取 Pod 列表
	const fetchPods = async () => {
		if (!queryParams.cluster_id) return
		loading.value = true
		try {
			const res = await workloadHttp.getPods(queryParams.cluster_id, queryParams.namespace)
			podList.value = res
			ElMessage.success('Pod 列表已刷新')
		} catch (err) {
			console.error(err)
			podList.value = []
			ElMessage.error(err.detail || '获取 Pod 列表失败')
		} finally {
			loading.value = false
		}
	}

	// --- 样式逻辑 ---
	const getStatusColor = (status) => {
		const map = {
			'Running': 'bg-success',
			'Succeeded': 'bg-success',
			'Pending': 'bg-warning',
			'Failed': 'bg-danger',
			'Unknown': 'bg-info'
		}
		return map[status] || 'bg-danger' // 默认红色，提示异常
	}

	// 根据百分比返回颜色 (绿 -> 橙 -> 红)
	const getUsageColor = (percent) => {
		if (percent < 60) return '#67c23a' // Element Success
		if (percent < 85) return '#e6a23c' // Element Warning
		return '#f56c6c' // Element Danger
	}

	const handleCreate = () => {
		// 1. 设置默认模板
		createYaml.value = defaultPodTemplate
		// 2. 如果当前选了 namespace 且不是 'all'，自动替换模板里的 namespace
		if (queryParams.namespace && queryParams.namespace !== 'all') {
			createYaml.value = createYaml.value.replace('namespace: default', `namespace: ${queryParams.namespace}`)
		}
		// 3. 打开弹窗
		createDialogVisible.value = true
	}

	const submitCreate = async () => {
		if (!createYaml.value) {
			ElMessage.warning('YAML 内容不能为空')
			return
		}

		if (!queryParams.cluster_id) {
			ElMessage.error('未选择集群')
			return
		}

		createLoading.value = true
		try {
			await workloadHttp.createPod(queryParams.cluster_id, createYaml.value)
			ElMessage.success('创建请求已发送')
			createDialogVisible.value = false

			// 稍等片刻后刷新列表，让用户看到新 Pod (Pending状态)
			setTimeout(() => {
				fetchPods()
			}, 1000)

		} catch (err) {
			// err 会包含后端返回的 detail (如 "pod xxx already exists")
			ElMessage.error(err)
		} finally {
			createLoading.value = false
		}
	}

	// --- 查看 YAML ---
	const handleViewYaml = async (row) => {
		currentPod.value = row
		dialogVisible.value = true
		currentYaml.value = '' // 先清空
		yamlLoading.value = true

		try {
			const res = await workloadHttp.getPodYaml(
				queryParams.cluster_id,
				row.namespace,
				row.name
			)
			// 后端返回的是 { content: "..." }
			currentYaml.value = res.content
		} catch (err) {
			ElMessage.error(err || '获取 YAML 失败')
			currentYaml.value = '# 获取失败，请重试'
		} finally {
			yamlLoading.value = false
		}
	}

	// --- 提交 YAML ---
	const handleUpdateYaml = async () => {
		if (!currentYaml.value) return

		// 简单的二次确认
		try {
			await ElMessageBox.confirm(
				'确定要更新此 Pod 的配置吗？如果修改了不可变字段可能会失败。',
				'更新确认', {
					type: 'warning'
				}
			)
		} catch {
			return // 用户取消
		}

		const loadingInstance = ElLoading.service({
			target: '.el-dialog', // 遮罩只覆盖弹窗
			text: '正在提交 K8s 更新...'
		})

		try {
			await workloadHttp.updatePodYaml(
				queryParams.cluster_id,
				currentPod.value.namespace,
				currentPod.value.name,
				currentYaml.value
			)

			ElMessage.success('YAML 更新成功，Pod 正在重建中...')
			dialogVisible.value = false
			fetchPods() // 刷新列表查看最新状态
		} catch (err) {
			console.error(err)
			// err 已经是拦截器处理过的 detail 字符串了
			ElMessage.error('更新失败: ' + err)
		} finally {
			loadingInstance.close()
		}
	}


	const handleDelete = (row) => {
		ElMessageBox.confirm(
			`确认删除 Pod: ${row.name} ? 此操作不可逆。`,
			'高危操作警告', {
				confirmButtonText: '确定删除',
				cancelButtonText: '取消',
				type: 'warning',
				confirmButtonClass: 'el-button--danger' // 按钮变红，起警示作用
			}
		).then(async () => {
			try {
				// 1. 调用接口
				await workloadHttp.deletePod(
					queryParams.cluster_id,
					row.namespace,
					row.name
				)

				ElMessage.success('删除指令已发送')

				// 2. 刷新列表 (删除是异步的，K8s 也就是标记为 Terminating)
				// 稍微延迟一下再刷新，能看到 Terminating 状态
				setTimeout(() => {
					fetchPods()
				}, 500)

			} catch (err) {
				ElMessage.error(err || '删除失败')
			}
		}).catch(() => {
			// 取消删除，不做任何事
		})
	}

	onMounted(() => {
		initData()
	})

</script>

<style scoped>
	/* 容器样式：使用白色背景，保持清爽 */
	.workload-container {
		padding: 24px;
		background-color: #f0f2f5;
		/* 外部浅灰底色 */
		min-height: calc(100vh - 60px);
	}

	.main-card {
		border: none;
		border-radius: 8px;
		/* 更圆润的边角 */
		box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
	}

	/* 顶部栏 */
	.header-actions {
		display: flex;
		justify-content: space-between;
		align-items: center;
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

	.ml-4 {
		margin-left: 24px;
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

	/* 表格自定义样式 */
	:deep(.table-header-custom) {
		background-color: #f8f9fb !important;
		color: #303133;
		font-weight: 600;
		height: 50px;
	}

	:deep(.table-row-custom) {
		height: 65px;
		/* 稍微增加行高，给胶囊条留空间 */
	}

	/* 文本样式 */
	.pod-name {
		font-weight: 600;
		color: #409EFF;
		font-size: 14px;
	}

	.main-text {
		color: #303133;
		font-size: 13px;
	}

	.sub-text {
		font-size: 12px;
		color: #909399;
		margin-top: 4px;
		line-height: 1.2;
	}

	/* 状态圆点 */
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

	.bg-danger {
		background-color: #f56c6c;
		box-shadow: 0 0 4px rgba(245, 108, 108, 0.4);
	}

	.bg-info {
		background-color: #909399;
	}

	/* --- 胶囊进度条样式 (核心) --- */
	.capsule-container {
		display: flex;
		flex-direction: column;
		justify-content: center;
		width: 100%;
	}

	.capsule-track {
		width: 100%;
		height: 8px;
		/* 轨道高度 */
		background-color: #ebeef5;
		/* 浅灰轨道 */
		border-radius: 4px;
		/* 全圆角 */
		overflow: hidden;
		margin-bottom: 6px;
	}

	.capsule-bar {
		height: 100%;
		border-radius: 4px;
		transition: width 0.5s ease-in-out, background-color 0.3s;
	}

	.capsule-text {
		display: flex;
		justify-content: space-between;
		font-size: 12px;
		font-weight: 500;
		line-height: 1;
	}

	.unit-text {
		color: #909399;
		font-weight: normal;
		transform: scale(0.95);
		transform-origin: right center;
	}

	/* 下拉菜单文字红色警告 */
	.text-danger {
		color: #f56c6c;
	}

	/* YAML 编辑器字体 */
	.yaml-editor :deep(.el-textarea__inner) {
		font-family: 'Consolas', 'Monaco', monospace;
		background-color: #f9fafc;
		color: #303133;
	}

	/* 【修改 2】补充日志弹窗的 CSS 样式 */
	.log-toolbar {
		margin-bottom: 10px;
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.log-label {
		font-weight: bold;
		color: #303133;
	}

	/* 模拟终端窗口 */
	.terminal-window {
		background-color: #1e1e1e;
		/* VSCode 风格深色背景 */
		color: #d4d4d4;
		/* 浅灰文字 */
		padding: 15px;
		border-radius: 4px;
		height: 60vh;
		/* 固定高度 */
		overflow-y: auto;
		/* 允许垂直滚动 */
		font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
		/* 等宽字体 */
		font-size: 13px;
		line-height: 1.5;
		border: 1px solid #333;
	}

	/* 保持格式，处理换行 */
	.terminal-content {
		margin: 0;
		white-space: pre-wrap;
		/* 自动换行 */
		word-wrap: break-word;
	}

	/* 滚动条美化 */
	.terminal-window::-webkit-scrollbar {
		width: 10px;
		background-color: #1e1e1e;
	}

	.terminal-window::-webkit-scrollbar-thumb {
		background-color: #444;
		border-radius: 5px;
	}

	.log-toolbar {
		margin-bottom: 10px;
		display: flex;
		justify-content: space-between;
		align-items: center;
		background-color: #f5f7fa;
		/* 加个浅底色更好看 */
		padding: 8px;
		border-radius: 4px;
	}

	.log-tools-left {
		display: flex;
		align-items: center;
		gap: 10px;
	}

	.log-label {
		font-weight: 600;
		color: #606266;
		font-size: 13px;
	}

	/* 之前 .ml-4 可能只定义在 template scope 外，这里补一个 safe 的 margin class */
	.ml-4 {
		margin-left: 16px;
	}
</style>