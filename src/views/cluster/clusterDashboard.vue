<template>
	<frame>
		<div class="dashboard-container">
			<div class="dashboard-header">
				<div class="header-left">
					<el-button @click="goBack" icon="ArrowLeft" circle class="back-btn" />
					<span class="page-title">集群概览</span>
				</div>
				<div class="header-right">
					<el-select v-model="selectedNamespace" placeholder="选择命名空间" @change="fetchData" class="ns-select"
						size="large">
						<el-option label="All Namespaces" value="all" />
						<el-option v-for="ns in namespaces" :key="ns" :label="ns" :value="ns" />
					</el-select>
					<el-button icon="Refresh" circle @click="fetchData" class="refresh-btn" />
				</div>
			</div>

			<el-card class="overview-banner" shadow="never">
				<el-row :gutter="0" align="middle" class="overview-row">
					<el-col :span="8" class="overview-item">
						<div class="ov-label">名称</div>
						<div class="ov-value">{{ clusterInfo.name }}</div>
					</el-col>
					<el-col :span="1" class="ov-divider">
						<div class="divider-line"></div>
					</el-col>
					<el-col :span="7" class="overview-item">
						<div class="ov-label">版本</div>
						<div class="ov-value">{{ clusterInfo.version }}</div>
					</el-col>
					<el-col :span="1" class="ov-divider">
						<div class="divider-line"></div>
					</el-col>
					<el-col :span="7" class="overview-item">
						<div class="ov-label">存活时间</div>
						<div class="ov-value">{{ clusterInfo.uptime }}</div>
					</el-col>
				</el-row>
			</el-card>

			<div class="resource-grid" v-loading="loading" element-loading-background="rgba(0, 0, 0, 0.5)">
				<el-row :gutter="15">
					<el-col :span="6" v-for="(item, index) in resourceConfig" :key="index" style="margin-bottom: 15px;">
						<DashboardCard :label="item.label" :value="stats[item.key] || 0" :color="item.color" />
					</el-col>
				</el-row>
			</div>

			<div class="events-section">
				<div class="section-title">事件 (Events)</div>
				<el-card class="event-card" shadow="never">
					<el-table :data="events" style="width: 100%; height: 100%;"
						:header-cell-style="{ background: '#f5f7fa', color: '#606266', fontWeight: '600' }">
						<el-table-column prop="reason" label="原因" width="120">
							<template #default="scope">
								<span :class="scope.row.reason === 'Normal' ? 'text-normal' : 'text-warning'">
									{{ scope.row.reason }}
								</span>
							</template>
						</el-table-column>
						<el-table-column prop="namespace" label="命名空间" width="140" />
						<el-table-column prop="message" label="消息" min-width="300" show-overflow-tooltip />
						<el-table-column prop="object" label="对象" width="220" />
						<el-table-column prop="time" label="时间" width="180">
							<template #default="scope">
								{{ formatTime(scope.row.time) }}
							</template>
						</el-table-column>
					</el-table>
				</el-card>
			</div>
		</div>
	</frame>
</template>

<script setup>
	// 1. 引入 onUnmounted
	import {
		ref,
		reactive,
		onMounted,
		onUnmounted
	} from 'vue';
	import {
		useRoute,
		useRouter
	} from 'vue-router';
	import {
		ElMessage
	} from 'element-plus';
	import {
		ArrowLeft,
		Refresh
	} from '@element-plus/icons-vue';
	import DashboardCard from './DashboardCard.vue';
	import clusterHttp from "@/api/clusterHttp";
	import frame from "@/views/main/frame.vue"

	const route = useRoute();
	const router = useRouter();
	const clusterId = route.params.id;

	const loading = ref(false);
	const selectedNamespace = ref('all');
	const namespaces = ref([]);

	// 定义定时器变量
	let timer = null;

	// 资源卡片配置 (保持不变)
	const resourceConfig = [{
			label: 'Nodes',
			key: 'nodes',
			color: '#F4D03F'
		}, // 黄
		{
			label: 'Namespaces',
			key: 'namespaces',
			color: '#A3E048'
		}, // 浅绿
		{
			label: 'Ingresses',
			key: 'ingresses',
			color: '#E74C3C'
		}, // 红
		{
			label: 'PVs',
			key: 'pvs',
			color: '#E91E63'
		}, // 粉
		{
			label: 'DaemonSets',
			key: 'daemon_sets',
			color: '#3498DB'
		}, // 蓝
		{
			label: 'StatefulSets',
			key: 'stateful_sets',
			color: '#E67E22'
		}, // 橙
		{
			label: 'Jobs',
			key: 'jobs',
			color: '#1ABC9C'
		}, // 青
		{
			label: 'Services',
			key: 'services',
			color: '#9B59B6'
		}, // 紫
		{
			label: 'CronJobs',
			key: 'cron_jobs',
			color: '#3F51B5'
		}, // 深蓝
		{
			label: 'Deployments',
			key: 'deployments',
			color: '#00BCD4'
		}, // 蓝绿
		{
			label: 'Secrets',
			key: 'secrets',
			color: '#8BC34A'
		}, // 绿
		{
			label: 'ConfigMaps',
			key: 'config_maps',
			color: '#C0392B'
		}, // 深红
	];

	const clusterInfo = reactive({
		name: 'Loading...',
		version: '-',
		uptime: '-'
	});
	const stats = ref({});
	const events = ref([]);

	const fetchNamespaces = async () => {
		try {
			const res = await clusterHttp.getClusterNamespace(clusterId)
			// console.log(res) // 轮询时建议注释掉 log，防止控制台刷屏
			namespaces.value = res;
		} catch (err) {
			console.error("获取命名空间失败", err);
		}
	};

	// ✅ 修改点：增加 isPolling 参数，默认为 false
	const fetchData = async (isPolling = false) => {
		if (!clusterId) return;

		// ✅ 关键逻辑：如果是轮询（isPolling=true），则【不】显示 loading
		// 只有首次加载或手动刷新时才显示转圈圈
		if (!isPolling) {
			loading.value = true;
		}

		try {
			// 1. 获取统计数据
			const res = await clusterHttp.getDashboardStats(clusterId, selectedNamespace.value);

			clusterInfo.name = res.name;
			clusterInfo.version = res.version;
			clusterInfo.uptime = res.uptime;
			stats.value = res.stats;

			// 2. 获取事件数据
			const eventRes = await clusterHttp.getRecentEvents(clusterId, selectedNamespace.value);
			events.value = eventRes;

		} catch (err) {
			// 轮询时出错可以考虑不弹窗，或者只打印日志，避免每两秒弹一个报错
			console.error(err);
			if (!isPolling) {
				ElMessage.error(typeof err === 'string' ? err : '获取集群监控数据失败');
			}
		} finally {
			loading.value = false;
		}
	};

	const formatTime = (timeStr) => {
		if (!timeStr) return '-';
		return new Date(timeStr).toLocaleString();
	};

	const goBack = () => {
		router.back();
	};

	onMounted(() => {
		// 进页面立即执行一次（前台加载，显示 Loading）
		fetchNamespaces();
		fetchData(false);

		// 每 2000ms 执行一次（后台轮询，不显示 Loading）
		timer = setInterval(() => {
			fetchNamespaces();
			fetchData(true); // 传入 true，表示这是静默刷新
		}, 30000);
	});

	// ✅ 必加：离开页面销毁定时器
	onUnmounted(() => {
		if (timer) {
			clearInterval(timer);
			timer = null;
		}
	});
</script>

<style scoped>
	/* ================== 核心布局 ================== */

	.dashboard-container {
		background-color: #f5f7fa;
		/* 浅灰背景 */
		height: 100vh;
		/* 占满一屏 */
		width: 100%;

		display: flex;
		flex-direction: column;
		/* 垂直排列 */

		padding: 20px;
		box-sizing: border-box;
		overflow: hidden;
		/* 禁止整页滚动 */
		color: #303133;
	}

	/* 1. 头部 (固定不缩放) */
	.dashboard-header {
		flex-shrink: 0;
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 20px;
	}

	/* 2. Banner (固定不缩放) */
	.overview-banner {
		flex-shrink: 0;
		background-color: #ffffff;
		border: 1px solid #e4e7ed;
		margin-bottom: 20px;
		border-radius: 4px;
	}

	/* 3. 资源 Grid (关键修改：全部展示，不许滚动，不许压缩) */
	.resource-grid {
		flex-shrink: 0;
		/* 关键：禁止被挤压 */
		height: auto;
		/* 关键：高度由内容撑开 */
		overflow: visible;
		/* 关键：取消滚动条 */
		margin-bottom: 20px;
	}

	/* 4. 事件列表 (关键修改：占据剩余空间，表格内部滚动) */
	.events-section {
		flex: 1;
		/* 占据剩余所有高度 */
		display: flex;
		flex-direction: column;
		overflow: hidden;
		/* 防止溢出 */
		min-height: 0;
		/* Flex 布局嵌套滚动必须属性 */
	}

	/* ================== 组件内部细节 ================== */

	.header-left {
		display: flex;
		align-items: center;
		gap: 15px;
	}

	.page-title {
		font-size: 20px;
		font-weight: 600;
		color: #303133;
	}

	.back-btn,
	.refresh-btn {
		background-color: #fff;
		border-color: #dcdfe6;
		color: #606266;
	}

	.back-btn:hover,
	.refresh-btn:hover {
		background-color: #ecf5ff;
		border-color: #409EFF;
		color: #409EFF;
	}

	.ns-select {
		width: 200px;
	}

	/* Banner 内容 */
	:deep(.el-card__body) {
		padding: 20px;
	}

	.overview-item {
		text-align: center;
	}

	.ov-label {
		color: #909399;
		font-size: 14px;
		margin-bottom: 8px;
	}

	.ov-value {
		font-size: 32px;
		font-weight: 500;
		color: #303133;
		font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', sans-serif;
	}

	.ov-divider {
		display: flex;
		justify-content: center;
	}

	.divider-line {
		width: 1px;
		height: 40px;
		background-color: #e4e7ed;
	}

	/* 事件部分标题 */
	.section-title {
		flex-shrink: 0;
		font-size: 16px;
		margin: 0 0 12px;
		color: #303133;
		padding-left: 8px;
		border-left: 4px solid #409EFF;
		font-weight: bold;
	}

	/* 事件卡片 & 表格自适应 */
	.event-card {
		background-color: #fff;
		border: 1px solid #e4e7ed;
		flex: 1;
		/* 卡片撑满剩余空间 */
		display: flex;
		flex-direction: column;
		overflow: hidden;
		/* 内部溢出隐藏 */
	}

	/* 让 el-card 的 body 也撑满，方便表格计算高度 */
	:deep(.event-card .el-card__body) {
		flex: 1;
		padding: 0;
		/* 建议去掉 padding 让表格贴边 */
		height: 100%;
	}

	/* 表格样式 */
	.text-normal {
		color: #606266;
	}

	.text-warning {
		color: #000000;
	}

	:deep(.el-table) {
		width: 100%;
		height: 100% !important;
		/* 强制表格高度占满父容器 */
		--el-table-border-color: #ebeef5;
		--el-table-header-bg-color: #f5f7fa;
	}

	:deep(.el-table th.el-table__cell) {
		background-color: #f5f7fa !important;
		color: #606266;
		font-weight: 600;
	}
</style>