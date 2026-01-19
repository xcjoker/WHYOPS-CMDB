<template>
	<frame>
		<div class="monitor-container">
			<div class="header-bar">
				<div class="header-left" style="margin-right: 20px;">
					<el-icon class="monitor-icon">
						<Monitor />
					</el-icon>
					<span class="node-title">节点监控: {{ props.ip }}</span>
				</div>

				<div
					style="flex: 1; display: flex; justify-content: flex-end; align-items: center; margin-right: 15px;">
					<span style="font-size: 14px; color: #606266; margin-right: 8px;">采样精度:</span>
					<el-radio-group v-model="stepValue" size="default" @change="handleStepChange">
						<el-radio-button value="1s">极高 (1s)</el-radio-button>
						<el-radio-button value="10s">高 (10s)</el-radio-button>
						<el-radio-button value="30s">中 (30s)</el-radio-button>
						<el-radio-button value="60s">低 (60s)</el-radio-button>
					</el-radio-group>
				</div>

				<el-date-picker v-model="timeRange" type="datetimerange" range-separator="至" start-placeholder="开始"
					end-placeholder="结束" @change="handleTimeChange" value-format="X" class="custom-picker"
					:disabled-date="disabledDate" />
			</div>

			<el-row :gutter="20">
				<el-col :span="8">
					<div class="chart-card">
						<div class="chart-title">CPU 使用率</div>
						<div ref="chartRef_cpu" class="chart-box-sm"></div>
					</div>
				</el-col>
				<el-col :span="8">
					<div class="chart-card">
						<div class="chart-title">内存 分配率</div>
						<div ref="chartRef_mem" class="chart-box-sm"></div>
					</div>
				</el-col>
				<el-col :span="8">
					<div class="chart-card">
						<div class="chart-title">磁盘容量 (根分区)</div>
						<div ref="chartRef_fs" class="chart-box-sm"></div>
					</div>
				</el-col>
			</el-row>

			<el-row :gutter="20" class="mt-20">
				<el-col :span="12">
					<div class="chart-card">
						<div class="chart-title">磁盘 IO 速率 (Read/Write) KB</div>
						<div ref="chartRef_disk" class="chart-box-md"></div>
					</div>
				</el-col>
				<el-col :span="12">
					<div class="chart-card">
						<div class="chart-title">网络流量 (In/Out) KB</div>
						<div ref="chartRef_net" class="chart-box-md"></div>
					</div>
				</el-col>
			</el-row>

			<el-row :gutter="20" class="mt-20">
				<el-col :span="12">
					<div class="chart-card">
						<div class="chart-title">系统平均负载 (Load Average)</div>
						<div ref="chartRef_load" class="chart-box-md"></div>
					</div>
				</el-col>
				<el-col :span="12">
					<div class="chart-card">
						<div class="chart-title">TCP 连接数</div>
						<div ref="chartRef_tcp" class="chart-box-md"></div>
					</div>
				</el-col>
			</el-row>
		</div>
	</frame>
</template>

<script setup>
	import {
		defineProps,
		onMounted,
		ref,
		nextTick
	} from 'vue'
	import frame from "@/views/main/frame.vue"
	import authHttp from "@/api/authHttp";
	import * as echarts from 'echarts'
	import {
		Monitor
	} from '@element-plus/icons-vue' // 假设你用了 Element Icon
	import {
			ElMessage
		} from 'element-plus'


	const stepValue = ref('10s')

	const disabledDate = (time) => {
		// 如果日期的时间戳 > 当前时间，这就代表是“未来”，返回 true 禁用它
		return time.getTime() > Date.now()
	}

	const formatTime = (timestamp) => {
		// new Date() 会自动读取你浏览器的时区（比如中国就是 UTC+8）
		const date = new Date(timestamp);
		// 转为 "16:45" 这种格式
		return date.toLocaleTimeString('en-GB', {
			hour12: false,
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	const props = defineProps({
		ip: {
			type: String,
			required: true
		}
	})

	// 初始时间：最近1小时
	const now = Math.floor(Date.now() / 1000);
	const timeRange = ref([now - 3600, now]);

	// Refs
	const chartRef_cpu = ref(null)
	const chartRef_mem = ref(null)
	const chartRef_fs = ref(null) // 新增
	const chartRef_disk = ref(null)
	const chartRef_net = ref(null)
	const chartRef_load = ref(null) // 新增
	const chartRef_tcp = ref(null)

	let charts = []

	// 通用配置：仪表盘
	const initGaugeChart = (el, val, name, color) => {
		const myChart = echarts.init(el)
		myChart.setOption({
			series: [{
				type: 'gauge',
				startAngle: 180,
				endAngle: 0,
				center: ['50%', '70%'],
				radius: '90%',
				progress: {
					show: true,
					width: 14,
					itemStyle: {
						color: color
					}
				},
				axisLine: {
					lineStyle: {
						width: 14,
						color: [
							[1, '#E6EBF8']
						]
					}
				}, // 灰色底色
				pointer: {
					show: false
				},
				axisTick: {
					show: false
				},
				splitLine: {
					show: false
				},
				axisLabel: {
					show: false
				},
				detail: {
					valueAnimation: true,
					offsetCenter: [0, -10],
					fontSize: 28,
					fontWeight: 'bold',
					formatter: '{value}%',
					color: '#333'
				},
				data: [{
					value: val,
					name: name
				}]
			}]
		})
		charts.push(myChart)
	}

	// 通用配置：折线图
	const initLineChart = (el, title, seriesData, colors, minTime, maxTime) => {
		const myChart = echarts.init(el)

		// 构造 Series，此时 data 里的每一项已经是 [时间戳, 数值] 的格式了
		const series = seriesData.map((item, index) => ({
			name: item.name,
			type: 'line',
			smooth: true,
			showSymbol: false,
			data: item.data, // 这里传入的是 [[time, value], [time, value]]
			itemStyle: {
				color: colors[index]
			},
			areaStyle: item.isArea ? {
				color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{
						offset: 0,
						color: colors[index]
					},
					{
						offset: 1,
						color: 'rgba(255,255,255,0)'
					}
				]),
				opacity: 0.3
			} : null
		}))

		myChart.setOption({
			tooltip: {
				trigger: 'axis',
				// 时间轴模式下，tooltip 需要格式化一下标题，否则显示的是长整数
				valueFormatter: (value) => value // 可选
			},
			legend: {
				bottom: 0,
				icon: 'circle'
			},
			grid: {
				left: '3%',
				right: '4%',
				bottom: '10%',
				top: '10%',
				containLabel: true
			},
			xAxis: {
				type: 'time', // <--- 关键修改：变成时间轴
				boundaryGap: false,
				min: minTime, // 传入毫秒级时间戳
				max: maxTime, // 传入毫秒级时间戳
				// 自动格式化 X 轴标签
				axisLabel: {
					formatter: (value) => {
						const date = new Date(value);
						return date.toLocaleTimeString('en-GB', {
							hour12: false,
							hour: '2-digit',
							minute: '2-digit'
						});
					}
				}
			},
			yAxis: {
				type: 'value',
				splitLine: {
					lineStyle: {
						type: 'dashed',
						color: '#eee'
					}
				}
			},
			series: series
		})
		charts.push(myChart)
	}

	const handleStepChange = () => {
		// 切换步长时，不需要 dispose 销毁图表，直接重新 fetch 更新数据即可
		// ECharts 会自动过渡动画，效果更好
		fetchData()
	}

	const fetchData = async () => {
		// 1. 获取当前用户选择的时间范围 (秒级时间戳)
		// 如果用户没选 (初始化状态)，start/end 可能是 undefined
		const startTimestamp = timeRange.value?.[0];
		const endTimestamp = timeRange.value?.[1];

		const params = {
			ip: props.ip,
			start_time: startTimestamp,
			end_time: endTimestamp,
			step: stepValue.value // <--- 传入用户选择的步长 (1s, 10s 等)
		}

		// 发送请求
		const res = await authHttp.monitorPost(params)

		// 如果没有数据直接返回，防止报错
		if (!res) return;
		// === 🆕 新增：处理步长调整的系统消息 ===
		if (res.sys_warning) {
			// 使用 Element Plus 的 Warning 提示
			ElMessage.warning({
				message: res.sys_warning,
				duration: 3000, // 显示 3 秒
				showClose: true,
				grouping: true // 防止连续弹窗堆叠
			});

			// (可选) 弹窗完后从对象里删掉，保持数据纯净
			delete res.sys_warning;
		}

		// === 辅助函数：数据对齐 ===
		// 将后端返回的 times(毫秒) 和 data 合并成 ECharts 需要的 [[time, value], ...] 格式
		// 这样就不需要依赖 CPU 的时间轴，每个指标都有自己独立的时间点，互不干扰
		const zipData = (sourceObj) => {
			if (!sourceObj || !sourceObj.times || !sourceObj.data) return [];
			return sourceObj.data.map((val, index) => {
				return [sourceObj.times[index], val];
			});
		}

		// === 🔴 关键步骤：计算 X 轴锁定的起止时间 (毫秒) ===
		// 即使后端中间有一段没数据，ECharts 也会强制把 X 轴画满这个范围，留白显示
		// 1. 如果 startTimestamp 存在，乘 1000 转毫秒
		// 2. 如果不存在 (默认情况)，用 Date.now() 往前推 1 小时
		const nowMs = Date.now();
		const minTimeMs = startTimestamp ? startTimestamp * 1000 : (nowMs - 3600 * 1000);
		const maxTimeMs = endTimestamp ? endTimestamp * 1000 : nowMs;

		// === 第一行：仪表盘 (不需要时间轴) ===

		// CPU 仪表盘 (取最后一个点的数据)
		const cpuVal = res.cpu_usage?.data?.slice(-1)[0] || 0;
		initGaugeChart(chartRef_cpu.value, cpuVal, 'CPU', '#409EFF')

		// 磁盘容量 仪表盘
		const fsVal = res.fs_usage_root?.data?.slice(-1)[0] || 0;
		initGaugeChart(chartRef_fs.value, fsVal, 'Disk Space', '#F56C6C')

		// === 带有时间轴的折线图 (传入 minTimeMs 和 maxTimeMs) ===

		// 内存 (面积图)
		initLineChart(chartRef_mem.value, 'Memory', [{
			name: '已用',
			data: zipData(res.mem_usage),
			isArea: true
		}], ['#67C23A'], minTimeMs, maxTimeMs)

		// 磁盘 IO (读/写)
		initLineChart(chartRef_disk.value, 'Disk IO', [{
				name: 'Read',
				data: zipData(res.disk_io_read)
			},
			{
				name: 'Write',
				data: zipData(res.disk_io_write)
			}
		], ['#E6A23C', '#409EFF'], minTimeMs, maxTimeMs)

		// 网络流量 (In/Out)
		initLineChart(chartRef_net.value, 'Network', [{
				name: 'Inbound',
				data: zipData(res.net_in),
				isArea: true
			},
			{
				name: 'Outbound',
				data: zipData(res.net_out),
				isArea: true
			}
		], ['#67C23A', '#909399'], minTimeMs, maxTimeMs)

		// 系统负载 (1/5/15分钟)
		initLineChart(chartRef_load.value, 'Load Avg', [{
				name: '1 min',
				data: zipData(res.load_1)
			},
			{
				name: '5 min',
				data: zipData(res.load_5)
			},
			{
				name: '15 min',
				data: zipData(res.load_15)
			}
		], ['#F56C6C', '#E6A23C', '#409EFF'], minTimeMs, maxTimeMs)

		// TCP 连接状态 (5种状态)
		initLineChart(chartRef_tcp.value, 'TCP Connection States', [{
					name: 'ESTABLISHED',
					data: zipData(res.tcp_established),
					isArea: true,
					opacity: 0.2
				},
				{
					name: 'TIME_WAIT',
					data: zipData(res.tcp_time_wait),
					isArea: false
				},
				{
					name: 'CLOSE_WAIT',
					data: zipData(res.tcp_close_wait),
					isArea: false
				},
				{
					name: 'SYN_RECV',
					data: zipData(res.tcp_syn_recv),
					isArea: false
				},
				{
					name: 'LISTEN',
					data: zipData(res.tcp_listen),
					isArea: false
				}
			],
			['#67C23A', '#E6A23C', '#F56C6C', '#9b59b6', '#409EFF'],
			minTimeMs, maxTimeMs) // <--- 传入时间范围
	}

	const handleTimeChange = () => {
		charts.forEach(c => c.dispose())
		charts = []
		fetchData()
	}

	onMounted(() => {
		nextTick(() => {
			fetchData()
		})
		window.addEventListener('resize', () => charts.forEach(c => c.resize()))
	})
</script>

<style scoped>
	.monitor-container {
		padding: 24px;
		background-color: #f6f8f9;
		min-height: 100vh;
	}

	/* 头部美化 */
	.header-bar {
		display: flex;
		justify-content: space-between;
		/* 关键：两端对齐 */
		align-items: center;
		margin-bottom: 24px;
		background: #fff;
		padding: 16px 24px;
		border-radius: 8px;
		box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
	}

	.header-left {
		display: flex;
		align-items: center;
		gap: 10px;
	}

	.monitor-icon {
		font-size: 20px;
		color: #409EFF;
	}

	.node-title {
		font-size: 18px;
		font-weight: 600;
		color: #1f2f3d;
	}

	.chart-card {
		background: #fff;
		padding: 20px;
		border-radius: 8px;
		box-shadow: 0 1px 4px rgba(0, 21, 41, 0.05);
		transition: transform 0.3s;
	}

	.chart-card:hover {
		box-shadow: 0 4px 12px rgba(0, 21, 41, 0.1);
	}

	.chart-title {
		font-size: 15px;
		color: #606266;
		font-weight: 600;
		margin-bottom: 15px;
		display: flex;
		align-items: center;
	}

	.chart-title::before {
		content: '';
		width: 4px;
		height: 16px;
		background: #409EFF;
		margin-right: 8px;
		border-radius: 2px;
	}

	.chart-box-sm {
		height: 180px;
	}

	/* 第一行稍矮 */
	.chart-box-md {
		height: 280px;
	}

	/* 下面两行稍高，展示细节 */
	.mt-20 {
		margin-top: 20px;
	}
</style>