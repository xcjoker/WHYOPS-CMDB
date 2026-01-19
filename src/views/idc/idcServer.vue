<template>
	<frame>
		<el-card class="box-card">
			<template #header>
				<div class="card-header">
					<span class="header-title">服务器资源列表</span>
					<div class="header-actions">
						<el-input v-model="search" placeholder="搜索主机名 / IP / 地域..." :prefix-icon="Search" clearable
							style="width: 250px; margin-right: 15px;" />
						<el-button type="primary" :icon="Plus" round @click="addIdServerButton">
							添加服务器
						</el-button>
					</div>
				</div>
			</template>

			<el-table :data="filterTableData" style="width: 100%" border stripe v-loading="tableLoading"
				element-loading-text="加载服务器数据中...">
				<el-table-column fixed="left" label="主机名" prop="hostname" min-width="140">
					<template #default="scope">
						<span style="font-weight: bold; color: #409EFF;">{{ scope.row.hostname }}</span>
					</template>
				</el-table-column>

				<el-table-column label="IP 地址" prop="ip" width="160">
					<template #default="scope">
						<el-icon style="margin-right: 4px; vertical-align: middle;">
							<Connection />
						</el-icon>
						<span>{{ scope.row.ip }}</span>
					</template>
				</el-table-column>

				<el-table-column label="配置信息" min-width="260">
					<template #default="scope">
						<el-space wrap :size="8">
							<el-tooltip content="CPU 核心数" placement="top">
								<el-tag type="info" effect="plain">
									<el-icon style="margin-right: 3px">
										<Cpu />
									</el-icon>
									{{ scope.row.cpu_count }}
								</el-tag>
							</el-tooltip>
							<el-tooltip content="内存大小" placement="top">
								<el-tag type="success" effect="plain">
									<el-icon style="margin-right: 3px">
										<Odometer />
									</el-icon>
									内存 {{ scope.row.memory_count }}
								</el-tag>
							</el-tooltip>
							<el-tooltip content="磁盘容量 (不含 swap)" placement="top">
								<el-tag type="warning" effect="plain">
									<el-icon style="margin-right: 3px">
										<Coin />
									</el-icon>
									磁盘 {{ scope.row.disk_count }}
								</el-tag>
							</el-tooltip>
						</el-space>
					</template>
				</el-table-column>

				<el-table-column label="所属地域" prop="region" width="120" sortable />

				<el-table-column label="用途描述" prop="function" show-overflow-tooltip min-width="150" />

				<el-table-column prop="status" label="监控状态" align="center" width="100">
					<template #default="scope">
						<el-tooltip content="扫描状态" placement="top">
							<div class="status-badge" :class="getStatusClass(scope.row.scan_status)">
								<span class="status-dot"></span>
								<span>{{ getStatusText(scope.row.scan_status) }}</span>
							</div>
						</el-tooltip>
					</template>
				</el-table-column>

				<el-table-column fixed="right" label="操作" width="160" align="center">
					<template #default="scope">
						<el-button size="small" type="primary" link :icon="DataLine" @click="monitor(scope.row)">
							监控
						</el-button>
						<el-button size="small" type="danger" link :icon="Delete" @click="handleDelete(scope.row)">
							删除
						</el-button>
					</template>
				</el-table-column>
			</el-table>

			<el-dialog v-model="dialogFormVisible" width="500px" draggable destroy-on-close class="custom-dialog"
				:close-on-click-modal="false">
				<template #header>
					<div class="dialog-header">
						<el-icon size="22" color="#409EFF" class="mr-2">
							<Platform />
						</el-icon>
						<span class="header-title">添加机房服务器</span>
					</div>
				</template>

				<div class="dialog-body">
					<el-alert title="服务器接入说明" type="info"
						description="系统将自动连接服务器，并在 27683 端口以 systemd 方式部署 node-exporter 用于监控。" show-icon
						:closable="false" class="mb-4" />

					<el-form :model="addIdcServerForm" :rules="rules" ref="formTag" label-position="top" size="large"
						class="custom-form">
						<el-row :gutter="20">
							<el-col :span="24">
								<el-form-item label="IP 地址" prop="ip">
									<el-input v-model="addIdcServerForm.ip" placeholder="请输入服务器内网 IP (如 192.168.1.1)"
										:prefix-icon="Connection" clearable />
								</el-form-item>
							</el-col>

							<el-col :span="24">
								<el-form-item label="SSH 密码" prop="password">
									<el-input v-model="addIdcServerForm.password" type="password" show-password
										placeholder="请输入 root 或 sudo 用户密码" :prefix-icon="Lock" />
								</el-form-item>
							</el-col>

							<el-col :span="12">
								<el-form-item label="服务器用途" prop="func">
									<el-input v-model="addIdcServerForm.func" placeholder="例如: 数据库/缓存"
										:prefix-icon="Document" />
								</el-form-item>
							</el-col>

							<el-col :span="12">
								<el-form-item label="所属地域" prop="region">
									<el-input v-model="addIdcServerForm.region" placeholder="例如: 北京机房"
										:prefix-icon="Location" />
								</el-form-item>
							</el-col>
						</el-row>
					</el-form>
				</div>

				<template #footer>
					<div class="dialog-footer">
						<el-button size="large" @click="dialogFormVisible = false">取消</el-button>

						<el-tooltip content="即将在27683端口以systemd部署node-exporter" placement="top" effect="dark">
							<span class="submit-wrapper">
								<el-button type="primary" size="large" @click="onsubmit" :loading="isSending"
									style="width: 140px;">
									<el-icon class="el-icon--left">
										<Upload />
									</el-icon>
									确认提交
								</el-button>
							</span>
						</el-tooltip>
					</div>
				</template>
			</el-dialog>

		</el-card>
	</frame>
</template>

<script setup>
	import frame from "@/views/main/frame.vue"
	import authHttp from "@/api/authHttp";
	import {
		Platform,
		Upload
	} from '@element-plus/icons-vue'
	import {
		computed,
		onMounted,
		ref,
		reactive
	} from 'vue'
	import {
		useRouter
	} from 'vue-router' // 1. 引入 useRouter
	import {
		ElMessage,
		ElMessageBox
	} from 'element-plus';
	import {
		Search,
		Plus,
		Delete,
		Connection,
		Cpu,
		Odometer,
		Coin,
		Lock,
		Document,
		Location,
		DataLine
	} from '@element-plus/icons-vue' // 引入 DataLine 图标

	const router = useRouter() // 2. 初始化 router

	// --- 状态定义 ---
	const search = ref('')
	const tableData = ref([])
	const dialogFormVisible = ref(false)
	const isSending = ref(false)
	const tableLoading = ref(false)
	const formLabelWidth = '100px'
	const formTag = ref()

	const addIdcServerForm = reactive({
		ip: '',
		password: '',
		func: '',
		region: ''
	})

	// --- 3. 新增监控跳转函数 ---
	const monitor = (row) => {
		const ip = row.ip + ':27683'
		router.push({
			name: 'monitor',
			params: {
				ip
			}
		})
	}

	// --- 校验规则 ---
	const validateIP = (rule, value, callback) => {
		const ipPattern =
			/^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/
		if (!value) {
			return callback(new Error('IP 地址是必填项'))
		} else if (!ipPattern.test(value)) {
			return callback(new Error('请输入合法的 IP 地址'))
		} else {
			callback()
		}
	}

	const rules = {
		ip: [{
			required: true,
			validator: validateIP,
			trigger: 'blur'
		}],
		password: [{
			required: true,
			message: '密码是必填项',
			trigger: 'blur'
		}],
		func: [{
			required: true,
			message: '此项是必填项',
			trigger: 'blur'
		}],
		region: [{
			required: true,
			message: '地域是必填项',
			trigger: 'blur'
		}],
	}

	// --- 计算属性 ---
	const filterTableData = computed(() =>
		tableData.value.filter((data) => {
			if (!search.value) return true;
			const key = search.value.toLowerCase();
			return (
				(data.region && data.region.toLowerCase().includes(key)) ||
				(data.hostname && data.hostname.toLowerCase().includes(key)) ||
				(data.ip && data.ip.includes(key))
			);
		})
	)

	// --- 辅助方法 ---
	const getStatusClass = (status) => {
		if (status === 1) return 'status-danger';
		if (status === 0) return 'status-warning';
		return 'status-success';
	}
	const getStatusText = (status) => {
		if (status === 1) return '异常';
		if (status === 0) return '告警';
		return '正常';
	}

	// --- 核心业务逻辑 ---
	const getList = async () => {
		tableLoading.value = true;
		try {
			const result = await authHttp.getIdcServer();
			tableData.value = result.map(item => ({
				id: item.id,
				hostname: item.hostname,
				ip: item.ip,
				cpu_count: item.cpu_count + '核',
				memory_count: item.memory_count + 'G',
				disk_count: item.disk_count + 'G',
				function: item.function,
				region: item.region,
				scan_status: item.scan_status
			}));
		} catch (e) {
			console.error(e);
			ElMessage.error("获取服务器列表失败");
		} finally {
			tableLoading.value = false;
		}
	}

	onMounted(() => {
		getList();
	})

	const onsubmit = async () => {
		formTag.value.validate(async (valid) => {
			if (valid) {
				try {
					isSending.value = true
					await authHttp.addIdcServer(
						addIdcServerForm.ip,
						addIdcServerForm.password,
						addIdcServerForm.func,
						addIdcServerForm.region
					)
					ElMessage.success('机房服务器添加成功')
					dialogFormVisible.value = false
					await getList();
				} catch (detail) {
					ElMessage.error(typeof detail === 'string' ? detail : '添加失败')
				} finally {
					isSending.value = false
				}
			} else {
				ElMessage.warning('请按要求填写字段')
			}
		})
	}

	const handleDelete = async (row) => {
		try {
			await ElMessageBox.confirm(
				`确认永久删除服务器 ${row.ip} 吗?`,
				'警告', {
					confirmButtonText: '确定删除',
					cancelButtonText: '取消',
					type: 'warning',
				}
			)
			await authHttp.deleteIdcServer(row.id)
			ElMessage.success('删除成功')
			await getList();
		} catch (error) {
			if (error !== 'cancel') {
				ElMessage.error('删除失败')
			}
		}
	}

	const addIdServerButton = () => {
		dialogFormVisible.value = true
		addIdcServerForm.ip = ''
		addIdcServerForm.password = ''
		addIdcServerForm.func = ''
		addIdcServerForm.region = ''
		if (formTag.value) formTag.value.clearValidate()
	}
</script>

<style scoped>
	.box-card {
		margin: 20px;
		border-radius: 8px;
	}

	.card-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.header-title {
		font-size: 18px;
		font-weight: 600;
		color: #333;
	}

	.header-actions {
		display: flex;
		align-items: center;
	}

	/* 状态徽章样式 */
	.status-badge {
		display: inline-flex;
		align-items: center;
		padding: 4px 10px;
		border-radius: 12px;
		font-size: 12px;
		font-weight: 500;
	}

	.status-dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		margin-right: 6px;
	}

	/* 正常 - 绿色 */
	.status-success {
		background-color: #f0f9eb;
		color: #67c23a;
		border: 1px solid #e1f3d8;
	}

	.status-success .status-dot {
		background-color: #67c23a;
	}

	/* 警告 - 黄色 */
	.status-warning {
		background-color: #fdf6ec;
		color: #e6a23c;
		border: 1px solid #faecd8;
	}

	.status-warning .status-dot {
		background-color: #e6a23c;
	}

	/* 危险/异常 - 红色 */
	.status-danger {
		background-color: #fef0f0;
		color: #f56c6c;
		border: 1px solid #fde2e2;
	}

	.status-danger .status-dot {
		background-color: #f56c6c;
	}

	.dialog-header {
		display: flex;
		/* 开启 Flex 布局 */
		align-items: center;
		/* 核心：强制垂直居中对齐 */

		padding-bottom: 10px;
		border-bottom: 1px solid #f0f2f5;
	}

	.header-title {
		font-size: 18px;
		font-weight: 600;
		color: #303133;
	}

	.mr-2 {
		margin-right: 8px;
	}

	.mb-4 {
		margin-bottom: 20px;
	}

	/* 调整表单内部间距 */
	.custom-form {
		margin-top: 10px;
	}

	.dialog-footer {
		display: flex;
		justify-content: flex-end;
		/* 按钮靠右 */
		align-items: center;
		padding-top: 10px;
	}

	.submit-wrapper {
		margin-left: 12px;
	}

	/* 稍微加深一点 label 的颜色 */
	:deep(.el-form-item__label) {
		font-weight: 500;
	}
</style>