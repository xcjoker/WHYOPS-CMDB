<template>
	<div class="dashboard-container">
		<el-row :gutter="20" class="mb-4">
			<el-col :xs="24" :sm="12" :md="6">
				<el-card shadow="hover" class="stat-card">
					<div class="stat-content">
						<div class="stat-icon bg-blue">
							<el-icon>
								<Monitor />
							</el-icon>
						</div>
						<div class="stat-info">
							<div class="stat-value">{{ clusters.length }}</div>
							<div class="stat-label">K8s 集群总数</div>
						</div>
					</div>
				</el-card>
			</el-col>
			<el-col :xs="24" :sm="12" :md="6">
				<el-card shadow="hover" class="stat-card">
					<div class="stat-content">
						<div class="stat-icon bg-green">
							<el-icon>
								<DataLine />
							</el-icon>
						</div>
						<div class="stat-info">
							<div class="stat-value">{{ serverList.length }}</div>
							<div class="stat-label">IDC 服务器总数</div>
						</div>
					</div>
				</el-card>
			</el-col>
			<el-col :xs="24" :sm="12" :md="6">
				<el-card shadow="hover" class="stat-card">
					<div class="stat-content">
						<div class="stat-icon bg-orange">
							<el-icon>
								<Bell />
							</el-icon>
						</div>
						<div class="stat-info">
							<div class="stat-value">{{ informs.length }}</div>
							<div class="stat-label">最新通知</div>
						</div>
					</div>
				</el-card>
			</el-col>
			<el-col :xs="24" :sm="12" :md="6">
				<el-card shadow="hover" class="stat-card">
					<div class="stat-content">
						<div class="stat-icon bg-purple">
							<el-icon>
								<Cpu />
							</el-icon>
						</div>
						<div class="stat-info">
							<div class="stat-value">{{ idcRegions.length }}</div>
							<div class="stat-label">IDC 机房区域</div>
						</div>
					</div>
				</el-card>
			</el-col>
		</el-row>

		<el-row :gutter="20" class="mb-4">
			<el-col :span="12">
				<el-card shadow="hover" class="chart-card">
					<template #header>
						<div class="card-header">
							<span><el-icon>
									<PieChart />
								</el-icon> K8s 集群健康状态</span>
						</div>
					</template>
					<div id="cluster-chart" style="width: 100%; height: 300px;"></div>
				</el-card>
			</el-col>
			<el-col :span="12">
				<el-card shadow="hover" class="chart-card">
					<template #header>
						<div class="card-header">
							<span><el-icon>
									<Histogram />
								</el-icon> IDC 机房资源分布</span>
						</div>
					</template>
					<div id="idc-chart" style="width: 100%; height: 300px;"></div>
				</el-card>
			</el-col>
		</el-row>

		<el-row :gutter="20">
			<el-col :span="8">
				<el-card shadow="hover" class="list-card">
					<template #header>
						<div class="card-header">
							<span>最新公告</span>
							<el-button text type="primary"
								@click="router.push({ name: 'inform_list' })">查看全部</el-button>
						</div>
					</template>
					<el-scrollbar height="350px">
						<el-timeline style="padding-left: 10px; padding-top: 10px;">
							<el-timeline-item v-for="(item, index) in informs" :key="index"
								:timestamp="timeFormatter.stringFromDate(item.create_time)"
								:type="item.reads.length > 0 ? 'success' : 'primary'" :hollow="item.reads.length > 0">
								<div class="timeline-content">
									<h4 class="timeline-title">
										<router-link :to="{ name: 'inform_detail', params: { pk: item.id } }"
											class="link-text">
											{{ item.title }}
										</router-link>
									</h4>
									<p class="timeline-meta">发布人: {{ item.author?.realname || 'Admin' }}</p>
								</div>
							</el-timeline-item>
						</el-timeline>
					</el-scrollbar>
				</el-card>
			</el-col>

			<el-col :span="16">
				<el-card shadow="hover" class="list-card">
					<template #header>
						<div class="card-header">
							<span>IDC 服务器概览</span>
						</div>
					</template>
					<el-table :data="serverList" height="350" stripe style="width: 100%">
						<el-table-column prop="hostname" label="主机名" min-width="120" />
						<el-table-column prop="ip" label="IP地址" width="140" />
						<el-table-column prop="region" label="地域" width="140" />=
						<el-table-column label="配置规格" width="140">
							<template #default="scope">
								<el-tag size="small" type="info">{{ scope.row.cpu_count }}C /
									{{ scope.row.memory_count }}G</el-tag>
							</template>
						</el-table-column>

						<el-table-column prop="function" label="用途" min-width="120" show-overflow-tooltip />

						<el-table-column label="状态" width="100" align="center">
							<template #default="scope">
								<el-tag v-if="scope.row.scan_status === 2" type="success" effect="dark">正常</el-tag>
								<el-tag v-else-if="scope.row.scan_status === 1" type="warning" effect="dark">故障</el-tag>
								<el-tag v-else type="danger" effect="dark">异常</el-tag>
							</template>
						</el-table-column>
					</el-table>
				</el-card>
			</el-col>
		</el-row>
	</div>
</template>

<script setup name='home'>
	import {
		ref,
		onMounted,
		nextTick
	} from "vue"
	import {
		useRouter
	} from 'vue-router'
	import {
		ElMessage
	} from "element-plus"
	import {
		Monitor,
		DataLine,
		Bell,
		Cpu,
		PieChart,
		Histogram
	} from '@element-plus/icons-vue'
	import timeFormatter from "@/utils/timeFormatter"
	import homeHttp from "@/api/homeHttp"
	import * as echarts from 'echarts'

	const router = useRouter()

	// --- Data Refs ---
	const informs = ref([])
	const idcRegions = ref([])
	const clusters = ref([])
	const serverList = ref([]) // 新增：服务器列表数据

	// --- Lifecycle ---
	onMounted(async () => {
		try {
			// 请求4个接口：通知、机房(用于图表)、集群、服务器(用于列表)
			const [informsRes, regionRes, clustersRes, serverRes] = await Promise.all([
				homeHttp.getInformList(),
				homeHttp.getIdcRegion(),
				homeHttp.getClusters(),
				homeHttp.getIdcServer() // 新增请求
			])

			// 1. 通知
			informs.value = Array.isArray(informsRes) ? informsRes : (informsRes.results || [])
			console.log(informs.value)

			// 2. 机房 (用于图表)
			idcRegions.value = Array.isArray(regionRes) ? regionRes : (regionRes.results || [])

			// 3. 集群
			clusters.value = Array.isArray(clustersRes) ? clustersRes : (clustersRes.results || [])

			// 4. 服务器列表 (用于表格)
			serverList.value = Array.isArray(serverRes) ? serverRes : (serverRes.results || [])

			nextTick(() => {
				initCharts()
			})

		} catch (err) {
			console.error(err)
			ElMessage.error("首页数据加载部分失败")
		}
	})

	// --- Charts ---
	const initCharts = () => {
		// 1. Cluster Status Chart (Pie)
		const statusCount = {
			running: 0,
			abnormal: 0,
			unknown: 0
		}
		for (const c of clusters.value) {
			const status = c.cluster_status || 'unknown'
			if (statusCount[status] !== undefined) statusCount[status]++
			else statusCount['unknown']++
		}

		const chartDom1 = document.getElementById('cluster-chart')
		if (chartDom1) {
			// 销毁旧实例防止重绘问题
			if (echarts.getInstanceByDom(chartDom1)) echarts.dispose(chartDom1);

			const myChart1 = echarts.init(chartDom1)
			myChart1.setOption({
				tooltip: {
					trigger: 'item'
				},
				legend: {
					top: '5%',
					left: 'center'
				},
				series: [{
					name: '集群状态',
					type: 'pie',
					radius: ['40%', '70%'],
					avoidLabelOverlap: false,
					itemStyle: {
						borderRadius: 10,
						borderColor: '#fff',
						borderWidth: 2
					},
					label: {
						show: false,
						position: 'center'
					},
					emphasis: {
						label: {
							show: true,
							fontSize: 20,
							fontWeight: 'bold'
						}
					},
					data: [{
							value: statusCount.running,
							name: '正常',
							itemStyle: {
								color: '#67C23A'
							}
						},
						{
							value: statusCount.abnormal,
							name: '异常',
							itemStyle: {
								color: '#F56C6C'
							}
						},
						{
							value: statusCount.unknown,
							name: '未知',
							itemStyle: {
								color: '#909399'
							}
						}
					]
				}]
			})
			window.addEventListener('resize', () => myChart1.resize())
		}

		// 2. IDC Region Chart (Bar) - 依然使用机房数据做统计
		const chartDom2 = document.getElementById('idc-chart')
		if (chartDom2) {
			if (echarts.getInstanceByDom(chartDom2)) echarts.dispose(chartDom2);

			const xData = idcRegions.value.map(item => item.address || '未知')
			const yData = idcRegions.value.map(item => item.server_count || 0)

			const myChart2 = echarts.init(chartDom2)
			myChart2.setOption({
				tooltip: {
					trigger: 'axis',
					axisPointer: {
						type: 'shadow'
					}
				},
				grid: {
					left: '3%',
					right: '4%',
					bottom: '3%',
					containLabel: true
				},
				xAxis: [{
					type: 'category',
					data: xData,
					axisTick: {
						alignWithLabel: true
					},
					axisLabel: {
						interval: 0,
						rotate: 30
					}
				}],
				yAxis: [{
					type: 'value'
				}],
				series: [{
					name: '服务器数量',
					type: 'bar',
					barWidth: '40%',
					data: yData,
					itemStyle: {
						color: '#409EFF',
						borderRadius: [5, 5, 0, 0]
					}
				}]
			})
			window.addEventListener('resize', () => myChart2.resize())
		}
	}
</script>

<style scoped>
	.dashboard-container {
		padding: 20px;
		background-color: #f5f7fa;
		min-height: 100vh;
	}

	.mb-4 {
		margin-bottom: 20px;
	}

	/* 统计卡片样式 */
	.stat-card {
		border: none;
		transition: transform 0.3s;
	}

	.stat-card:hover {
		transform: translateY(-5px);
	}

	.stat-content {
		display: flex;
		align-items: center;
		padding: 10px;
	}

	.stat-icon {
		width: 60px;
		height: 60px;
		border-radius: 12px;
		display: flex;
		align-items: center;
		justify-content: center;
		margin-right: 15px;
	}

	.stat-icon .el-icon {
		font-size: 30px;
		color: #fff;
	}

	.stat-icon.bg-blue {
		background: linear-gradient(135deg, #409EFF, #79bbff);
	}

	.stat-icon.bg-green {
		background: linear-gradient(135deg, #67C23A, #95d475);
	}

	.stat-icon.bg-orange {
		background: linear-gradient(135deg, #E6A23C, #f3d19e);
	}

	.stat-icon.bg-purple {
		background: linear-gradient(135deg, #a0cfff, #b3e19d);
		background-color: #8e44ad;
	}

	.stat-info .stat-value {
		font-size: 24px;
		font-weight: bold;
		color: #303133;
	}

	.stat-info .stat-label {
		font-size: 14px;
		color: #909399;
		margin-top: 5px;
	}

	/* 图表与列表卡片通用头 */
	.card-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		font-weight: bold;
		font-size: 16px;
		color: #303133;
	}

	.card-header .el-icon {
		margin-right: 5px;
		vertical-align: middle;
	}

	/* 时间轴样式 */
	.timeline-content .timeline-title {
		margin: 0;
		font-size: 14px;
		font-weight: normal;
	}

	.timeline-content .link-text {
		color: #303133;
		text-decoration: none;
		transition: color 0.2s;
	}

	.timeline-content .link-text:hover {
		color: #409EFF;
	}

	.timeline-content .timeline-meta {
		margin: 5px 0 0;
		font-size: 12px;
		color: #909399;
	}
</style>